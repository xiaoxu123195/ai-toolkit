import requests
from bs4 import BeautifulSoup
import time
import socket
import socks
from fake_useragent import UserAgent
import concurrent.futures
import json
from datetime import datetime

# 初始化配置
ua = UserAgent()

# 代理网站配置
SITE_CONFIGS = {
    'proxy_scdn': {
        'url': 'https://proxy.scdn.io/text.php',
        'type': 'api',
        'parser': 'pre',
        'extractor': lambda text: [
            {
                'ip': line.split(':')[0],
                'port': line.split(':')[1].strip(),
                'type': '待检测',
                'https': '待检测'
            } for line in text.split('\n') if ':' in line
        ]
    },
    'freeproxylist': {
        'url': 'https://free-proxy-list.net/',
        'type': 'web',
        'parser': 'table.table tbody tr',
        'extractor': lambda row: {
            'ip': row.find_all('td')[0].get_text() if len(row.find_all('td')) > 0 else None,
            'port': row.find_all('td')[1].get_text() if len(row.find_all('td')) > 1 else None,
            'type': 'SOCKS5' if 'socks' in (
                row.find_all('td')[4].get_text().lower() if len(row.find_all('td')) > 4 else '') else 'HTTP',
            'https': '支持' if 'yes' in (
                row.find_all('td')[6].get_text().lower() if len(row.find_all('td')) > 6 else '') else '不支持'
        }
    },
    'proxy_list_plus': {
        'url': 'https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-{page}',
        'pages': 5,
        'type': 'web',
        'parser': 'table.bg tr.cells',
        'extractor': lambda row: {
            'ip': row.find_all('td')[1].get_text(),
            'port': row.find_all('td')[2].get_text(),
            'type': row.find_all('td')[6].get_text(),
            'https': '支持' if 'yes' in row.find_all('td')[5].get_text().lower() else '不支持'
        }
    },
    'geonode': {
        'url': 'https://proxylist.geonode.com/api/proxy-list?limit=100&page={page}',
        'pages': 5,
        'type': 'api',
        'extractor': lambda data: [
            {
                'ip': item['ip'],
                'port': item['port'],
                'type': item['protocols'][0].upper(),
                'https': '支持' if 'https' in item['protocols'] else '不支持'
            } for item in data['data']
        ]
    },
    '89ip': {
        'url': 'https://www.89ip.cn/index_{page}.html',
        'pages': 5,
        'type': 'web',
        'parser': 'table.layui-table tbody tr',
        'extractor': lambda row: {
            'ip': row.find_all('td')[0].get_text().strip(),
            'port': row.find_all('td')[1].get_text().strip(),
            'type': 'HTTP',
            'https': '待检测'
        }
    },
    'proxyscrape': {
        'url': 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
        'type': 'api',
        'extractor': lambda text: [
            {
                'ip': line.split(':')[0],
                'port': line.split(':')[1].strip(),
                'type': 'HTTP',
                'https': '待检测'
            } for line in text.split('\n') if ':' in line
        ]
    },
    'sslproxies': {
        'url': 'https://www.sslproxies.org/',
        'type': 'web',
        'parser': 'table.table tbody tr',
        'extractor': lambda row: {
            'ip': row.find_all('td')[0].get_text() if len(row.find_all('td')) > 0 else None,
            'port': row.find_all('td')[1].get_text() if len(row.find_all('td')) > 1 else None,
            'type': 'HTTPS',
            'https': '支持'
        }
    }
}


# 检测地区
def detect_region(ip: str) -> str:
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            api_url = f"https://apimobile.meituan.com/locate/v2/ip/loc?rgeo=true&ip={ip}"
            response = requests.get(api_url, timeout=5)
            data = response.json()
            rgeo = data.get('data', {}).get('rgeo', {})
            country = rgeo.get('country', '未知')
            province = rgeo.get('province', '未知')
            city = rgeo.get('city', '未知')
            return f"{country}/{province}/{city}"
        except (requests.RequestException, json.JSONDecodeError):
            print(f"检测 IP {ip} 地区信息失败，尝试第 {retries + 1} 次重试")
            retries += 1
    return "未知"


# 检测代理类型
def detect_proxy_type(proxy: str) -> str:
    ip, port = proxy.split(':')
    test_urls = [
        ('http://httpbin.org/ip', 'HTTP'),
        ('https://httpbin.org/ip', 'HTTPS')
    ]

    for url, ptype in test_urls:
        try:
            proxies = {ptype.lower(): f'{ptype.lower()}://{proxy}'}
            res = requests.get(url, proxies=proxies, timeout=5)
            if res.status_code == 200:
                return ptype
        except:
            pass

    try:
        socks.set_default_proxy(socks.SOCKS5, ip, int(port))
        socket.socket = socks.socksocket
        res = requests.get('http://httpbin.org/ip', timeout=5)
        if res.status_code == 200:
            return 'SOCKS5'
    except:
        pass

    return '未知'


# 核心爬取逻辑
def get_proxies_from_site(site: str) -> list:
    config = SITE_CONFIGS[site]
    all_proxies = []
    try:
        for page in range(1, config.get('pages', 1) + 1):
            headers = {'User-Agent': ua.random}
            url = config['url'].format(page=page) if '{page}' in config['url'] else config['url']
            print(f"正在爬取 {site} 第 {page} 页...")
            if config['type'] == 'api':
                response = requests.get(url, headers=headers, timeout=10)
                if site in ['proxy_scdn', 'proxyscrape']:
                    text = response.text
                    proxies = config['extractor'](text)
                else:
                    try:
                        data = response.json()
                        proxies = config['extractor'](data)
                    except json.JSONDecodeError:
                        print(f"警告：{site} 第 {page} 页返回的数据格式有误，跳过此页。")
                        continue
            else:
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                rows = soup.select(config['parser'])
                proxies = [config['extractor'](row) for row in rows if len(row.find_all('td')) >= 2]
            all_proxies.extend([proxy for proxy in proxies if proxy['ip'] and proxy['port']])
            time.sleep(1)
    except Exception as e:
        print(f"{site} 爬取失败: {e}")
    return all_proxies


# 保存代理
def save_proxies(proxies, format_type, filename, only_ip=False):
    if format_type == 'json':
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(proxies, f, ensure_ascii=False, indent=4)
    elif format_type == 'txt':
        with open(filename, 'w', encoding='utf-8') as f:
            if only_ip:
                for proxy in proxies:
                    f.write(f"{proxy['ip']}:{proxy['port']}\n")
            else:
                f.write("地区 | 类型 | HTTPS | 代理地址\n")
                f.write("-" * 50 + "\n")
                for p in proxies:
                    p['addr'] = f"{p['ip']}:{p['port']}"
                    f.write(f"{p.get('region', '未知')} | {p['type']} | {p['https']} | {p['addr']}\n")


# 验证代理可用性
def validate_proxy(proxy):
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            test_url = 'http://httpbin.org/ip'
            proxy['addr'] = f"{proxy['ip']}:{proxy['port']}"
            proxies = {proxy['type'].lower(): f"{proxy['type'].lower()}://{proxy['addr']}"}
            timeout = 5 if proxy['type'] in ['HTTP', 'HTTPS'] else 10
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                print(f"代理 {proxy['addr']} 验证通过，类型: {proxy['type']}，是否支持 HTTPS: {proxy['https']}")
                return proxy
            print(f"代理 {proxy['addr']} 验证失败，尝试第 {retries + 1} 次重试")
        except requests.RequestException as e:
            print(f"代理 {proxy['addr']} 验证失败，错误信息: {e}，尝试第 {retries + 1} 次重试")
        except Exception as e:
            print(f"代理 {proxy['addr']} 验证失败，未知错误: {e}，尝试第 {retries + 1} 次重试")
        retries += 1
    print(f"代理 {proxy['addr']} 验证失败，达到最大重试次数")
    return None


# 补充代理信息
def analyze_proxy(proxy, check_region, check_type, check_https):
    proxy['addr'] = f"{proxy['ip']}:{proxy['port']}"
    if check_region and proxy.get('region') is None:
        proxy['region'] = detect_region(proxy['ip'])
        print(f"代理 {proxy['addr']} 地区检测结果: {proxy['region']}")
    if check_type and proxy['type'] in ['待检测', '未知']:
        proxy['type'] = detect_proxy_type(proxy['addr'])
        print(f"代理 {proxy['addr']} 类型检测结果: {proxy['type']}")
    if check_https and proxy['https'] == '待检测':
        proxy['https'] = '支持' if proxy['type'] == 'HTTPS' else '不支持'
        print(f"代理 {proxy['addr']} 是否支持 HTTPS 检测结果: {proxy['https']}")
    return proxy


# 主程序
def main():
    print("=" * 50)
    print("🌟 多源代理 IP 爬虫 v3.0")
    print("=" * 50)

    # 爬取所有代理
    all_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(get_proxies_from_site, site): site for site in SITE_CONFIGS}
        for future in concurrent.futures.as_completed(futures):
            site = futures[future]
            try:
                proxies = future.result()
                print(f"从 {site} 获取到 {len(proxies)} 个代理")
                all_proxies.extend(proxies)
            except Exception as e:
                print(f"{site} 爬取异常: {e}")

    # 去重
    unique_proxies = []
    seen = set()
    for p in all_proxies:
        key = f"{p['ip']}:{p['port']}"
        if key not in seen:
            seen.add(key)
            unique_proxies.append(p)
    print(f"\n📦 共获取到 {len(unique_proxies)} 个唯一代理")

    # 询问用户需要多少代理
    while True:
        input_num = input("请输入你需要的代理数量（直接回车代表全部）：")
        if input_num == '':
            selected_proxies = unique_proxies
            break
        try:
            num = int(input_num)
            if num > len(unique_proxies):
                print(f"输入的数量超过了可用代理数量，可用代理数量为 {len(unique_proxies)}，请重新输入。")
            else:
                selected_proxies = unique_proxies[:num]
                break
        except ValueError:
            print("输入无效，请输入一个有效的整数或直接回车。")

    # 获取当前时间
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")

    # 保存未过滤的代理 IP
    while True:
        format_choice = input("请选择未过滤代理 IP 的输出格式 (json/txt): ").strip().lower()
        if format_choice in ['json', 'txt']:
            unfiltered_filename = f'unfiltered_proxies_{current_time}.{format_choice}'
            save_proxies(selected_proxies, format_choice, unfiltered_filename, False)
            print(f"未过滤的代理 IP 已保存为 {unfiltered_filename}")
            break
        else:
            print("输入无效，请输入 'json' 或 'txt'。")

    # 询问检测选项
    check_region = input("是否需要检测代理 IP 的地区信息？(y/n): ").strip().lower() == 'y'
    check_type = input("是否需要检测代理类型？(y/n): ").strip().lower() == 'y'
    check_https = input("是否需要检测是否支持 HTTPS？(y/n): ").strip().lower() == 'y'
    only_check_availability = not (check_region or check_type or check_https)

    # 补充检测信息
    print("\n🔍 正在分析代理信息...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        analyzed_proxies = list(
            executor.map(lambda p: analyze_proxy(p, check_region, check_type, check_https), selected_proxies))

    # 验证可用性
    print("\n⚡ 正在验证代理可用性...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        valid_proxies = list(filter(None, executor.map(validate_proxy, analyzed_proxies)))

    # 保存有效代理 IP
    while True:
        format_choice = input("请选择有效代理 IP 的输出格式 (json/txt): ").strip().lower()
        if format_choice in ['json', 'txt']:
            output_filename = f'valid_proxies_{current_time}.{format_choice}'
            if format_choice == 'txt':
                only_ip = input("是否仅输出代理 IP，每行一个代理？(y/n): ").strip().lower() == 'y'
            else:
                only_ip = False
            save_proxies(valid_proxies, format_choice, output_filename, only_ip)
            print(f"\n🎉 找到 {len(valid_proxies)} 个有效代理，已保存到 {output_filename}")
            break
        else:
            print("输入无效，请输入 'json' 或 'txt'。")


if __name__ == "__main__":
    main()
