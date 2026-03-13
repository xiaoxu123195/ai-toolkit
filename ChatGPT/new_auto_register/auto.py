import json
import os
import re
import sys
import time
import random
import string
import secrets
import hashlib
import base64
import logging
import urllib
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict

import yaml
import requests as std_requests
from curl_cffi import requests

# ========== 日志 ==========

log = logging.getLogger("auto_register")


def setup_logging(log_to_file: bool):
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    log.addHandler(ch)

    if log_to_file:
        os.makedirs("logs", exist_ok=True)
        fh = logging.FileHandler(f"logs/{time.strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)


# ========== 临时邮箱 ==========

def create_email(cfg: dict) -> dict:
    """创建临时邮箱，返回 {"id": ..., "address": ...}"""
    api_base = cfg["email_api"]
    api_key = cfg["email_api_key"]
    domain = cfg.get("email_domain") or None
    body = {
        "name": "gpt" + secrets.token_hex(3),
        "expiryTime": 3600000,
    }
    if domain:
        body["domain"] = domain
    resp = std_requests.post(f"{api_base}/api/emails/generate", headers={
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {"id": data["id"], "address": data["email"]}


def get_oai_code(email_id: str, cfg: dict) -> str:
    """轮询邮箱获取6位验证码"""
    api_base = cfg["email_api"]
    api_key = cfg["email_api_key"]
    regex = r"\b(\d{6})\b"
    for i in range(60):
        resp = std_requests.get(f"{api_base}/api/emails/{email_id}", headers={
            "X-API-Key": api_key,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        messages = data.get("messages", [])
        if messages:
            msg = messages[0]
            if msg.get("subject"):
                m = re.search(regex, msg["subject"])
                if m:
                    return m.group(1)
            content = msg.get("content") or msg.get("html") or ""
            m = re.search(regex, content)
            if m:
                return m.group(1)
        time.sleep(3)


# ========== 密码生成 ==========

def generate_random_password(length=16):
    """生成符合 OpenAI 要求的随机密码"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    pwd = list(
        random.choice(string.ascii_uppercase)
        + random.choice(string.ascii_lowercase)
        + random.choice(string.digits)
        + random.choice("!@#$%")
        + "".join(random.choice(chars) for _ in range(length - 4))
    )
    random.shuffle(pwd)
    return "".join(pwd)


# ========== OAuth ==========

AUTH_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_REDIRECT_URI = "http://localhost:1455/auth/callback"
DEFAULT_SCOPE = "openid email profile offline_access"


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sha256_b64url_no_pad(s: str) -> str:
    return _b64url_no_pad(hashlib.sha256(s.encode("ascii")).digest())


def _random_state(nbytes: int = 16) -> str:
    return secrets.token_urlsafe(nbytes)


def _pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def _parse_callback_url(callback_url: str) -> Dict[str, str]:
    candidate = callback_url.strip()
    if not candidate:
        return {"code": "", "state": "", "error": "", "error_description": ""}

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

    return {"code": code, "state": state, "error": error, "error_description": error_description}


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
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.status != 200:
                raise RuntimeError(f"token exchange failed: {resp.status}: {raw.decode('utf-8', 'replace')}")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(f"token exchange failed: {exc.code}: {raw.decode('utf-8', 'replace')}") from exc


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
        "client_id": CLIENT_ID, "response_type": "code", "redirect_uri": redirect_uri,
        "scope": scope, "state": state, "code_challenge": code_challenge,
        "code_challenge_method": "S256", "prompt": "login",
        "id_token_add_organizations": "true", "codex_cli_simplified_flow": "true",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return OAuthStart(auth_url=auth_url, state=state, code_verifier=code_verifier, redirect_uri=redirect_uri)


def submit_callback_url(*, callback_url: str, expected_state: str, code_verifier: str,
                        redirect_uri: str = DEFAULT_REDIRECT_URI) -> str:
    cb = _parse_callback_url(callback_url)
    if cb["error"]:
        raise RuntimeError(f"oauth error: {cb['error']}: {cb['error_description']}".strip())
    if not cb["code"]:
        raise ValueError("callback url missing ?code=")
    if not cb["state"]:
        raise ValueError("callback url missing ?state=")
    if cb["state"] != expected_state:
        raise ValueError("state mismatch")

    token_resp = _post_form(TOKEN_URL, {
        "grant_type": "authorization_code", "client_id": CLIENT_ID,
        "code": cb["code"], "redirect_uri": redirect_uri, "code_verifier": code_verifier,
    })

    access_token = (token_resp.get("access_token") or "").strip()
    refresh_token = (token_resp.get("refresh_token") or "").strip()
    id_token = (token_resp.get("id_token") or "").strip()
    expires_in = _to_int(token_resp.get("expires_in"))

    claims = _jwt_claims_no_verify(id_token)
    email = str(claims.get("email") or "").strip()
    auth_claims = claims.get("https://api.openai.com/auth") or {}
    account_id = str(auth_claims.get("chatgpt_account_id") or "").strip()

    now = int(time.time())
    expired_rfc3339 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + max(expires_in, 0)))
    now_rfc3339 = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

    config = {
        "id_token": id_token, "access_token": access_token, "refresh_token": refresh_token,
        "account_id": account_id, "last_refresh": now_rfc3339, "email": email,
        "type": "codex", "expired": expired_rfc3339,
    }
    return json.dumps(config, ensure_ascii=False, separators=(",", ":"))


# ========== 上传 ==========

def upload_auth_file(filepath: str, upload_url: str, upload_token: str):
    boundary = f"----WebKitFormBoundary{secrets.token_hex(8)}"
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(upload_url, data=body, method="POST", headers={
        "Authorization": f"Bearer {upload_token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


# ========== 注册流程 ==========

def run(cfg: dict) -> str:
    s = requests.Session(impersonate="chrome")
    mail = create_email(cfg)
    email = mail["address"]
    email_id = mail["id"]
    log.info(f"邮箱: {email}")
    oauth = generate_oauth_url()
    s.get(oauth.auth_url)
    did = s.cookies.get("oai-did")
    log.info(f"oai-did: {did}")

    password = generate_random_password()
    log.info(f"密码: {password}")

    signup_body = f'{{"username":{{"value":"{email}","kind":"email"}},"screen_hint":"signup"}}'
    sen_req_body = f'{{"p":"","id":"{did}","flow":"authorize_continue"}}'
    sen_resp = requests.post("https://sentinel.openai.com/backend-api/sentinel/req",
                             headers={"origin": "https://sentinel.openai.com",
                                      "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                                      "content-type": "text/plain;charset=UTF-8"}, data=sen_req_body)
    log.info(f"sentinel: {sen_resp.status_code}")
    sen_token = sen_resp.json()["token"]
    sentinel = f'{{"p": "", "t": "", "c": "{sen_token}", "id": "{did}", "flow": "authorize_continue"}}'

    signup_resp = s.post("https://auth.openai.com/api/accounts/authorize/continue",
                         headers={"referer": "https://auth.openai.com/create-account", "accept": "application/json",
                                  "content-type": "application/json", "openai-sentinel-token": sentinel},
                         data=signup_body)
    log.info(f"signup: {signup_resp.status_code}")
    if signup_resp.status_code != 200:
        log.error(f"signup 失败: {signup_resp.text}")
        return None

    # 步骤2: 用密码注册 (替代旧的 passwordless/send-otp)
    register_body = json.dumps({"username": email, "password": password})
    register_resp = s.post("https://auth.openai.com/api/accounts/user/register",
                           headers={"referer": "https://auth.openai.com/create-account/password",
                                    "accept": "application/json", "content-type": "application/json",
                                    "openai-sentinel-token": sentinel},
                           data=register_body)
    log.info(f"register: {register_resp.status_code}")
    if register_resp.status_code not in (200, 301, 302):
        log.error(f"register 失败: {register_resp.text}")
        return None

    # 步骤3: 触发邮箱验证码发送 (GET 请求)
    s.get("https://auth.openai.com/api/accounts/email-otp/send",
          headers={"referer": "https://auth.openai.com/create-account/password"})
    s.get("https://auth.openai.com/email-verification",
          headers={"referer": "https://auth.openai.com/create-account/password"})
    log.info("email-otp/send 触发完成")

    code = get_oai_code(email_id, cfg)
    if not code:
        log.error("获取验证码超时")
        return None
    log.info(f"验证码: {code}")

    code_body = f'{{"code":"{code}"}}'
    code_resp = s.post("https://auth.openai.com/api/accounts/email-otp/validate",
                       headers={"referer": "https://auth.openai.com/email-verification", "accept": "application/json",
                                "content-type": "application/json"}, data=code_body)
    log.info(f"validate-otp: {code_resp.status_code}")

    create_account_body = '{"name":"Neo","birthdate":"2000-02-20"}'
    create_resp = s.post("https://auth.openai.com/api/accounts/create_account",
                         headers={"referer": "https://auth.openai.com/about-you", "accept": "application/json",
                                  "content-type": "application/json"}, data=create_account_body)
    log.info(f"create_account: {create_resp.status_code}")
    if create_resp.status_code != 200:
        log.error(f"创建账号失败: {create_resp.text}")
        return None

    auth = s.cookies.get("oai-client-auth-session")
    auth = json.loads(base64.b64decode(auth.split(".")[0]))
    workspace_id = auth["workspaces"][0]["id"]
    log.info(f"workspace: {workspace_id}")

    select_body = f'{{"workspace_id":"{workspace_id}"}}'
    select_resp = s.post("https://auth.openai.com/api/accounts/workspace/select",
                         headers={"referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
                                  "content-type": "application/json"}, data=select_body)
    log.info(f"workspace/select: {select_resp.status_code}")

    continue_url = select_resp.json()["continue_url"]
    final_resp = s.get(continue_url, allow_redirects=False)
    final_resp = s.get(final_resp.headers.get("Location"), allow_redirects=False)
    final_resp = s.get(final_resp.headers.get("Location"), allow_redirects=False)
    cbk = final_resp.headers.get("Location")
    return submit_callback_url(callback_url=cbk, code_verifier=oauth.code_verifier,
                               redirect_uri=oauth.redirect_uri, expected_state=oauth.state)


# ========== 单个任务 ==========

def register_one(index: int, total: int, cfg: dict) -> bool:
    log.info(f"===== 第 {index}/{total} 个账号 =====")
    try:
        result = run(cfg)
        if not result:
            log.warning(f"[{index}/{total}] 失败: 未返回结果")
            return False

        data = json.loads(result)
        email = data.get("email", f"unknown_{index}")
        filename = f"files/{email}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"[{index}/{total}] 成功, 已保存到 {filename}")

        if cfg["upload"]:
            try:
                status, resp = upload_auth_file(filename, cfg["upload_url"], cfg["upload_token"])
                log.info(f"[{index}/{total}] 上传结果: {status} {resp}")
            except Exception as ue:
                log.error(f"[{index}/{total}] 上传失败: {ue}")
        return True

    except Exception as e:
        log.error(f"[{index}/{total}] 失败: {e}")
        return False


# ========== 入口 ==========

def main():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    count = cfg.get("count", 1)
    max_workers = cfg.get("max_workers", 1)

    setup_logging(cfg.get("log_to_file", 0))
    os.makedirs("files", exist_ok=True)

    log.info(f"开始注册 {count} 个账号, 并发数 {max_workers}")

    if max_workers <= 1:
        success = 0
        for i in range(1, count + 1):
            if register_one(i, count, cfg):
                success += 1
    else:
        success = 0
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="worker") as pool:
            for i in range(1, count + 1):
                futures.append(pool.submit(register_one, i, count, cfg))
            for fut in as_completed(futures):
                if fut.result():
                    success += 1

    log.info(f"完成: 成功 {success}/{count}")


if __name__ == "__main__":
    main()
