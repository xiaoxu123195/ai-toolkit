import json
import re
import os


def process_api_keys(input_file):
    """
    处理包含API密钥的文本文件，提取并去重API密钥，同时尽可能准确地关联邮箱信息。
    采用全文搜索、多模式匹配和动态窗口策略。

    Args:
        input_file: 包含API密钥的文本文件路径。

    Returns:
        一个元组，包含两个元素：
        - result_data: 包含API密钥列表和邮箱映射的字典。
        - duplicate_count: 重复API密钥的数量。
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'gemini_merge')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    result_data = {
        "api_keys": [],
        "email_mapping": {}
    }
    duplicate_keys = set()
    unique_keys = set()

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"读取到的内容长度：{len(content)} 字符")

        # 全局搜索所有可能的API Key
        api_key_pattern = r"AIzaSy[a-zA-Z0-9_-]{15,}"
        api_key_matches = re.finditer(api_key_pattern, content)

        # 预先提取所有可能的邮箱，并构建邮箱位置字典
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        email_matches = list(re.finditer(email_pattern, content))
        email_positions = {match.group(0): match.start() for match in email_matches}

        for api_key_match in api_key_matches:
            api_key = api_key_match.group(0)
            api_key_start = api_key_match.start()

            # 寻找最近的邮箱
            closest_email = None
            min_distance = float('inf')

            for email, email_start in email_positions.items():
                distance = abs(api_key_start - email_start)
                if distance < min_distance:
                    min_distance = distance
                    closest_email = email

            # 如果找到的最近邮箱距离在合理范围内（例如，500个字符内），则进行关联
            if min_distance <= 500:
                if api_key in unique_keys:
                    duplicate_keys.add(api_key)
                    print(f"发现重复的API key: {api_key}")
                else:
                    unique_keys.add(api_key)
                    result_data['api_keys'].append(api_key)
                    result_data['email_mapping'][api_key] = closest_email
            else:
                # 如果没有找到合适的邮箱，则标记为 unknown
                if api_key in unique_keys:
                    duplicate_keys.add(api_key)
                    print(f"发现重复的API key: {api_key}")
                else:
                    unique_keys.add(api_key)
                    result_data['api_keys'].append(api_key)
                    result_data['email_mapping'][api_key] = "unknown@email.com"

        # 输出完整JSON格式
        full_json_path = os.path.join(output_dir, 'gemini_merge_data.json')
        with open(full_json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        # 输出简单JSON格式
        simple_json_path = os.path.join(output_dir, 'gemini_keys.json')
        with open(simple_json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data['api_keys'], f, indent=2, ensure_ascii=False)

        # 输出纯文本格式
        txt_path = os.path.join(output_dir, 'gemini_merge_txt.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            for key in result_data['api_keys']:
                f.write(f"{key}\n")

        # 输出重复的API keys
        if duplicate_keys:
            duplicate_path = os.path.join(output_dir, 'duplicate_keys.txt')
            with open(duplicate_path, 'w', encoding='utf-8') as f:
                f.write("发现以下重复的API keys：\n")
                for key in duplicate_keys:
                    f.write(f"{key}\n")
            print(f"发现 {len(duplicate_keys)} 个重复的API keys，已保存到 duplicate_keys.txt")

    except FileNotFoundError:
        print(f"错误：找不到输入文件 {input_file}")
        return None, 0
    except Exception as e:
        print(f"处理过程中出现错误：{e}")
        return None, 0

    return result_data, len(duplicate_keys)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, 'input.txt')

    if not os.path.exists(input_file):
        print(f"错误：找不到输入文件 {input_file}")
    else:
        result_data, duplicate_count = process_api_keys(input_file)
        if result_data:
            print(f"处理完成！共处理 {len(result_data['api_keys'])} 个唯一API keys")
            if duplicate_count > 0:
                print(f"发现并移除了 {duplicate_count} 个重复的API keys")
            print(f"输出文件保存在: {os.path.join(current_dir, 'gemini_merge')}")
