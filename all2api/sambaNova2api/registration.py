import requests
import secrets
import random
import string
from fake_useragent import UserAgent


def generate_random_string(length=5):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def register_and_get_access_token(email, password):
    session = requests.Session()
    ua = UserAgent()
    common_headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "origin": "https://cloud.sambanova.ai",
        "referer": "https://cloud.sambanova.ai/",
        "user-agent": ua.random
    }

    config_url = "https://cloud.sambanova.ai/api/config"
    response_config = session.get(config_url, headers=common_headers)
    if response_config.status_code != 200:
        print("获取配置信息失败:", response_config.text)
        return None
    config_data = response_config.json()
    client_id = config_data.get("clientId")
    issuer_base_url = config_data.get("issuerBaseUrl")
    redirect_url = config_data.get("redirectURL")
    print("Client ID:", client_id)
    print("Issuer Base URL:", issuer_base_url)
    print("Redirect URL:", redirect_url)

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    print("生成的 state:", state)
    print("生成的 nonce:", nonce)

    first_name = generate_random_string()
    last_name = generate_random_string()
    print("生成的 first_name:", first_name)
    print("生成的 last_name:", last_name)

    signup_url = f"https://{issuer_base_url}/dbconnections/signup"
    headers_signup = {
        **common_headers,
        "auth0-client": "eyJuYW1lIjoibG9jay5qcyIsInZlcnNpb24iOiIxMi4zLjAiLCJlbnYiOnsiYXV0aDAuanMiOiI5LjIyLjEifX0="
    }
    data_signup = {
        "client_id": client_id,
        "connection": "Username-Password-Authentication",
        "email": email,
        "password": password,
        "user_metadata": {
            "first_name": first_name,
            "last_name": last_name,
            "company": "hbc",
            "country": "Japan",
            "job_title": "Engineering Leadership",
            "opted_in_to_marketing_emails__c": "false"
        }
    }
    response_signup = session.post(signup_url, headers=headers_signup, json=data_signup)
    print("Step 2: 状态码:", response_signup.status_code)
    if response_signup.status_code != 200:
        print("Step 2: 注册失败:", response_signup.text)
        return None
    signup_data = response_signup.json()
    print("Step 2: 注册成功:", signup_data)

    authenticate_url = f"https://{issuer_base_url}/co/authenticate"
    headers_auth = {
        **common_headers,
        "auth0-client": "eyJuYW1lIjoibG9jay5qcyIsInZlcnNpb24iOiIxMi4zLjAiLCJlbnYiOnsiYXV0aDAuanMiOiI5LjIyLjEifX0=",
        "content-type": "application/json",
        "cache-control": "no-cache"
    }
    data_auth = {
        "client_id": client_id,
        "username": email,
        "password": password,
        "realm": "Username-Password-Authentication",
        "credential_type": "http://auth0.com/oauth/grant-type/password-realm"
    }
    response_auth = session.post(authenticate_url, headers=headers_auth, json=data_auth)
    print("Step 3: 状态码:", response_auth.status_code)
    if response_auth.status_code != 200:
        print("Step 3: 认证失败:", response_auth.text)
        return None

    authorize_url = f"https://{issuer_base_url}/authorize"
    params_code = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_url,
        "scope": "openid profile email",
        "nonce": nonce,
        "state": state,
        "connection": "Username-Password-Authentication",
        "realm": "Username-Password-Authentication",
    }
    headers_code = {
        **common_headers,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    }
    response_code = session.get(authorize_url, params=params_code, headers=headers_code, allow_redirects=False)
    print("Step 4: 状态码:", response_code.status_code)
    if response_code.status_code == 302:
        location = response_code.headers.get("location")
        print("Step 4: Location:", location)
        if "verify" in location and "email" in location:
            print("注册成功！请检查邮箱进行验证。")
            return True
        else:
            print("注册失败：未收到邮箱验证提示")
            return False
    else:
        print("Step 4: 获取授权码失败")
        return False


if __name__ == "__main__":
    email = ""
    password = ""
    result = register_and_get_access_token(email, password)
    print('\n注册成功！请检查邮箱进行验证。' if result else "注册失败")