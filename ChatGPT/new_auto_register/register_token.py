"""注册 ChatGPT 网页账号并获取 accessToken。

与 auto.py(codex 流程)的区别：本脚本走 chatgpt.com 的网页登录上下文注册
(经 chatgpt.com/api/auth/signin/openai 让服务端生成网页 client_id + chatgpt.com
回调的授权 URL)，是普通消费者注册，OTP 后不会被强制手机验证(add_phone)。
注册完成后直接落到 chatgpt.com/api/auth/callback 写入 session-token，
再 GET /api/auth/session 取 accessToken，逐行写入 txt。

sentinel 风控用 QuickJS(node 跑真实 sdk.js, 带 turnstile t)，失败回退纯 Python PoW。
"""
import os
import re
import sys
import json
import time
import random
import string
import base64
import logging
import tempfile
import threading
import subprocess
import urllib.parse
import uuid

import yaml
import requests as std_requests
from curl_cffi import requests

# ========== 日志 ==========

log = logging.getLogger("register_token")
_token_lock = threading.Lock()


def setup_logging(log_to_file: bool):
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    log.addHandler(ch)
    if log_to_file:
        os.makedirs("logs", exist_ok=True)
        fh = logging.FileHandler(f"logs/{time.strftime('%Y%m%d_%H%M%S')}_token.log", encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)


# ========== 临时邮箱 (moe mail) ==========

def create_email(cfg: dict) -> dict:
    api_base = cfg["email_api"]
    api_key = cfg["email_api_key"]
    domain = cfg.get("email_domain") or None
    body = {"name": "gpt" + uuid.uuid4().hex[:6], "expiryTime": 3600000}
    if domain:
        body["domain"] = domain
    resp = std_requests.post(f"{api_base}/api/emails/generate", headers={
        "X-API-Key": api_key, "Content-Type": "application/json",
    }, json=body, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {"id": data["id"], "address": data["email"]}


def get_oai_code(email_id: str, cfg: dict) -> str:
    api_base = cfg["email_api"]
    api_key = cfg["email_api_key"]
    regex = r"\b(\d{6})\b"
    for _ in range(60):
        resp = std_requests.get(f"{api_base}/api/emails/{email_id}", headers={"X-API-Key": api_key}, timeout=10)
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        if messages:
            msg = messages[0]
            if msg.get("subject"):
                m = re.search(regex, msg["subject"])
                if m:
                    return m.group(1)
            m = re.search(regex, msg.get("content") or msg.get("html") or "")
            if m:
                return m.group(1)
        time.sleep(3)
    return ""


# ========== 密码 ==========

def generate_random_password(length=16):
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


# ========== Sentinel 风控 (QuickJS 优先, PoW 兜底) ==========

AUTH_BASE = "https://auth.openai.com"
CHATGPT_BASE = "https://chatgpt.com"

SENTINEL_REQ_URL = "https://sentinel.openai.com/backend-api/sentinel/req"
SENTINEL_REF = "https://sentinel.openai.com/backend-api/sentinel/frame.html"
SENTINEL_VERSION = "20260219f9f6"
SENTINEL_SDK_URL = f"https://sentinel.openai.com/sentinel/{SENTINEL_VERSION}/sdk.js"
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
DEFAULT_SEC_CH_UA = '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUICKJS_SCRIPT = os.path.join(BASE_DIR, "openai_sentinel_quickjs.js")
_sdk_cache_path = None
_sdk_lock = threading.Lock()

_SENTINEL_WRAPPER_JS = r"""
const fs = require('fs');
const timeoutMs = Number(process.env.OPENAI_SENTINEL_VM_TIMEOUT_MS || '10000');
const sdkFile = process.env.OPENAI_SENTINEL_SDK_FILE;
const scriptFile = process.env.OPENAI_SENTINEL_QUICKJS_SCRIPT;
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', async () => {
  try {
    const payload = JSON.parse(input || '{}');
    globalThis.__payload_json = JSON.stringify(payload);
    globalThis.__sdk_source = fs.readFileSync(sdkFile, 'utf8');
    globalThis.__vm_done = false;
    globalThis.__vm_output_json = '';
    globalThis.__vm_error = '';
    const script = fs.readFileSync(scriptFile, 'utf8');
    eval(script);
    const started = Date.now();
    while (!globalThis.__vm_done) {
      if ((Date.now() - started) > timeoutMs) throw new Error('QuickJS timeout');
      await new Promise((resolve) => setTimeout(resolve, 1));
    }
    if (String(globalThis.__vm_error || '').trim()) throw new Error(String(globalThis.__vm_error));
    process.stdout.write(String(globalThis.__vm_output_json || ''));
  } catch (err) {
    process.stderr.write(err && err.stack ? String(err.stack) : String(err));
    process.exit(1);
  }
});
""".strip()


def _fnv_mixed(text: str) -> str:
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 2246822507) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 3266489909) & 0xFFFFFFFF
    h ^= h >> 16
    return format(h & 0xFFFFFFFF, "08x")


def _b64_json(data) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _sentinel_fingerprint(ua: str) -> list:
    date_str = time.strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)", time.gmtime())
    nav = random.choice([
        "vendorSub", "productSub", "vendor", "maxTouchPoints", "scheduling",
        "userActivation", "doNotTrack", "geolocation", "connection", "plugins",
        "mimeTypes", "pdfViewerEnabled", "webkitTemporaryStorage",
        "webkitPersistentStorage", "hardwareConcurrency", "cookieEnabled",
        "credentials", "mediaDevices", "permissions", "locks", "ink",
    ]) + "−undefined"
    doc = random.choice(["location", "implementation", "URL", "documentURI", "compatMode"])
    win = random.choice(["Object", "Function", "Array", "Number", "parseFloat", "undefined"])
    time_origin = time.time() * 1000 - random.uniform(1000, 50000)
    return [
        "1920x1080", date_str, 4294705152, random.random(), ua, SENTINEL_SDK_URL,
        None, None, "en-US", "en-US,en", random.random(), nav, doc, win,
        random.uniform(1000, 50000), str(uuid.uuid4()), "",
        random.choice([4, 8, 12, 16]), time_origin,
    ]


def _sentinel_requirements_token(ua: str) -> str:
    config = _sentinel_fingerprint(ua)
    config[3] = 1
    config[9] = round(random.uniform(5, 50))
    return "gAAAAAC" + _b64_json(config)


def _sentinel_solve_pow(seed: str, difficulty: str, config: list, max_attempts: int = 500000) -> str:
    start = time.time()
    for nonce in range(max_attempts):
        config[3] = nonce
        config[9] = round((time.time() - start) * 1000)
        encoded = _b64_json(config)
        if _fnv_mixed(seed + encoded)[:len(difficulty)] <= difficulty:
            return encoded + "~S"
    return ""


def _ensure_sentinel_sdk(sess) -> str:
    global _sdk_cache_path
    with _sdk_lock:
        if _sdk_cache_path and os.path.exists(_sdk_cache_path):
            return _sdk_cache_path
        cache_dir = os.path.join(tempfile.gettempdir(), "openai-sentinel-sdk", SENTINEL_VERSION)
        os.makedirs(cache_dir, exist_ok=True)
        sdk_file = os.path.join(cache_dir, "sdk.js")
        if os.path.exists(sdk_file) and os.path.getsize(sdk_file) > 0:
            _sdk_cache_path = sdk_file
            return sdk_file
        resp = sess.get(SENTINEL_SDK_URL, headers={
            "accept": "*/*", "referer": "https://auth.openai.com/",
            "sec-fetch-dest": "script", "sec-fetch-mode": "no-cors", "sec-fetch-site": "same-site",
        }, timeout=20)
        if resp.status_code != 200 or not resp.content:
            raise RuntimeError(f"下载 sdk.js 失败: HTTP {resp.status_code}")
        with open(sdk_file, "wb") as f:
            f.write(resp.content)
        _sdk_cache_path = sdk_file
        return sdk_file


def _run_quickjs_action(action: str, sdk_file: str, payload: dict, timeout_ms: int = 45000) -> dict:
    body = dict(payload)
    body["action"] = action
    node = (os.getenv("OPENAI_SENTINEL_NODE_PATH", "") or "node").strip()
    proc = subprocess.run(
        [node, "-e", _SENTINEL_WRAPPER_JS],
        input=json.dumps(body, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8",
        timeout=max(10, timeout_ms // 1000 + 5),
        env={**os.environ,
             "OPENAI_SENTINEL_SDK_FILE": sdk_file,
             "OPENAI_SENTINEL_QUICKJS_SCRIPT": QUICKJS_SCRIPT,
             "OPENAI_SENTINEL_VM_TIMEOUT_MS": str(min(timeout_ms, 30000))},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"QuickJS 执行失败: {(proc.stderr or proc.stdout or '').strip()[:300]}")
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("QuickJS 返回空输出")
    return json.loads(out)


def _fetch_sentinel_challenge(sess, did: str, flow: str, request_p: str) -> dict:
    resp = sess.post(
        SENTINEL_REQ_URL,
        data=json.dumps({"p": request_p, "id": did, "flow": flow}, separators=(",", ":")),
        headers={
            "origin": "https://sentinel.openai.com",
            "referer": f"{SENTINEL_REF}?sv={SENTINEL_VERSION}",
            "content-type": "text/plain;charset=UTF-8", "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"/sentinel/req HTTP {resp.status_code}")
    return resp.json()


def _sentinel_via_quickjs(did: str, flow: str, ua: str):
    if not os.path.exists(QUICKJS_SCRIPT):
        log.warning("缺少 openai_sentinel_quickjs.js，跳过 QuickJS")
        return None
    sess = requests.Session(impersonate="chrome")
    try:
        sdk_file = _ensure_sentinel_sdk(sess)
        req = _run_quickjs_action("requirements", sdk_file, {"device_id": did, "user_agent": ua})
        request_p = str(req.get("request_p") or "").strip()
        if not request_p:
            return None
        challenge = _fetch_sentinel_challenge(sess, did, flow, request_p)
        c_value = str(challenge.get("token") or "").strip()
        if not c_value:
            return None
        solved = _run_quickjs_action("solve", sdk_file,
                                     {"device_id": did, "user_agent": ua,
                                      "request_p": request_p, "challenge": challenge})
        final_p = str(solved.get("final_p") or solved.get("p") or "").strip()
        t_raw = solved.get("t")
        t_value = "" if t_raw is None else str(t_raw).strip()
        if not final_p or not t_value:
            log.warning(f"sentinel({flow}) QuickJS 缺 p/t (p={len(final_p)} t={len(t_value)})")
            return None
        log.info(f"sentinel({flow}) QuickJS 成功 (p={len(final_p)} t={len(t_value)} c={len(c_value)})")
        return json.dumps({"p": final_p, "t": t_value, "c": c_value, "id": did, "flow": flow},
                          separators=(",", ":"), ensure_ascii=False)
    finally:
        try:
            sess.close()
        except Exception:
            pass


def _sentinel_pure_python(did: str, flow: str, ua: str = DEFAULT_UA) -> str:
    token, required, seed, difficulty = "", False, "", "0"
    try:
        resp = requests.post(
            SENTINEL_REQ_URL,
            data=json.dumps({"p": _sentinel_requirements_token(ua), "id": did, "flow": flow},
                            separators=(",", ":")),
            headers={
                "content-type": "text/plain;charset=UTF-8", "accept": "*/*",
                "referer": SENTINEL_REF, "origin": "https://sentinel.openai.com",
                "user-agent": ua, "sec-ch-ua": DEFAULT_SEC_CH_UA,
                "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            },
            impersonate="chrome", timeout=30,
        )
        log.info(f"sentinel({flow}): {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            token = str(data.get("token") or "").strip()
            pow_data = data.get("proofofwork") or {}
            required = bool(pow_data.get("required"))
            seed = str(pow_data.get("seed") or "").strip()
            difficulty = str(pow_data.get("difficulty") or "0").strip()
    except Exception as e:
        log.warning(f"sentinel({flow}) 异常: {e}")

    config = _sentinel_fingerprint(ua)
    if required and seed:
        p_value = _sentinel_solve_pow(seed, difficulty, config) or ("gAAAAAC" + _b64_json(config))
    else:
        p_value = "gAAAAAC" + _b64_json(config)

    return json.dumps({"p": p_value, "t": "", "c": token, "id": did, "flow": flow},
                      separators=(",", ":"), ensure_ascii=False)


def gen_sentinel(did: str, flow: str, ua: str = DEFAULT_UA) -> str:
    if not os.environ.get("OPENAI_SENTINEL_DISABLE_QUICKJS"):
        try:
            token = _sentinel_via_quickjs(did, flow, ua)
            if token:
                return token
            log.warning(f"sentinel({flow}) QuickJS 未成功，回退纯 Python")
        except Exception as e:
            log.warning(f"sentinel({flow}) QuickJS 异常，回退纯 Python: {e}")
    return _sentinel_pure_python(did, flow, ua)


# ========== 请求头 ==========

def _trace_headers() -> dict:
    parent_id = random.getrandbits(64)
    return {
        "traceparent": f"00-{uuid.uuid4().hex}-{parent_id:016x}-01",
        "tracestate": "dd=s:1;o:rum",
        "x-datadog-origin": "rum",
        "x-datadog-parent-id": str(parent_id),
        "x-datadog-sampling-priority": "1",
        "x-datadog-trace-id": str(random.getrandbits(64)),
    }


def _auth_headers(did: str, referer: str, sentinel: str = "") -> dict:
    h = {
        "accept": "application/json", "content-type": "application/json",
        "accept-language": "en-US,en;q=0.9", "referer": referer,
        "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
    }
    if did:
        h["oai-device-id"] = did
    h.update(_trace_headers())
    if sentinel:
        h["openai-sentinel-token"] = sentinel
    return h


# ========== 网页注册流程 ==========

def _follow_to_session(s, cont: str):
    """跟随 continue_url 重定向链，直到 chatgpt 回调写入 __Secure-next-auth.session-token。"""
    if not cont:
        return
    if cont.startswith("/"):
        cont = f"{AUTH_BASE}{cont}"
    url = cont
    for _ in range(20):
        resp = s.get(url, allow_redirects=False)
        if s.cookies.get("__Secure-next-auth.session-token"):
            return
        if resp.status_code not in (301, 302, 303, 307, 308):
            return
        loc = resp.headers.get("Location", "")
        if not loc:
            return
        if loc.startswith("/"):
            p = urllib.parse.urlparse(url)
            loc = f"{p.scheme}://{p.netloc}{loc}"
        if "chatgpt.com/api/auth/callback" in loc:
            s.get(loc, allow_redirects=True)
            return
        if "localhost" in loc:
            return
        url = loc


def register_and_get_token(cfg: dict) -> str:
    """注册一个 ChatGPT 网页账号并返回 accessToken；失败返回 None。"""
    s = requests.Session(impersonate="chrome")
    # 预设 oai-did 并全程复用(与 sentinel id / oai-device-id 头保持一致)
    did = str(uuid.uuid4())
    s.cookies.set("oai-did", did, domain=".auth.openai.com")
    s.cookies.set("oai-did", did, domain="auth.openai.com")

    mail = create_email(cfg)
    email = mail["address"]
    email_id = mail["id"]
    log.info(f"邮箱: {email}")
    password = generate_random_password()
    log.info(f"密码: {password}")

    # 1. csrf
    r = s.get(f"{CHATGPT_BASE}/api/auth/csrf",
              headers={"accept": "application/json", "referer": f"{CHATGPT_BASE}/auth/login"})
    csrf = r.json().get("csrfToken", "") if r.status_code == 200 else ""
    if not csrf:
        log.error(f"获取 csrfToken 失败: {r.status_code}")
        return None

    # 2. signin/openai -> 网页 client_id + chatgpt.com 回调的授权 URL
    r = s.post(f"{CHATGPT_BASE}/api/auth/signin/openai",
               data={"csrfToken": csrf, "callbackUrl": f"{CHATGPT_BASE}/", "json": "true"},
               headers={"accept": "application/json",
                        "content-type": "application/x-www-form-urlencoded",
                        "origin": CHATGPT_BASE, "referer": f"{CHATGPT_BASE}/auth/login"},
               allow_redirects=False)
    if r.status_code == 200:
        auth_url = r.json().get("url", "")
    elif r.status_code in (301, 302, 303):
        auth_url = r.headers.get("Location", "")
    else:
        auth_url = ""
    if not auth_url:
        log.error(f"获取 auth_url 失败: {r.status_code} {r.text[:200]}")
        return None

    # 指示注册流程
    auth_url += ("&" if "?" in auth_url else "?") + "screen_hint=signup"

    # 3. GET auth_url -> 建立网页登录会话 (login_session)
    s.get(auth_url, allow_redirects=True)
    log.info(f"oai-did: {did}")

    # 4. 提交邮箱 (screen_hint=signup)
    signup_body = json.dumps({"username": {"value": email, "kind": "email"}, "screen_hint": "signup"})
    r = s.post(f"{AUTH_BASE}/api/accounts/authorize/continue",
               headers=_auth_headers(did, f"{AUTH_BASE}/create-account",
                                     gen_sentinel(did, "authorize_continue")),
               data=signup_body)
    log.info(f"signup: {r.status_code}")
    if r.status_code != 200:
        log.error(f"signup 失败: {r.text[:300]}")
        return None

    # 5. 设密码注册
    r = s.post(f"{AUTH_BASE}/api/accounts/user/register",
               headers=_auth_headers(did, f"{AUTH_BASE}/create-account/password",
                                     gen_sentinel(did, "username_password_create")),
               data=json.dumps({"password": password, "username": email}))
    log.info(f"register: {r.status_code}")
    if r.status_code not in (200, 301, 302):
        log.error(f"register 失败: {r.text[:300]}")
        return None

    # 6. 触发邮箱验证码
    s.post(f"{AUTH_BASE}/api/accounts/email-otp/send",
           headers=_auth_headers(did, f"{AUTH_BASE}/create-account/password",
                                 gen_sentinel(did, "authorize_continue")),
           data="{}")
    log.info("email-otp/send 触发完成")

    code = get_oai_code(email_id, cfg)
    if not code:
        log.error("获取验证码超时")
        return None
    log.info(f"验证码: {code}")

    # 7. 校验验证码
    r = s.post(f"{AUTH_BASE}/api/accounts/email-otp/validate",
               headers=_auth_headers(did, f"{AUTH_BASE}/email-verification",
                                     gen_sentinel(did, "authorize_continue")),
               data=json.dumps({"code": code}))
    otp_json = {}
    try:
        otp_json = r.json()
    except Exception:
        pass
    cont = str(otp_json.get("continue_url") or "")
    page = (otp_json.get("page") or {}).get("type", "")
    log.info(f"validate-otp: {r.status_code} page={page} continue_url={cont}")

    # 8. 创建账号 (about-you)
    r = s.post(f"{AUTH_BASE}/api/accounts/create_account",
               headers=_auth_headers(did, f"{AUTH_BASE}/about-you",
                                     gen_sentinel(did, "create_account")),
               data=json.dumps({"name": "Neo", "birthdate": "2000-02-20"}))
    log.info(f"create_account: {r.status_code}")
    if r.status_code == 200:
        cont = str(r.json().get("continue_url") or cont)
    else:
        log.warning(f"create_account 非 200: {r.text[:300]}")

    # 9. 跟随 continue_url -> chatgpt 回调写入 session-token
    _follow_to_session(s, cont)
    if not s.cookies.get("__Secure-next-auth.session-token"):
        log.warning("未拿到 session-token")

    # 10. 取 accessToken
    r = s.get(f"{CHATGPT_BASE}/api/auth/session",
              headers={"accept": "application/json", "referer": f"{CHATGPT_BASE}/"})
    token = r.json().get("accessToken", "") if r.status_code == 200 else ""
    if not token:
        log.error(f"未获取到 accessToken: {r.status_code} {r.text[:200]}")
        return None
    log.info(f"accessToken 获取成功 (长度 {len(token)})")
    return token


# ========== 单任务 / 入口 ==========

def register_one(index: int, total: int, cfg: dict) -> bool:
    log.info(f"===== 第 {index}/{total} 个账号 =====")
    try:
        token = register_and_get_token(cfg)
        if not token:
            log.warning(f"[{index}/{total}] 失败: 未拿到 token")
            return False
        token_file = cfg.get("access_token_file", "ac/tokens.txt")
        if not os.path.isabs(token_file):
            token_file = os.path.join(BASE_DIR, token_file)
        with _token_lock:
            os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
            with open(token_file, "a", encoding="utf-8") as f:
                f.write(token + "\n")
        log.info(f"[{index}/{total}] 成功, accessToken 已追加到 {token_file}")
        return True
    except Exception as e:
        log.error(f"[{index}/{total}] 失败: {e}")
        return False


def main():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    count = cfg.get("count", 1)
    max_workers = cfg.get("max_workers", 1)
    setup_logging(cfg.get("log_to_file", 0))

    log.info(f"开始注册 {count} 个账号, 并发数 {max_workers}")

    success = 0
    if max_workers <= 1:
        for i in range(1, count + 1):
            if register_one(i, count, cfg):
                success += 1
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="worker") as pool:
            futures = [pool.submit(register_one, i, count, cfg) for i in range(1, count + 1)]
            for fut in as_completed(futures):
                if fut.result():
                    success += 1

    log.info(f"完成: 成功 {success}/{count}")


if __name__ == "__main__":
    main()
