import requests
from openai import OpenAI

# Ollama API base URL
Ollama_API_URL = "http://64.191.166.202:80/v1"
# 设置  API 密钥
# Ollama_API_KEY = "sk-"
Ollama_API_KEY = "ollama"


# 获取模型列表
def get_model_list():
    try:
        response = requests.get(f"{Ollama_API_URL}/models")
        response.raise_for_status()  # 如果响应有错误，抛出异常
        models = response.json()  # 假设响应是 JSON 格式

        # 打印整个响应
        print("Response from server:", models)

        # 提取模型 ID
        model_list = [model['id'] for model in models.get('data', [])]
        return model_list

    except requests.exceptions.RequestException as e:
        print(f"Error fetching model list: {e}")
        return []


# 主函数，获取模型列表并向选定模型进行对话
def main():
    # 获取模型列表
    models = get_model_list()

    if not models:
        print("No models available.")
        return

    # 显示可用的模型
    print("Available models:")
    for idx, model in enumerate(models):
        print(f"{idx + 1}. {model}")

    # 选择模型
    model_idx = int(input("Select a model by number: ")) - 1
    if model_idx < 0 or model_idx >= len(models):
        print("Invalid selection.")
        return

    model_name = models[model_idx]

    # 设置 OpenAI 的 base_url 为 Ollama 的服务器 URL
    openai_client = OpenAI(base_url=Ollama_API_URL, api_key=Ollama_API_KEY)

    print(f"Selected model: {model_name}")

    # 开始交互对话
    print("Start chatting (type 'exit' to stop):")
    conversation_history = []

    while True:
        question = input("You: ")

        if question.lower() == 'exit':
            print("Ending conversation.")
            break

        # Add user message to conversation history
        conversation_history.append({"role": "user", "content": question})

        # 获取模型的回答
        try:
            stream = openai_client.chat.completions.create(
                model=model_name,
                messages=conversation_history,
                stream=True,
                max_tokens=2048,
                top_p=0.85,
                temperature=0.58,
            )
            answer = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="")
                    answer += chunk.choices[0].delta.content
            # Add the assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": answer})

        except Exception as e:
            print(f"Error during conversation: {e}")
            break


if __name__ == "__main__":
    main()
