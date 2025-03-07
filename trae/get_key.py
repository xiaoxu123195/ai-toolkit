import os
import re
import glob

# 检查操作系统是否为 Windows
if os.name != 'nt':
    print("Error: This script only supports Windows")
    exit(1)

# 检查 Trae 安装目录是否存在
trae_dir = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Trae')
if not os.path.exists(trae_dir):
    print("Error: Trae installation not found")
    exit(1)

# 找到最旧的日志目录 (2025 开头的)
log_dirs = sorted(glob.glob(os.path.join(trae_dir, 'logs', '2025*')))
if not log_dirs:
    print("Error: No log directories found matching the pattern")
    exit(1)
old_log_dir = log_dirs[0]  # 最旧的目录

old_main_log = os.path.join(old_log_dir, 'main.log')
if not os.path.exists(old_main_log):
    print("Error: main.log not found in the oldest log directory")
    exit(1)

# 提取 ClientID
try:
    with open(old_main_log, 'r', encoding='utf-8') as f:
        content = f.read()
        # client_id_match = re.search(r'"ClientID":"([^"]*)"', content)
        client_id_match = re.search(r'ClientID\\\":\\\"([\w]+)', content)
        if not client_id_match:
            print("Error: Could not find ClientID in main.log")
            exit(1)
        client_id = client_id_match.group(1)
except Exception as e:
    print(f"Error reading or processing main.log: {e}")
    exit(1)
# 找到最新的日志目录 (2025 开头的)
new_log_dir = sorted(glob.glob(os.path.join(trae_dir, 'logs', '2025*')))[-1]  # 最新的目录
new_app_log = os.path.join(new_log_dir, 'Modular', 'ai_1_stdout.log')
if not os.path.exists(new_app_log):
    print("Error: ai_1_stdout.log not found in the latest log directory")
    exit(1)

# 提取 AppID
try:
    with open(new_app_log, 'r', encoding='utf-8') as f:
        app_content = f.read()
        app_id_match = re.search(r'"x-app-id": "([^"]*)"', app_content)
        if not app_id_match:
            print("Error: Could not find APP_ID in ai_1_stdout.log")
            exit(1)
        app_id = app_id_match.group(1)
except Exception as e:
    print(f"Error reading or processing ai_1_stdout.log: {e}")
    exit(1)

# 提取认证信息
storage_file = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Trae', 'User', 'globalStorage',
                            'storage.json')
try:
    with open(storage_file, 'r', encoding='utf-8') as f:
        storage_content = f.read()
        auth_match = re.search(r'"iCubeAuthInfo://icube\.cloudide": "({.*?})"', storage_content)
        if auth_match:
            json_str = auth_match.group(1).replace('\\"', '"')
            refresh_token_match = re.search(r'refreshToken":"(.*?)"(?:,|})', json_str)
            user_id_match = re.search(r'userId":"(\d+)"', json_str)

            if refresh_token_match and user_id_match:
                user_id = user_id_match.group(1)
                refresh_token = refresh_token_match.group(1)

                print(f"USER_ID={user_id}")
                print(f"REFRESH_TOKEN={refresh_token}")
                print(f"CLIENT_ID={client_id}")
                print(f"APP_ID={app_id}")
except Exception as e:
    print(f"Error reading or processing storage.json: {e}")
    exit(1)