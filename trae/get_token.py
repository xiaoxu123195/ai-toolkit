import json
import os
import sys
import subprocess
import base64
import pyperclip
from datetime import datetime


def decode_jwt(token):
    """解码 JWT token 并提取过期时间"""
    try:
        # 分割 token
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # 解码 payload 部分（第二部分）
        # 添加补位以确保base64解码正确
        padding = '=' * (4 - len(parts[1]) % 4)
        payload = base64.b64decode(parts[1] + padding)
        payload_data = json.loads(payload)

        # 获取过期时间
        exp_timestamp = payload_data.get('exp')
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            return exp_date.strftime('%Y-%m-%d %H:%M:%S')
        return None
    except Exception as e:
        print(f"Token 解析错误: {e}")
        return None


def ensure_dependencies():
    """确保依赖库 pyperclip 已安装（如未安装则自动安装）"""
    try:
        import pyperclip
    except ImportError:
        print("检测到未安装依赖库 pyperclip，正在自动安装...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pyperclip"],
                stdout=subprocess.DEVNULL
            )
            print("✅ pyperclip 安装成功！")
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败！错误代码：{e.returncode}")
            print("请尝试以下方法手动安装：")
            print("  1. 在终端执行: pip install pyperclip")
            print("  2. 如果权限不足，尝试: pip install --user pyperclip")
            sys.exit(1)
        import pyperclip


def main():
    ensure_dependencies()

    app_data = os.environ['APPDATA']
    json_path = os.path.join(app_data, r'Trae\User\globalStorage\storage.json')

    if not os.path.exists(json_path):
        print(f"错误：文件未找到！请检查路径:\n{json_path}")
        sys.exit(1)

    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            outer_json = json.load(file)

        inner_json_str = outer_json.get('iCubeAuthInfo://icube.cloudide', '')
        if not inner_json_str:
            print("错误：未能找到 'iCubeAuthInfo://icube.cloudide' 字段！")
            sys.exit(2)

        inner_json = json.loads(inner_json_str)
        token = inner_json.get('token', '')

        if token:
            import pyperclip
            pyperclip.copy(token)
            print("\n✅ Token 已复制到剪贴板:", end='\n\n')
            print(f"\033[96m{token}\033[0m\n")

            # 解析并显示token过期时间
            exp_time = decode_jwt(token)
            if exp_time:
                print(f"Token 过期时间: \033[93m{exp_time}\033[0m\n")
            else:
                print("无法解析 Token 过期时间\n")
        else:
            print("错误：未找到 'token' 字段！完整内层JSON内容：")
            print(json.dumps(inner_json, indent=2))

    except json.JSONDecodeError as e:
        print(f"JSON解析失败：{e}\n请检查文件格式是否正确！")
        sys.exit(3)
    except Exception as e:
        print(f"未知错误：{e}")
        sys.exit(4)


if __name__ == "__main__":
    main()