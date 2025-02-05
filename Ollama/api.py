import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

# 条件变量定义
MIN_SIZE_GB = 10  # 模型大小必须大于 10GB 才符合条件
MIN_VERSION_NUM = 32  # 如果版本以 "b" 结尾，则数值部分必须大于等于 32
LATEST_STR = "latest"  # 版本为 latest 时符合条件


def normalize_url(url):
    """
    标准化 URL：
    - 如果没有 http:// 或 https:// 则自动添加 http://
    - 强制使用路径 /api/tags
    """
    # 自动补全 http:// 协议
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    parsed = urlparse(url)
    # 使用解析后的 netloc (包括端口) 拼接成新的 URL
    normalized = f"{parsed.scheme}://{parsed.netloc}/api/tags"
    return normalized


def check_ollama(url):
    """检测单个 OLLAMA 实例"""
    try:
        normalized_url = normalize_url(url)
        parsed = urlparse(normalized_url)
        # 显示 host:port
        display_host = parsed.netloc

        session = requests.Session()
        session.trust_env = False  # 禁用环境代理
        session.proxies = {"http": None, "https": None}

        resp = session.get(normalized_url, timeout=5)

        if resp.status_code == 200:
            models = resp.json().get("models", [])
            status = f"✅ {display_host} 可用"
            details = []
            for m in models:
                # m['name'] 格式通常为 "模型名:版本"，例如 "llama3:70b" 或 "killphish_test:latest"
                parts = m.get("name", "").rsplit(":", maxsplit=1)
                if len(parts) == 2:
                    _, ver = parts
                else:
                    ver = ""
                size_gb = m.get("size", 0) >> 30  # 以 GB 为单位显示
                # 只显示符合条件的模型：
                # 1. 模型大小必须大于 MIN_SIZE_GB
                # 2. 且版本为 latest 或者版本以 "b" 结尾且数值大于等于 MIN_VERSION_NUM
                try:
                    if size_gb > MIN_SIZE_GB and (
                            ver == LATEST_STR or (ver.endswith("b") and float(ver[:-1]) >= MIN_VERSION_NUM)):
                        details.append(f"   - {m['name']} ({size_gb}GB)")
                except ValueError:
                    # 版本信息无法转换为数字则跳过该模型
                    continue

            if not details:
                details = ["   (无符合条件模型)"]
            return "\n".join([status] + details)
        else:
            return f"⚠️ {display_host} 异常 HTTP {resp.status_code}"

    except requests.exceptions.RequestException as e:
        return f"❌ {display_host} 连接失败: {type(e).__name__}"
    except Exception as e:
        return f"⚠️ {display_host} 错误: {str(e)}"


if __name__ == "__main__":
    # 从环境变量读取实例列表，使用分号分隔
    urls = os.getenv("OLLAMA_URLS", "").split(";")
    if not urls or urls == [""]:
        print("请在 .env 中设置 OLLAMA_URLS (分号分隔)")
        exit(1)

    print(f"🔍 开始检测 {len(urls)} 个实例:")
    for url in urls:
        url = url.strip()
        if url:
            result = check_ollama(url)
            print("\n" + result)
