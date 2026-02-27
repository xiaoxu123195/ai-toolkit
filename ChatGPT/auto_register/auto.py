# www~
import json
import os
import re
import sys
import time
import uuid
import math
import random
import string
import secrets
import hashlib
import base64
import threading
from datetime import datetime, timezone, timedelta
from urllib import request as urllib_request
from urllib.parse import urlparse, parse_qs, urlencode, quote
from dataclasses import dataclass
from typing import Any, Dict
import urllib
from urllib.parse import urlparse, parse_qs
from urllib import request

from curl_cffi import requests


# email
def get(url: str, headers: dict | None = None) -> tuple[str, dict]:
    # res, header
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req) as response:
            resp_text = response.read().decode("utf-8")
            resp_headers = dict(response.getheaders())
            return resp_text, resp_headers
    except Exception as e:
        print(e)
        return -1, {}


def get_email() -> str:
    body, _ = get("https://mail.chatgpt.org.uk/api/generate-email",
                  {"X-API-Key": "gpt-test", "User-Agent": "Mozilla/5.0"})
    data = json.loads(body)
    return data["data"]["email"]


def get_oai_code(email: str) -> str:
    regex = r" (?<!\d)(\d{6})(?!\d)"  # r"(?<!\d)\d{6}(?!\d)"
    for i in range(20):
        body, _ = get(f"https://mail.chatgpt.org.uk/api/emails?email={email}",
                      {"referer": "https://mail.chatgpt.org.uk/", "User-Agent": "Mozilla/5.0"})
        data = json.loads(body)
        emails = data["data"]["emails"]
        for email in emails:
            if "openai" in email["from_address"]:
                m = re.search(regex, email["subject"])
                if m:
                    return m.group(1)
                m = re.search(regex, email["html_content"])
                return m.group(1)
            else:
                time.sleep(3)
                continue


# end


# oauth
AUTH_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

DEFAULT_REDIRECT_URI = f"http://localhost:1455/auth/callback"
DEFAULT_SCOPE = "openid email profile offline_access"


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sha256_b64url_no_pad(s: str) -> str:
    return _b64url_no_pad(hashlib.sha256(s.encode("ascii")).digest())


def _random_state(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)


def _pkce_verifier() -> str:
    # RFC 7636 allows 43..128 chars; urlsafe token is fine.
    return secrets.token_urlsafe(64)


def _parse_callback_url(callback_url: str) -> Dict[str, str]:
    candidate = callback_url.strip()
    if not candidate:
        return {
            "code": "",
            "state": "",
            "error": "",
            "error_description": "",
        }

    if "://" not in candidate:
        if candidate.startswith("?"):
            candidate = f"http://localhost{candidate}"
        elif any(ch in candidate for ch in "/?#") or ":" in candidate:
            candidate = f"http://{candidate}"
        elif "=" in candidate:
            candidate = f"http://localhost/?{candidate}"

    parsed = urllib.parse.urlparse(candidate)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    fragment = urllib.parse.parse_qs(parsed.fragment, keep_blank_values=True)

    for key, values in fragment.items():
        if key not in query or not query[key] or not (query[key][0] or "").strip():
            query[key] = values

    def get1(k: str) -> str:
        v = query.get(k, [""])
        return (v[0] or "").strip()

    code = get1("code")
    state = get1("state")
    error = get1("error")
    error_description = get1("error_description")

    if code and not state and "#" in code:
        code, state = code.split("#", 1)

    if not error and error_description:
        error, error_description = error_description, ""

    return {
        "code": code,
        "state": state,
        "error": error,
        "error_description": error_description,
    }


def _jwt_claims_no_verify(id_token: str) -> Dict[str, Any]:
    if not id_token or id_token.count(".") < 2:
        return {}
    payload_b64 = id_token.split(".")[1]
    pad = "=" * ((4 - (len(payload_b64) % 4)) % 4)
    try:
        payload = base64.urlsafe_b64decode((payload_b64 + pad).encode("ascii"))
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return {}


def _to_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _post_form(url: str, data: Dict[str, str], timeout: int = 30) -> Dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.status != 200:
                raise RuntimeError(
                    f"token exchange failed: {resp.status}: {raw.decode('utf-8', 'replace')}"
                )
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(
            f"token exchange failed: {exc.code}: {raw.decode('utf-8', 'replace')}"
        ) from exc


@dataclass(frozen=True)
class OAuthStart:
    auth_url: str
    state: str
    code_verifier: str
    redirect_uri: str


def generate_oauth_url(*, redirect_uri: str = DEFAULT_REDIRECT_URI, scope: str = DEFAULT_SCOPE) -> OAuthStart:
    state = _random_state()
    code_verifier = _pkce_verifier()
    code_challenge = _sha256_b64url_no_pad(code_verifier)

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return OAuthStart(
        auth_url=auth_url,
        state=state,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
    )


def submit_callback_url(*, callback_url: str, expected_state: str, code_verifier: str,
                        redirect_uri: str = DEFAULT_REDIRECT_URI) -> str:
    cb = _parse_callback_url(callback_url)
    if cb["error"]:
        desc = cb["error_description"]
        raise RuntimeError(f"oauth error: {cb['error']}: {desc}".strip())

    if not cb["code"]:
        raise ValueError("callback url missing ?code=")
    if not cb["state"]:
        raise ValueError("callback url missing ?state=")
    if cb["state"] != expected_state:
        raise ValueError("state mismatch")

    token_resp = _post_form(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": cb["code"],
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )

    access_token = (token_resp.get("access_token") or "").strip()
    refresh_token = (token_resp.get("refresh_token") or "").strip()
    id_token = (token_resp.get("id_token") or "").strip()
    expires_in = _to_int(token_resp.get("expires_in"))

    claims = _jwt_claims_no_verify(id_token)
    email = str(claims.get("email") or "").strip()
    auth_claims = claims.get("https://api.openai.com/auth") or {}
    account_id = str(auth_claims.get("chatgpt_account_id") or "").strip()

    now = int(time.time())
    expired_rfc3339 = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + max(expires_in, 0))
    )
    now_rfc3339 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

    config = {
        "id_token": id_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "account_id": account_id,
        "last_refresh": now_rfc3339,
        "email": email,
        "type": "codex",
        "expired": expired_rfc3339,
    }

    return json.dumps(config, ensure_ascii=False, separators=(",", ":"))


# end


def run() -> str:
    s = requests.Session(impersonate="chrome")
    email = get_email()
    print(email)
    oauth = generate_oauth_url()
    url = oauth.auth_url
    resp = s.get(url)
    did = s.cookies.get("oai-did")
    print(did)
    signup_body = f'{{"username":{{"value":"{email}","kind":"email"}},"screen_hint":"signup"}}'
    sen_req_body = f'{{"p":"","id":"{did}","flow":"authorize_continue"}}'
    sen_resp = requests.post("https://sentinel.openai.com/backend-api/sentinel/req",
                             headers={"origin": "https://sentinel.openai.com",
                                      "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                                      "content-type": "text/plain;charset=UTF-8"}, data=sen_req_body)
    print(sen_resp.status_code)
    sen_resp = sen_resp.json()["token"]
    sentinel = f'{{"p": "", "t": "", "c": "{sen_resp}", "id": "{did}", "flow": "authorize_continue"}}'
    signup_resp = s.post("https://auth.openai.com/api/accounts/authorize/continue",
                         headers={"referer": "https://auth.openai.com/create-account", "accept": "application/json",
                                  "content-type": "application/json", "openai-sentinel-token": sentinel},
                         data=signup_body)
    print(signup_resp.status_code)
    otp_resp = s.post("https://auth.openai.com/api/accounts/passwordless/send-otp",
                      headers={"referer": "https://auth.openai.com/create-account/password",
                               "accept": "application/json", "content-type": "application/json"})
    print(otp_resp.status_code)
    code = get_oai_code(email)
    print(code)
    code_body = f'{{"code":"{code}"}}'
    code_resp = s.post("https://auth.openai.com/api/accounts/email-otp/validate",
                       headers={"referer": "https://auth.openai.com/email-verification", "accept": "application/json",
                                "content-type": "application/json"}, data=code_body)
    print(code_resp.status_code)
    create_account_body = '{"name":"Neo","birthdate":"2000-02-20"}'
    create_account_resp = s.post("https://auth.openai.com/api/accounts/create_account",
                                 headers={"referer": "https://auth.openai.com/about-you", "accept": "application/json",
                                          "content-type": "application/json"}, data=create_account_body)
    create_account_status = create_account_resp.status_code
    print(create_account_status)
    if create_account_status != 200:
        print(create_account_resp.text)
        return
    print(create_account_status)
    auth = s.cookies.get("oai-client-auth-session")
    auth = base64.b64decode(auth.split(".")[0])
    auth = json.loads(auth)
    workspace_id = auth["workspaces"][0]["id"]
    print(workspace_id)
    select_body = f'{{"workspace_id":"{workspace_id}"}}'
    select_resp = s.post("https://auth.openai.com/api/accounts/workspace/select",
                         headers={"referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                                  "content-type": "application/json"}, data=select_body)
    print(select_resp.status_code)
    continue_url = select_resp.json()["continue_url"]
    final_resp = s.get(continue_url, allow_redirects=False)
    final_resp = s.get(final_resp.headers.get("Location"), allow_redirects=False)
    final_resp = s.get(final_resp.headers.get("Location"), allow_redirects=False)
    cbk = final_resp.headers.get("Location")
    return submit_callback_url(callback_url=cbk, code_verifier=oauth.code_verifier, redirect_uri=oauth.redirect_uri,
                               expected_state=oauth.state)


UPLOAD_URL = "http://35.212.247.92:8317/v0/management/auth-files"


def upload_auth_file(filepath: str):
    boundary = f"----WebKitFormBoundary{secrets.token_hex(8)}"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        UPLOAD_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer admin123456",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


if __name__ == "__main__":
    count = int(input("注册数量: "))
    os.makedirs("files", exist_ok=True)
    success = 0
    for i in range(count):
        print(f"\n===== 第 {i + 1}/{count} 个账号 =====")
        try:
            result = run()
            if result:
                data = json.loads(result)
                email = data.get("email", f"unknown_{i}")
                filename = f"files/{email}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                success += 1
                print(f"成功，已保存到 {filename}")
                try:
                    status, resp = upload_auth_file(filename)
                    print(f"上传结果：{status} {resp}")
                except Exception as ue:
                    print(f"上传失败：{ue}")
            else:
                print("失败：未返回结果")
        except Exception as e:
            print(f"失败：{e}")
        time.sleep(5)
    print(f"\n完成：成功 {success}/{count}")