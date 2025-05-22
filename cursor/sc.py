import requests
import random
import string
import re
import time


# 生成随机的5位小写字母和数字组合
def generate_random_code(length=5):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# 从响应文本中提取referral链接
def extract_referral_link(text):
    # 匹配形如https://cursor.com/referral?code=VWF8EBCTHVDT的链接
    regex = r'https://cursor\.com/referral\?code=[A-Z0-9]+'
    matches = re.findall(regex, text)
    return matches[0] if matches else None


# 主函数
def start_fetching(cookies_str):
    print("开始执行，每0.5秒尝试一次...")
    print("按Ctrl+C可以停止执行")

    # 解析Cookie字符串为字典
    cookies = {}
    for item in cookies_str.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            cookies[key] = value

    # 请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Referer': 'https://www.perplexity.ai/'
    }

    try:
        while True:
            # 生成随机五位码
            random_code = generate_random_code()

            try:
                # 构建URL，将rsc参数替换为随机生成的代码
                url = f'https://www.perplexity.ai/account/pro-perks?_rsc={random_code}'

                # 打印请求信息
                print(f"🔴 GET {url}", end=' ')

                # 发送请求
                response = requests.get(url, headers=headers, cookies=cookies)

                # 打印响应状态码
                print(f"{response.status_code} ({response.reason})")

                # 获取响应文本
                response_text = response.text

                # 提取referral链接
                referral_link = extract_referral_link(response_text)

                # 如果找到链接，则输出
                if referral_link:
                    print(f"{referral_link}")
                    # 找到链接后不停止，继续尝试获取更多链接

            except Exception as e:
                # 出错时显示错误信息
                print(f"请求失败: {str(e)}")

            # 暂停0.5秒
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n已停止自动获取链接")


if __name__ == "__main__":
    # 用户提供的Cookie
    cookies_str = """pplx.visitor-id=3576445d-fdf1-49a5-9283-ce046eaff37a; _gcl_au=1.1.521350169.1747234386; __podscribe_perplexityai_referrer=_; __podscribe_perplexityai_landing_url=https://www.perplexity.ai/referrals/XF0W8L9I?__cf_chl_tk=kga570DF95D5_hecEOAcweNHJ_ioFrYo5iDxtoTtzF0-1747234375-1.0.1.1-489sdJXnJcWNi9XyFvcpLD94eX6qwo1ZUn0xBSzMhp8; _fbp=fb.1.1747234386707.508118285422951949; intercom-device-id-l2wyozh0=db68d0a0-58db-4f86-b1e4-7f467c340f3f; __cf_bm=UvDnWsZModtHCjplfSaUP_BwinSqdjoOKm6x9ZtECFM-1747919807-1.0.1.1-yuXy1L1Atowb_782CqRtdRnq_bYDfMBJFN5NfHIWkPhysWuwaIa5.SrAUY7OOQPlRHNSObPBf9hXoljBbL.OlMXW_mNMUwmxWOYnMUHw7QA; pplx.session-id=687058d8-735b-4285-b642-3e0fa46acef8; __cflb=02DiuDyvFMmK5p9jVbVnMNSKYZhUL9aGm7joC6BKxAJRS; pplx.search-mode-layout-variant=enabled; next-auth.csrf-token=83a221fb65b1be025159b56622f8af44077b84ecf3b952e4331b57f2fcfa3abf%7C08b8dfd888b14dcdd5f57bcd6f9ff41289c1835cfb8df23cfdd3cac7ada2793d; intercom-session-l2wyozh0=Wm9lQlpUcnN0bTBQbEhVRjV2MDJCT2VQTFczQTd2QzNhNGUyN1ZTTFhFeERSU1BjS2lycHBtQkFVakZOQjBZdS9zR0k5QXYxNC94TmZlaEFnQndJMHNiNE5ieThvbG44RlhKd2ZkQWdGbms9LS14dG1ETVhlV1d5RlQvdVZVbXdmQ213PT0=--c1117693275c5efedd57b288617140b03ab023e0; pplx.is-incognito=false; sidebarHiddenHubs=[]; next-auth.callback-url=https%3A%2F%2Fwww.perplexity.ai%2Fapi%2Fauth%2Fsignin-callback%3Fredirect%3Dhttps%253A%252F%252Fwww.perplexity.ai%252F%253Flogin-source%253DfloatingSignup; cf_clearance=FFLxRIlXb8Pz.IUf.NcyagO7rkMU8HoYjUK7laDY0co-1747920183-1.2.1.1-wYrF7qa55i06BEKWL3AHyuEU1r0X57oGWwHdbho.mumgOcpTHynU1M3GwPg3oFsz6ik0uLQK5p9sK9veQPTYJxfZsa6_gqzUWQESqfaG0S0qFvrLMKDvEGHLm2Urf0hCdGm4nv8qPcfVicASV3ntYkLX._42BabuBIg2pLAu.kOEm8Ih8r4Q8w_NYCzo2UtdGeYoGhulimrpcEYlxGDvDTXt8FY5Ox0TKVVOk2dqgVs9VXgCTK06YmTbGpplwmIlkcfh3iGEDS4376kb1B_8mt1WnJhto08OU_eI0GQoaB.rcmigPDBb_BSs3hlnSsL3U2kNhU_2.N2H94o.VSVBRkpogJqCdvMeSurKgFCuXf.ZDcZqUe8wvXF7FdvFnGY0; _rdt_uuid=1747234386522.0d93453c-a075-4812-96b8-39a1425d5cfb; pplx.metadata={%22qc%22:2%2C%22qcu%22:0%2C%22qcm%22:0%2C%22qcc%22:0%2C%22qcr%22:0%2C%22qcdr%22:0%2C%22qcs%22:0%2C%22qcd%22:0%2C%22hli%22:true%2C%22hcga%22:false%2C%22hcds%22:false%2C%22hso%22:true%2C%22hfo%22:true}; __Secure-next-auth.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..Ram0LVVIMvLp2oB7.sbPyTaYJfBiVvTTi0RZSjlU0wNGkKqaBbU54uyeytDvFHiAOsqYHNcg5VCoB57dtnbQ0wv7feczmVZG_FVHH7HPkofwQz3gokF1bZ2kPrwIqX879sADgsd5nLxIG8W5MFjXlGRvIyt_Qmp7fq_OGSmykI_1hE8jTL2KqLqlIPYLoMLD6p-LWR3_WCHwkTx-aAAgWFgLykERyARqo8wzFkNvpVVgdMfsqM1c658gxQsrDxmFYdd0paTsR_qo48k-SheJiZ_-9y1QjbObGzz62YfsBDpB0nRLrkg2kWPxO-rzLHVzlu8mk7mvavU_8524yUgOyJiJuL2WiK1QYZOKFnE3AovuY63Ob0Y_yAH93LriNmOBggD7aPUYstY0NsnVBFRE6J91hpZZ-G7rb59FJaa9WR0E5NETS1L9wRIpplQ.qU3rhWx-etWikVZ2EUsqdw; AWSALB=a6r34sJfLps+NQj1aBgXJALThmLZZ2a/DWMzDzK7Z/OapwSczzfvBT2/NX7LYeqogl9bCwpOHhNWgtE+im9ufbp1kGxXQQd7Z/lF6ve8qo+6BzaPAxdnLi8rVfpi; AWSALBCORS=a6r34sJfLps+NQj1aBgXJALThmLZZ2a/DWMzDzK7Z/OapwSczzfvBT2/NX7LYeqogl9bCwpOHhNWgtE+im9ufbp1kGxXQQd7Z/lF6ve8qo+6BzaPAxdnLi8rVfpi; _dd_s=aid=6b0993d9-9ad3-4489-9bbd-8029a9d56b61&rum=0&expire=1747921147391&logs=0"""

    # 开始获取链接
    start_fetching(cookies_str) 