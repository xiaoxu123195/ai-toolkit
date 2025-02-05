import requests
import json
import time
import random
import concurrent.futures
import threading
import os
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 设置输入输出文件路径
INPUT_DIR = os.path.join(SCRIPT_DIR, "gemini_merge")
INPUT_FILE = os.path.join(INPUT_DIR, "gemini_merge_txt.txt")

# 输出文件路径
OUTPUT_VALID_TXT = os.path.join(INPUT_DIR, "valid_keys.txt")
OUTPUT_INVALID_TXT = os.path.join(INPUT_DIR, "invalid_keys.txt")
OUTPUT_VALID_JSON = os.path.join(INPUT_DIR, "valid_keys.json")
OUTPUT_INVALID_JSON = os.path.join(INPUT_DIR, "invalid_keys.json")

# API配置（可以多个，自行填写）
API_ENDPOINTS = [
    "https://generativelanguage.googleapis.com",
]

API_MODEL = "gemini-1.5-flash"  # 测试模型
CONCURRENCY = 2  # 并发数
RETRY_COUNT = 3  # 重试次数
MIN_DELAY = 2  # 最小延迟秒数
MAX_DELAY = 5  # 最大延迟秒数
RETRY_DELAY = 5  # 重试等待时间(秒)
BAR_LENGTH = 30  # 进度条长度
REQUESTS_PER_MINUTE = 5  # 每分钟请求阈值

# 全局变量
valid_keys = []
invalid_keys = []
lock = threading.Lock()
stats = {"valid": 0, "invalid": 0, "total": 0, "processed": 0}
print_lock = threading.Lock()
endpoint_lock = threading.Lock()
start_time = time.time()

# 接口请求计数追踪
endpoint_requests = {
    endpoint: {
        'count': 0,  # 一分钟内的请求次数
        'last_reset': time.time(),  # 上次重置计数的时间
        'last_used': 0  # 最后使用时间
    }
    for endpoint in API_ENDPOINTS
}


def print_header():
    """打印测试开始的标题栏"""
    print("\n" + "─" * 80)
    print(f"{Fore.MAGENTA}==== Testing Gemini Model: {API_MODEL} ===={Style.RESET_ALL}".center(80))
    print("─" * 80 + "\n")


def print_api_test_info(api_key, endpoint):
    """打印API测试信息"""
    print(f"{Fore.CYAN}Testing API Key: {api_key}")
    print(f"└── Endpoint: {endpoint}{Style.RESET_ALL}")


def print_test_result(is_valid, error_msg=None):
    """打印测试结果"""
    if is_valid:
        print(f"└── Result: {Fore.GREEN}✓ Valid{Style.RESET_ALL}")
    else:
        print(f"└── Result: {Fore.RED}✗ Invalid{Style.RESET_ALL}")
        if error_msg:
            print(f"    └── Error: {Fore.RED}{error_msg}{Style.RESET_ALL}")
    print()


def calculate_remaining_time(processed, total):
    """计算剩余时间"""
    if processed == 0:
        return "N/A"
    elapsed_time = time.time() - start_time
    rate = processed / elapsed_time
    remaining = total - processed
    remaining_time = remaining / rate
    return f"{remaining_time:.1f}s"


def print_progress_bar(processed, total, valid, invalid):
    """打印进度条"""
    percent = (processed / total) * 100
    filled_length = int(BAR_LENGTH * processed // total)

    bar = (
        f"{Fore.GREEN}{'█' * filled_length}"
        f"{Fore.WHITE}{'─' * (BAR_LENGTH - filled_length)}{Style.RESET_ALL}"
    )

    remaining = total - processed
    remaining_time = calculate_remaining_time(processed, total)

    progress_info = (
        f"\r{Fore.BLUE}Progress: "
        f"|{bar}| "
        f"{percent:>5.1f}% "
        f"Processed: {processed}/{total} "
        f"({Fore.GREEN}✓:{valid}{Style.RESET_ALL}, "
        f"{Fore.RED}✗:{invalid}{Style.RESET_ALL}, "
        f"Remaining: {remaining}, "
        f"Est. Time Left: {remaining_time})"
        f"{Style.RESET_ALL}"
    )

    print(progress_info, end="", flush=True)


def print_summary():
    """打印测试总结"""
    duration = time.time() - start_time
    print("\n\n" + "─" * 80)
    print(f"{Fore.CYAN}Test Summary:{Style.RESET_ALL}")
    print(f"├── Total Time: {duration:.2f}s")
    print(f"├── Total Keys: {stats['total']}")
    print(f"├── Valid Keys: {Fore.GREEN}{stats['valid']}{Style.RESET_ALL}")
    print(f"└── Invalid Keys: {Fore.RED}{stats['invalid']}{Style.RESET_ALL}")
    print("─" * 80 + "\n")


def print_save_results():
    """打印保存结果信息"""
    print(f"{Fore.CYAN}Saving results...{Style.RESET_ALL}")
    print(f"├── Valid keys   → {Fore.GREEN}{os.path.basename(OUTPUT_VALID_TXT)}{Style.RESET_ALL}")
    print(f"├── Valid JSON   → {Fore.GREEN}{os.path.basename(OUTPUT_VALID_JSON)}{Style.RESET_ALL}")
    print(f"├── Invalid keys → {Fore.RED}{os.path.basename(OUTPUT_INVALID_TXT)}{Style.RESET_ALL}")
    print(f"└── Invalid JSON → {Fore.RED}{os.path.basename(OUTPUT_INVALID_JSON)}{Style.RESET_ALL}")


def should_cooldown(endpoint):
    """检查接口是否需要冷却"""
    current_time = time.time()
    endpoint_data = endpoint_requests[endpoint]

    # 检查是否需要重置计数(每60秒重置一次)
    if current_time - endpoint_data['last_reset'] >= 60:
        endpoint_data['count'] = 0
        endpoint_data['last_reset'] = current_time
        return False

    # 检查一分钟内的请求次数是否达到阈值
    if endpoint_data['count'] >= REQUESTS_PER_MINUTE:
        return True

    return False


def get_available_endpoint():
    """智能选择可用的接口"""
    current_time = time.time()

    with endpoint_lock:
        # 按最后使用时间排序
        available_endpoints = sorted(
            endpoint_requests.items(),
            key=lambda x: x[1]['last_used']
        )

        for endpoint, data in available_endpoints:
            # 如果接口未触发冷却机制,直接使用
            if not should_cooldown(endpoint):
                # 更新接口使用信息
                endpoint_requests[endpoint]['count'] += 1
                endpoint_requests[endpoint]['last_used'] = current_time
                return endpoint

        # 如果所有接口都在冷却,等待最早使用的接口
        earliest_endpoint = available_endpoints[0][0]
        endpoint_data = endpoint_requests[earliest_endpoint]

        # 等待到下一个60秒周期
        wait_time = 60 - (current_time - endpoint_data['last_reset'])
        if wait_time > 0:
            time.sleep(wait_time)
            return get_available_endpoint()

        return earliest_endpoint


def smart_delay():
    """智能延迟函数"""
    base_delay = random.uniform(MIN_DELAY, MAX_DELAY)

    if stats["processed"] > 0:
        request_rate = stats["processed"] / (time.time() - start_time)
        if request_rate > 0.5:
            base_delay *= 1.5

    time.sleep(base_delay)


def test_api_key(api_key, endpoint, retry_count=RETRY_COUNT):
    """测试API密钥有效性"""
    url = f"{endpoint}/v1beta/models/{API_MODEL}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    data = {
        "contents": [{"parts": [{"text": "Hi"}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)

        # 429不触发冷却,只重试
        if response.status_code in [429, 403]:
            with print_lock:
                print(f"    {Fore.YELLOW}└── Warning: Rate limit detected, retrying...{Style.RESET_ALL}")
            time.sleep(RETRY_DELAY)
            if retry_count > 0:
                return test_api_key(api_key, endpoint, retry_count - 1)

        if response.status_code == 200:
            return True
        else:
            with print_lock:
                print(f"    {Fore.RED}└── Error: HTTP {response.status_code}{Style.RESET_ALL}")
            return False

    except requests.exceptions.RequestException as e:
        if retry_count > 0:
            time.sleep(RETRY_DELAY)
            return test_api_key(api_key, endpoint, retry_count - 1)
        else:
            with print_lock:
                print(f"    {Fore.RED}└── Error: {str(e)}{Style.RESET_ALL}")
            return False


def worker(api_key):
    """工作线程函数"""
    global stats
    endpoint = get_available_endpoint()

    with print_lock:
        print_api_test_info(api_key, endpoint)

    smart_delay()
    is_valid = test_api_key(api_key, endpoint)

    with lock:
        if is_valid:
            valid_keys.append({"api_key": api_key, "endpoint": endpoint})
            stats["valid"] += 1
        else:
            invalid_keys.append({"api_key": api_key, "endpoint": endpoint})
            stats["invalid"] += 1
        stats["processed"] += 1

        with print_lock:
            print_test_result(is_valid)


def save_results(valid_keys, invalid_keys):
    """保存结果到文件"""
    # 保存 TXT 文件
    with open(OUTPUT_VALID_TXT, "w") as f:
        for key in valid_keys:
            f.write(f"{key['api_key']}\n")

    with open(OUTPUT_INVALID_TXT, "w") as f:
        for key in invalid_keys:
            f.write(f"{key['api_key']}\n")

    # 保存 JSON 文件
    valid_json = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_valid": len(valid_keys),
        "keys": valid_keys
    }

    invalid_json = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_invalid": len(invalid_keys),
        "keys": invalid_keys
    }

    with open(OUTPUT_VALID_JSON, "w", encoding="utf-8") as f:
        json.dump(valid_json, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_INVALID_JSON, "w", encoding="utf-8") as f:
        json.dump(invalid_json, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    global stats, start_time

    if not os.path.exists(INPUT_DIR):
        print(f"{Fore.RED}Error: Input directory '{INPUT_DIR}' not found.{Style.RESET_ALL}")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}Error: Input file '{INPUT_FILE}' not found.{Style.RESET_ALL}")
        return

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            api_keys = [line.strip() for line in f if line.strip()]
        stats["total"] = len(api_keys)
    except Exception as e:
        print(f"{Fore.RED}Error reading input file: {str(e)}{Style.RESET_ALL}")
        return

    print_header()
    print(f"{Fore.CYAN}Input File: {os.path.basename(INPUT_FILE)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Found {stats['total']} API keys to test{Style.RESET_ALL}\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(worker, api_key): api_key for api_key in api_keys}

        processed_in_group = 0
        for future in concurrent.futures.as_completed(futures):
            processed_in_group += 1
            if processed_in_group % CONCURRENCY == 0 or processed_in_group == stats["total"]:
                with print_lock:
                    print_progress_bar(stats["processed"], stats["total"],
                                       stats["valid"], stats["invalid"])

    print_summary()
    save_results(valid_keys, invalid_keys)
    print_save_results()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}程序被用户中断{Style.RESET_ALL}")
        if stats["processed"] > 0:
            save_results(valid_keys, invalid_keys)
            print_save_results()
    except Exception as e:
        print(f"\n{Fore.RED}程序发生错误: {str(e)}{Style.RESET_ALL}")
