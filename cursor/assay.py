import requests
import json
import time
import sys
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


def extract_referral_code(text):
    """从文本中提取推荐码
    支持两种格式：
    1. 完整URL: https://cursor.com/referral?code=NQKAMRHQNZG2
    2. 直接推荐码: NQKAMRHQNZG2
    """
    text = text.strip()

    # 尝试从URL中提取
    url_pattern = r'https?://.*cursor\.com/.*[?&]code=([A-Z0-9]{8,12})(?:&|$)'
    url_match = re.search(url_pattern, text, re.IGNORECASE)
    if url_match:
        return url_match.group(1).upper()

    # 检查是否是直接的推荐码格式（8-12位字母数字）
    code_pattern = r'^[A-Z0-9]{8,12}$'
    if re.match(code_pattern, text, re.IGNORECASE):
        return text.upper()

    # 尝试在文本中查找可能的推荐码
    inline_pattern = r'\b([A-Z0-9]{8,12})\b'
    inline_match = re.search(inline_pattern, text, re.IGNORECASE)
    if inline_match:
        return inline_match.group(1).upper()

    return None


def check_referral_code(code):
    """验证单个推荐码是否有效"""
    url = "https://www.cursor.com/api/dashboard/check-referral-code"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "Referer": f"https://www.cursor.com/cn/referral?code={code}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {"referralCode": code}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            try:
                result = response.json()
                is_valid = result.get("isValid", False)
                return code, is_valid, result
            except json.JSONDecodeError as e:
                return code, False, {"error": "Invalid JSON response"}
        else:
            return code, False, {"error": f"HTTP {response.status_code}"}

    except requests.exceptions.RequestException as e:
        return code, False, {"error": str(e)}
    except Exception as e:
        return code, False, {"error": str(e)}


def batch_check_codes(codes, max_workers=100):
    """批量验证推荐码，支持并发请求"""
    results = []
    total = len(codes)

    print(f"\n开始验证 {total} 个推荐码...")
    print(f"使用 {max_workers} 个并发线程")
    print("提示：线程数越多验证越快，但请注意不要设置过高以免被限流")
    print("-" * 60)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_code = {executor.submit(check_referral_code, code): code for code in codes}

        # 处理完成的任务
        completed = 0
        for future in as_completed(future_to_code):
            completed += 1
            code, is_valid, result = future.result()
            results.append((code, is_valid, result))

            # 显示进度
            status = "✅ 有效" if is_valid else "❌ 无效"
            print(f"[{completed}/{total}] {code}: {status}")

            # 根据线程数调整延迟，线程越多延迟越短
            if completed < total and max_workers < 20:
                time.sleep(0.1)

    return results


def read_codes_from_file(filename):
    """从文件读取推荐码列表，支持多种格式"""
    codes = []
    invalid_lines = []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"\n从文件 {filename} 读取到 {len(lines)} 行")

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过空行和注释
                continue

            code = extract_referral_code(line)
            if code:
                codes.append(code)
            else:
                invalid_lines.append((i, line))

        # 去重
        unique_codes = list(set(codes))

        print(f"成功提取 {len(unique_codes)} 个唯一推荐码")
        if len(codes) > len(unique_codes):
            print(f"（去除了 {len(codes) - len(unique_codes)} 个重复项）")

        if invalid_lines:
            print(f"\n⚠️  无法识别的行（{len(invalid_lines)} 行）：")
            for line_num, content in invalid_lines[:5]:  # 只显示前5个
                print(f"  第{line_num}行: {content[:50]}{'...' if len(content) > 50 else ''}")
            if len(invalid_lines) > 5:
                print(f"  ... 还有 {len(invalid_lines) - 5} 行")

        return unique_codes

    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}")
        return []
    except Exception as e:
        print(f"读取文件错误：{e}")
        return []


def save_results(results, filename=None):
    """保存验证结果到文件"""
    if filename is None:
        filename = f"cursor_codes_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== Cursor推荐码验证结果 ===\n")
            f.write(f"验证时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计验证：{len(results)} 个推荐码\n")
            f.write("-" * 60 + "\n\n")

            valid_codes = []
            invalid_codes = []

            for code, is_valid, result in results:
                if is_valid:
                    valid_codes.append(code)
                else:
                    invalid_codes.append((code, result.get("error", "Unknown error")))

            f.write(f"有效推荐码 ({len(valid_codes)} 个):\n")
            for code in valid_codes:
                f.write(f"✅ {code}\n")

            f.write(f"\n无效推荐码 ({len(invalid_codes)} 个):\n")
            for code, error in invalid_codes:
                f.write(f"❌ {code} - {error}\n")

        print(f"\n结果已保存到：{filename}")
        return filename
    except Exception as e:
        print(f"保存结果失败：{e}")
        return None


def main():
    print("=== Cursor推荐码批量验证工具 ===")
    print("支持自动识别以下格式：")
    print("• 完整URL: https://cursor.com/referral?code=NQKAMRHQNZG2")
    print("• 纯推荐码: NQKAMRHQNZG2 (8-12位字母数字)")
    print("• 支持混合格式，自动提取和去重")
    print("• 默认100线程并发验证，可自定义1-200线程")
    print("\n命令行用法:")
    print("  python script.py codes.txt [--threads 150]")
    print("  python script.py CODE1 CODE2 [--threads 50]")
    print("-" * 60)

    # 默认线程数
    max_workers = 100

    # 如果有命令行参数，直接使用
    if len(sys.argv) > 1:
        # 检查是否有 --threads 参数
        threads_idx = None
        for i, arg in enumerate(sys.argv):
            if arg == '--threads' and i + 1 < len(sys.argv):
                threads_idx = i
                try:
                    max_workers = int(sys.argv[i + 1])
                    if max_workers < 1:
                        max_workers = 1
                    elif max_workers > 200:
                        max_workers = 200
                    print(f"使用命令行指定的线程数: {max_workers}")
                except ValueError:
                    print("线程数参数无效，使用默认值 100")
                    max_workers = 100
                break

        # 移除 --threads 参数
        if threads_idx is not None:
            del sys.argv[threads_idx:threads_idx + 2]

        if len(sys.argv) > 1:
            if sys.argv[1].endswith('.txt'):
                # 从文件读取
                codes = read_codes_from_file(sys.argv[1])
            else:
                # 直接使用命令行参数作为推荐码
                codes = []
                for arg in sys.argv[1:]:
                    # 尝试提取每个参数中的推荐码
                    extracted_codes = []
                    for item in arg.replace(',', ' ').split():
                        code = extract_referral_code(item)
                        if code:
                            extracted_codes.append(code)
                    codes.extend(extracted_codes)
                codes = list(set(codes))  # 去重

            # 如果通过命令行参数提供了推荐码，直接开始验证
            if codes:
                print(f"\n准备验证 {len(codes)} 个推荐码")
                print(f"将使用 {max_workers} 个线程进行验证")

                # 开始验证
                start_time = time.time()
                results = batch_check_codes(codes, max_workers=max_workers)
                end_time = time.time()

                # 显示统计
                print("\n" + "=" * 60)
                print("=== 验证完成 ===")
                valid_count = sum(1 for _, is_valid, _ in results if is_valid)
                print(f"总计验证：{len(results)} 个推荐码")
                print(f"有效推荐码：{valid_count} 个")
                print(f"无效推荐码：{len(results) - valid_count} 个")
                print(f"耗时：{end_time - start_time:.2f} 秒")

                # 显示有效的推荐码
                if valid_count > 0:
                    print("\n有效的推荐码：")
                    for code, is_valid, _ in results:
                        if is_valid:
                            print(f"✅ {code}")

                # 自动保存结果
                save_results(results)
                print("\n验证完成！")
                return
    else:
        # 交互式输入
        print("\n请选择输入方式：")
        print("1. 直接输入推荐码或URL")
        print("2. 从文件读取")
        print("3. 逐个输入（输入空行结束）")
        print("\n💡 提示：可以直接拖拽文件到终端窗口")

        choice = input("\n请选择 (1/2/3) 或直接拖拽文件到此处: ").strip()

        # 处理可能的引号和转义字符（macOS拖拽文件时会添加）
        if choice.startswith('"') and choice.endswith('"'):
            choice = choice[1:-1]
        elif choice.startswith("'") and choice.endswith("'"):
            choice = choice[1:-1]
        # 处理转义的空格
        choice = choice.replace('\\ ', ' ')

        # 智能识别：如果输入看起来像文件路径，直接当作文件处理
        if (choice.endswith('.txt') or '/' in choice or '\\' in choice or
                ':' in choice or os.path.exists(choice)):
            print("\n检测到文件路径，自动使用文件读取模式")
            codes = read_codes_from_file(choice)
        elif choice == '1':
            user_input = input("\n请输入推荐码或URL（多个用空格、逗号或换行分隔）: ")
            # 检查是否输入了文件路径
            if (user_input.endswith('.txt') or '/' in user_input or '\\' in user_input or
                    ':' in user_input or os.path.exists(user_input.strip())):
                print("\n检测到文件路径，自动使用文件读取模式")
                codes = read_codes_from_file(user_input.strip())
            else:
                codes = []
                for item in user_input.replace(',', ' ').split():
                    code = extract_referral_code(item)
                    if code:
                        codes.append(code)
                    else:
                        print(f"⚠️  无法识别: {item}")
                codes = list(set(codes))  # 去重

        elif choice == '2':
            filename = input("\n请输入文件名或拖拽文件到此处: ").strip()
            # 处理可能的引号和转义字符
            if filename.startswith('"') and filename.endswith('"'):
                filename = filename[1:-1]
            elif filename.startswith("'") and filename.endswith("'"):
                filename = filename[1:-1]
            filename = filename.replace('\\ ', ' ')
            codes = read_codes_from_file(filename)

        elif choice == '3':
            print("\n请逐个输入推荐码或URL（输入空行结束）:")
            codes = []
            while True:
                user_input = input(f"输入 {len(codes) + 1}: ").strip()
                if not user_input:
                    break
                code = extract_referral_code(user_input)
                if code:
                    if code not in codes:  # 实时去重
                        codes.append(code)
                        print(f"  ✓ 已添加: {code}")
                    else:
                        print(f"  ⚠️  重复的推荐码: {code}")
                else:
                    print(f"  ✗ 无法识别的格式: {user_input}")
        else:
            print("无效选择")
            return

    if not codes:
        print("\n没有找到任何有效的推荐码")
        return

    print(f"\n准备验证 {len(codes)} 个推荐码")
    print("推荐码列表:")
    for i, code in enumerate(codes[:10], 1):  # 只显示前10个
        print(f"  {i}. {code}")
    if len(codes) > 10:
        print(f"  ... 还有 {len(codes) - 10} 个")

    # 询问线程数
    thread_input = input(f"\n请输入并发线程数 (1-200, 默认100, 直接回车使用默认值): ").strip()
    if thread_input:
        try:
            max_workers = int(thread_input)
            if max_workers < 1:
                max_workers = 1
            elif max_workers > 200:
                max_workers = 200
                print("线程数已限制为最大值 200")
        except ValueError:
            max_workers = 100
            print("输入无效，使用默认值 100")
    else:
        max_workers = 100

    print(f"\n将使用 {max_workers} 个线程进行验证")

    # 询问是否保存结果
    save_option = input("\n是否保存结果到文件？(y/n): ").strip().lower()

    # 开始验证
    start_time = time.time()
    results = batch_check_codes(codes, max_workers=max_workers)
    end_time = time.time()

    # 显示统计
    print("\n" + "=" * 60)
    print("=== 验证完成 ===")
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    print(f"总计验证：{len(results)} 个推荐码")
    print(f"有效推荐码：{valid_count} 个")
    print(f"无效推荐码：{len(results) - valid_count} 个")
    print(f"耗时：{end_time - start_time:.2f} 秒")

    # 显示有效的推荐码
    if valid_count > 0:
        print("\n有效的推荐码：")
        for code, is_valid, _ in results:
            if is_valid:
                print(f"✅ {code}")

    # 保存结果
    if save_option == 'y':
        save_results(results)

    print("\n验证完成！")


if __name__ == "__main__":
    main()