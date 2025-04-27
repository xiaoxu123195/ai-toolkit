"""
MIT License

Copyright (c) 2025 Neuroplexus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import requests
import json
import random
import string
from concurrent.futures import ThreadPoolExecutor
import time
from faker import Faker
from TempMail import TempMail
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

fake = Faker()
tm = TempMail()

proxy = "替换为你的代理, 最好是动态代理"

YESCAPTCHA_API_KEY = "替换为你的 yescaptcha key"
VERIFY_EMAIL = False  # Set to False to skip email verification


def generate_random_gmail():
    """Generates a random 7-10 digit Gmail address."""
    length = random.randint(7, 10)
    random_str = ''.join(random.choice(string.digits) for _ in range(length))
    return f"{random_str}@gmail.com"


def get_token():
    url = "https://near-bobcat-75.deno.dev/createTask"
    token = YESCAPTCHA_API_KEY

    payload = {
        "clientKey": token,
        "task": {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": "https://platform.kluster.ai",
            "websiteKey": "6a2a0f82-62b8-4b62-b43e-ff724da88858",
        },
    }

    # Create task
    try:
        result = requests.post(url, json=payload).json()
        taskId = result.get("taskId")
        if not taskId:
            print("Failed to create task:", result)
            return None
        print(f"Created a task: {taskId}")

        # Poll for result
        for i in range(100):
            time.sleep(1)
            url = "https://near-bobcat-75.deno.dev/getTaskResult"
            payload = {"clientKey": token, "taskId": taskId}
            resp = requests.post(url, json=payload)
            result = resp.json()

            # print(f"Polling for result: {result}")

            if result.get("status") == "ready":
                if "solution" in result and "gRecaptchaResponse" in result["solution"]:
                    print("Captcha solved:", result["solution"]["gRecaptchaResponse"])
                    return result["solution"]["gRecaptchaResponse"]

            elif result.get("errorId") == 1:
                print("Task failed:", resp.text)
                return None

            else:
                print(f"Polling for result: {result}")

        print("Timeout waiting for captcha solution")
        return None

    except Exception as e:
        print(f"Error in get_token: {e}")
        return None


def generate_random_string(length, include_special=False):
    letters = string.ascii_letters + string.digits
    if include_special:
        special_chars = "!@#$%^&*"
        letters += special_chars
    return "".join(random.choice(letters) for _ in range(length))


def generate_password():
    password = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.ascii_lowercase)
            + random.choice(string.digits)
            + random.choice("!@#$%^&*")
            + generate_random_string(8, True)
    )
    password_list = list(password)
    random.shuffle(password_list)
    return "".join(password_list)


def generate_random_email():
    if not VERIFY_EMAIL:
        return generate_random_gmail()
    inbox = tm.createInbox()
    return inbox


def generate_random_first_name():
    return fake.name().split(" ")[0]


def generate_random_last_name():
    return fake.name().split(" ")[1]


def register_account():
    url = "https://api.kluster.ai/v1/user/register"

    # Get captcha token first
    captcha_token = get_token()
    if captcha_token is None:
        print("Failed to get captcha token, skipping registration")
        return None

    # 设置请求头
    headers = {
        "authority": "api.kluster.ai",
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "origin": "https://platform.kluster.ai",
        "referer": "https://platform.kluster.ai/",
        "sec-ch-ua": '"Chromium";v="134", "Not A Brand";v="24", "Google Chrome";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    if VERIFY_EMAIL:
        inbox = generate_random_email()
        email = inbox.address
    else:
        email = generate_random_email()  # This will now return a Gmail address
        inbox = None

    password = generate_password()
    firstName = generate_random_first_name()
    lastName = generate_random_last_name()

    data = {
        "captcha": captcha_token,  # Use the validated token
        "email": email,
        "password": password,
        "firstName": firstName,
        "lastName": lastName,
        "useHcaptcha": True,
    }

    try:
        response = requests.post(url, headers=headers, json=data, proxies={"http": proxy, "https": proxy}, verify=False)

        if response.status_code == 200:
            # 提交调查问卷
            survey_url = "https://api.kluster.ai/v1/survey/answers/batch"
            survey_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.5",
                "Content-Type": "application/json",
                "Origin": "https://platform.kluster.ai",
                "DNT": "1",
                "Sec-GPC": "1",
                "Connection": "keep-alive",
                "Referer": "https://platform.kluster.ai/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "Priority": "u=0",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "TE": "trailers"
            }

            survey_data = {
                "questionAnswers": [
                    {
                        "question": "What role best describes you?",
                        "answer": "Other"
                    },
                    {
                        "question": "Do you have a gen AI app in production?",
                        "answer": "No, just exploring"
                    },
                    {
                        "question": "How did you hear about us?",
                        "answer": "Other"
                    }
                ]
            }

            requests.post(
                survey_url,
                headers=survey_headers,
                cookies=response.cookies,
                json=survey_data
            )

            accounts_file = SCRIPT_DIR / "accounts.csv"
            with open(accounts_file, "a", encoding="utf-8") as f:
                f.write(f"{email},{password},{firstName},{lastName}\n")
            print(f"注册成功! Email: {email} | Password: {password}")

            if VERIFY_EMAIL:
                return [inbox, response.cookies]
            return [None, response.cookies]
        else:
            print(f"注册失败! 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")

    except Exception as e:
        print(f"发生错误: {str(e)}")


def verify_email(inbox, cookies):
    emails = tm.getEmails(inbox)
    for email in emails:
        if "kluster.ai" in email.subject:
            pattern = r"https://platform\.kluster\.ai/email/([\w-]+)(?=\]|\s|$)"
            urls = re.findall(pattern, email.body)
            url = urls[0]
            print(url)

            response = requests.post(
                "https://api.kluster.ai/v1/user/validateEmail",
                cookies=cookies,
                json={"verificationCode": url},
            )
            if response.status_code == 200:
                print(f"验证成功! 验证码: {url}")
                return True
            else:
                print(f"验证失败! 状态码: {response.status_code}")
                print(f"错误信息: {response.text}")
                return False
    # [https://platform.kluster.ai/email/okms8klvzbz4ihy2d2h6itov]


def register_and_verify():
    inbox, cookies = register_account()
    return [verify_email(inbox, cookies), cookies]


def get_new_api_key(cookies):
    response = requests.post(
        "https://api.kluster.ai/v1/user/apiKeys",
        cookies=cookies,
        json={"name": "Bulk Key"},
    )
    if response.status_code == 200:
        return response.json()["key"]
    else:
        print(f"获取新API密钥失败! 状态码: {response.status_code}")
        print(f"错误信息: {response.text}")
        return None


def register_with_delay():
    try:
        # 1. 注册并验证账号
        result = register_account()
        if not result:
            print("注册失败，跳过后续步骤")
            return

        inbox, cookies = result

        # 2. 如果需要验证邮箱
        if VERIFY_EMAIL:
            status = verify_email(inbox, cookies)
            if not status:
                print("邮箱验证失败，跳过创建API key")
                return

        # 3. 创建API key
        key_result = get_new_api_key(cookies)
        if not key_result:
            print("创建API key失败")
            return

        # 4. 保存API key
        keys_file = SCRIPT_DIR / "keys.txt"
        with open(keys_file, "a", encoding="utf-8") as f:
            f.write(f"{key_result}\n")
        print(f"新API密钥: {key_result}")

        # 5. 添加随机延迟
        time.sleep(random.uniform(1, 3))

        return True

    except Exception as e:
        print(f"注册过程发生错误: {str(e)}")
        return False


def main():
    print("""
MIT License

Copyright (c) 2025 Neuroplexus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

================
          _____                    _____            _____                    _____                _____                    _____                    _____          
         /\    \                  /\    \          /\    \                  /\    \              /\    \                  /\    \                  /\    \         
        /::\____\                /::\____\        /::\____\                /::\    \            /::\    \                /::\    \                /::\    \        
       /:::/    /               /:::/    /       /:::/    /               /::::\    \           \:::\    \              /::::\    \              /::::\    \       
      /:::/    /               /:::/    /       /:::/    /               /::::::\    \           \:::\    \            /::::::\    \            /::::::\    \      
     /:::/    /               /:::/    /       /:::/    /               /:::/\:::\    \           \:::\    \          /:::/\:::\    \          /:::/\:::\    \     
    /:::/____/               /:::/    /       /:::/    /               /:::/__\:::\    \           \:::\    \        /:::/__\:::\    \        /:::/__\:::\    \    
   /::::\    \              /:::/    /       /:::/    /                \:::\   \:::\    \          /::::\    \      /::::\   \:::\    \      /::::\   \:::\    \   
  /::::::\____\________    /:::/    /       /:::/    /      _____    ___\:::\   \:::\    \        /::::::\    \    /::::::\   \:::\    \    /::::::\   \:::\    \  
 /:::/\:::::::::::\    \  /:::/    /       /:::/____/      /\    \  /\   \:::\   \:::\    \      /:::/\:::\    \  /:::/\:::\   \:::\    \  /:::/\:::\   \:::\____\ 
/:::/  |:::::::::::\____\/:::/____/       |:::|    /      /::\____\/::\   \:::\   \:::\____\    /:::/  \:::\____\/:::/__\:::\   \:::\____\/:::/  \:::\   \:::|    |
\::/   |::|~~~|~~~~~     \:::\    \       |:::|____\     /:::/    /\:::\   \:::\   \::/    /   /:::/    \::/    /\:::\   \:::\   \::/    /\::/   |::::\  /:::|____|
 \/____|::|   |           \:::\    \       \:::\    \   /:::/    /  \:::\   \:::\   \/____/   /:::/    / \/____/  \:::\   \:::\   \/____/  \/____|:::::\/:::/    / 
       |::|   |            \:::\    \       \:::\    \ /:::/    /    \:::\   \:::\    \      /:::/    /            \:::\   \:::\    \            |:::::::::/    /  
       |::|   |             \:::\    \       \:::\    /:::/    /      \:::\   \:::\____\    /:::/    /              \:::\   \:::\____\           |::|\::::/    /   
       |::|   |              \:::\    \       \:::\__/:::/    /        \:::\  /:::/    /    \::/    /                \:::\   \::/    /           |::| \::/____/    
       |::|   |               \:::\    \       \::::::::/    /          \:::\/:::/    /      \/____/                  \:::\   \/____/            |::|  ~|          
       |::|   |                \:::\    \       \::::::/    /            \::::::/    /                                 \:::\    \                |::|   |          
       \::|   |                 \:::\____\       \::::/    /              \::::/    /                                   \:::\____\               \::|   |          
        \:|   |                  \::/    /        \::/____/                \::/    /                                     \::/    /                \:|   |          
         \|___|                   \/____/          ~~                       \/____/                                       \/____/                  \|___|          


Kluster 注册机
----------------
Copyright (c) 20225 Neuroplexus

此脚本按"原样"提供, 不提供任何明示或暗示的保证, 包括适销性和特定用途的适用性和非侵权性的保证.
本脚本仅用于测试和学习目的, 请勿用于非法用途, 否则后果自负.

此脚本仅作用于安全审计目的, 任何一切其他目的使用此脚本造成的后果由使用者自行承担. 
在使用此脚本前, 确保得到授权, 并在安全的测试环境中测试. 

================
    """)
    num_accounts = int(input("请输入要注册的账号数量: "))
    max_workers = int(input("请输入并发线程数量(建议3个左右，过大会触发cf盾): "))

    print(f"\n开始使用{max_workers}个线程注册{num_accounts}个账号...")

    # 创建线程池
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(register_with_delay) for _ in range(num_accounts)]
        completed = 0
        for future in futures:
            try:
                future.result()
                completed += 1
                print(f"\n进度: {completed}/{num_accounts}")
            except Exception as e:
                print(f"任务执行失败: {str(e)}")

    print(f"\n注册完成! 成功注册{completed}个账号")


if __name__ == "__main__":
    main()
