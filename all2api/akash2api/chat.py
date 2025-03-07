import requests
import json
import time

def call_akash_proxy(messages, model="DeepSeek-R1"):
    """
    调用 Akash 代理服务，发送消息并接收流式响应。

    Args:
        messages (list): OpenAI 格式的消息列表。
        model (str): 模型名称 (默认: "DeepSeek-R1")。
        temperature (float): 温度参数 (默认: 0.7)。
        top_p (float): Top P 参数 (默认: 0.9)。

    Returns:
        str: 完整的响应内容（从所有 chunks 中提取）。
    """

    url = "http://127.0.0.1:5002/v1/chat/completions"  # 确保URL正确
    data = {
        "model": model,
        "messages": messages,
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()  # 检查HTTP错误
        return response.content

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
        return None


if __name__ == "__main__":
    # 示例消息
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What are the first 5 prime numbers?"}
    ]

    # 调用 Akash 代理
    response_content = call_akash_proxy(messages)

    if response_content:
        print("\n--- Full Response: ---")
        print(response_content)
    else:
        print("请求失败，请检查错误信息。")
