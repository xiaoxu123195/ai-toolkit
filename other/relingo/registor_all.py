import concurrent.futures
import random
import re
import threading
import time

import requests
from fake_useragent import UserAgent
from loguru import logger

referrer = "您的code"


class WordGenerator:
    def __init__(self):
        # 常用辅音字母
        self.consonants = "bcdfghjklmnpqrstvwxyz"
        # 元音字母
        self.vowels = "aeiou"
        # 常用的字母组合
        self.common_pairs = [
            "th",
            "ch",
            "sh",
            "ph",
            "wh",
            "br",
            "cr",
            "dr",
            "fr",
            "gr",
            "pr",
            "tr",
        ]
        # 常用的词尾
        self.common_endings = ["ing", "ed", "er", "est", "ly", "tion", "ment"]
        # 常用的用户名后缀
        self.username_suffixes = [
            "123",
            "888",
            "666",
            "777",
            "999",
            "pro",
            "cool",
            "good",
            "best",
        ]

    def generate_syllable(self):
        """生成一个音节"""
        if random.random() < 0.3 and self.common_pairs:  # 30% 概率使用常用字母组合
            return random.choice(self.common_pairs) + random.choice(self.vowels)
        else:
            return random.choice(self.consonants) + random.choice(self.vowels)

    def generate_word(self, min_length=4, max_length=8):
        """生成一个随机单词"""
        word = ""
        target_length = random.randint(min_length, max_length)

        # 添加音节直到达到目标长度附近
        while len(word) < target_length - 2:
            word += self.generate_syllable()

        # 可能添加常用词尾
        if random.random() < 0.3 and len(word) < max_length - 2:
            word += random.choice(self.common_endings)
        elif len(word) < target_length:
            word += random.choice(self.consonants)

        return word.lower()

    def generate_random_username(self, min_length=3, max_length=8):
        """生成随机用户名"""
        username = self.generate_word(min_length, max_length)

        # 50% 的概率添加数字或特殊后缀
        if random.random() < 0.5:
            if random.random() < 0.7:  # 70% 概率添加数字
                username += str(random.randint(0, 999)).zfill(random.randint(2, 3))
            else:  # 30% 概率添加特殊后缀
                username += random.choice(self.username_suffixes)

        return username

    def generate_combined_username(self, num_words=1, separator="_"):
        """生成完整的组合用户名"""
        # 首先生成基础用户名
        base_username = self.generate_random_username()

        # 生成额外的随机单词
        words = [self.generate_word() for _ in range(num_words)]

        # 随机决定用户名放在前面还是后面
        if random.random() < 0.5:
            words.append(base_username)
        else:
            words.insert(0, base_username)

        return separator.join(words)


class MailTmClient:
    baseurl = "https://api.mail.tm"

    def __init__(self, user=None):
        if user is None:
            generator = WordGenerator()
            user = generator.generate_combined_username(1)

        # 重试机制
        for attempt in range(3):
            try:
                domain = self.get_domains()
                if not domain:
                    logger.warning(f"尝试 {attempt + 1}/3: 获取域名失败，重试中...")
                    time.sleep(2)
                    continue

                logger.info("Get domain:" + domain)
                self.acount = user + "@" + domain
                logger.info("Get acount:" + self.acount)

                account_result = self.acounts(self.acount)
                if not account_result:
                    logger.warning(f"尝试 {attempt + 1}/3: 创建账户失败，重试中...")
                    time.sleep(2)
                    continue

                token_result = self.get_token(self.acount)
                if not token_result:
                    logger.warning(f"尝试 {attempt + 1}/3: 获取令牌失败，重试中...")
                    time.sleep(2)
                    continue

                # 成功初始化
                break
            except Exception as e:
                logger.error(f"初始化邮箱客户端出错 (尝试 {attempt + 1}/3): {str(e)}")
                if attempt < 2:  # 如果不是最后一次尝试，则等待后重试
                    time.sleep(3)
                else:
                    raise Exception(f"初始化邮箱客户端失败，已重试3次: {str(e)}")

    def get_email(self):
        return self.acount

    def get_domains(self):
        try:
            response = requests.get(f"{self.baseurl}/domains", timeout=10)
            if response.status_code != 200:
                logger.error(f"获取域名失败: 状态码 {response.status_code}")
                return None

            response_data = response.json()
            if (
                "hydra:member" not in response_data
                or len(response_data["hydra:member"]) == 0
            ):
                logger.error("获取域名失败: 返回数据结构异常")
                return None

            return response_data["hydra:member"][0]["domain"]
        except Exception as e:
            logger.error(f"获取域名时出错: {str(e)}")
            return None

    def acounts(self, acount):
        try:
            json_data = {
                "address": acount,
                "password": "thisispassword",
            }
            response = requests.post(
                "https://api.mail.tm/accounts", json=json_data, timeout=10
            )

            if response.status_code != 201 and response.status_code != 200:
                logger.error(f"创建账户失败: 状态码 {response.status_code}")
                if response.text:
                    logger.info("acounts:" + response.text)
                return None

            if not response.text:
                logger.error("创建账户失败: 空响应")
                return None

            logger.info("acounts:" + response.text)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"创建账户请求出错: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"解析账户响应出错: {str(e)}")
            return None

    def get_token(self, acount):
        try:
            json_data = {
                "address": acount,
                "password": "thisispassword",
            }

            response = requests.post(
                "https://api.mail.tm/token", json=json_data, timeout=10
            )

            if response.status_code != 200:
                logger.error(f"获取令牌失败: 状态码 {response.status_code}")
                if response.text:
                    logger.info("get_token:" + response.text)
                return None

            if not response.text:
                logger.error("获取令牌失败: 空响应")
                return None

            logger.info("get_token:" + response.text)
            response_data = response.json()

            if "token" not in response_data:
                logger.error("获取令牌失败: 返回数据中无token字段")
                return None

            self.token = response_data["token"]
            return self.token
        except requests.exceptions.RequestException as e:
            logger.error(f"获取令牌请求出错: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"解析令牌响应出错: {str(e)}")
            return None

    def getmessage(self):
        try:
            headers = {
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "authorization": "Bearer " + self.token,
                "cache-control": "no-cache",
                "origin": "https://mail.tm",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://mail.tm/",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            }
            response = requests.get(
                "https://api.mail.tm/messages", headers=headers, timeout=10
            )

            if response.status_code != 200:
                logger.error(f"获取消息失败: 状态码 {response.status_code}")
                return None

            response_data = response.json()

            if (
                "hydra:totalItems" in response_data
                and response_data["hydra:totalItems"] > 0
            ):
                return response_data["hydra:member"][0]["intro"]
            else:
                return None
        except Exception as e:
            logger.error(f"获取消息时出错: {str(e)}")
            return None

    def wait_getmessage(self, max_wait_time=60):  # 缩短默认等待时间为60秒
        start_time = time.time()
        check_count = 0

        while True:
            try:
                message = self.getmessage()
                if message is not None:
                    return message

                # 检查是否超时
                if time.time() - start_time > max_wait_time:
                    logger.error(f"等待消息超时，已等待{max_wait_time}秒")
                    return None

                check_count += 1
                if check_count > 15:  # 如果检查超过15次仍未收到邮件，认为邮箱有问题
                    logger.warning(f"多次检查未收到邮件，邮箱可能有问题: {self.acount}")
                    return None

                logger.info(f"等待邮件中... ({check_count}/15)")
                time.sleep(2)  # 增加等待时间，减轻请求频率
            except Exception as e:
                logger.error(f"等待消息时出错: {str(e)}")
                time.sleep(2)


class RelingoReg:
    def __init__(self):
        self.mm = MailTmClient()
        self.email = self.mm.get_email()

        ua = UserAgent(platforms="desktop")

        self.headers = {
            "authority": "api.relingo.net",
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "chrome-extension://dpphkcfmnbkdpmgneljgdhfnccnhmfig",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "none",
            "user-agent": ua.random,
            "x-relingo-dest-lang": "en",
            "x-relingo-lang": "zh",
            "x-relingo-platform": "extension",
            "x-relingo-referrer": "https://relingo.net/en/try?relingo-drawer=account",
            "x-relingo-version": "3.16.6",
        }
        self.cookies = {"referrer": referrer}

    def sendcode(self):
        try:
            json_data = {
                "email": self.email,
                "type": "LOGIN",
            }

            response = requests.post(
                "https://api.relingo.net/api/sendPasscode",
                cookies=self.cookies,
                headers=self.headers,
                json=json_data,
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(f"发送验证码失败: 状态码 {response.status_code}")
                return False

            logger.info("Relingo_SendCode:" + response.text)
            return True
        except Exception as e:
            logger.error(f"发送验证码时出错: {str(e)}")
            return False

    def reg(self, code):
        try:
            json_data = {
                "type": "PASSCODE",
                "email": self.email,
                "code": code,
                "referrer": referrer,
            }

            response = requests.post(
                "https://api.relingo.net/api/login",
                cookies=self.cookies,
                headers=self.headers,
                json=json_data,
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(f"注册失败: 状态码 {response.status_code}")
                return False

            logger.info("Relingo_Reg:" + response.text)
            return True
        except Exception as e:
            logger.error(f"注册时出错: {str(e)}")
            return False

    def start(self):
        try:
            if not self.sendcode():
                logger.error("发送验证码失败")
                return False

            # 等待并获取验证码
            message = self.mm.wait_getmessage(180)  # 最多等待3分钟

            if not message:
                logger.error("未收到验证码邮件")
                return False

            logger.info("Get message:" + message)
            result = re.search(r"\d+", message)

            if result:
                code = result.group(0)
                return self.reg(code)
            else:
                logger.error("无法从邮件中提取验证码")
                return False
        except Exception as e:
            logger.error(f"注册出错: {str(e)}")
            return False


def register_task(task_id, success_counter):
    try:
        logger.info(f"任务 {task_id} 开始注册")

        # 添加重试机制
        for attempt in range(5):  # 增加到5次尝试
            try:
                relingoreg = RelingoReg()
                result = relingoreg.start()

                if result:
                    with success_counter_lock:
                        success_counter[0] += 1
                    logger.success(
                        f"任务 {task_id} 注册成功! 总成功次数: {success_counter[0]}"
                    )
                    return True
                else:
                    logger.warning(f"任务 {task_id} 注册失败 (尝试 {attempt + 1}/5)")
                    # 不等待，直接尝试新邮箱
                    logger.info(f"任务 {task_id} 跳过当前邮箱，尝试新邮箱")
            except Exception as e:
                logger.error(
                    f"任务 {task_id} 发生错误 (尝试 {attempt + 1}/5): {str(e)}"
                )
                if attempt < 4:  # 如果不是最后一次尝试，则继续
                    time.sleep(1)

        logger.error(f"任务 {task_id} 失败，已重试5次")
        return False
    except Exception as e:
        logger.error(f"任务 {task_id} 发生严重错误: {str(e)}")
        return False


if __name__ == "__main__":
    success_counter = [0]  # 使用列表存储计数器，方便在线程间共享
    success_counter_lock = threading.Lock()  # 线程锁，防止计数冲突

    fail_counter = [0]  # 失败计数器
    fail_counter_lock = threading.Lock()  # 线程锁

    # 配置日志
    logger.remove()
    logger.add(
        "relingo_reg_{time}.log",
        rotation="100 MB",
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>",
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>",
    )

    logger.info("Relingo自动注册程序开始运行...")
    logger.info("按 Ctrl+C 停止程序")

    task_id = 0
    max_workers = 3  # 减少并发数，避免API限制

    # 添加任务间延迟，避免同时发起大量请求
    task_delay = 1  # 减少任务延迟到1秒

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                # 提交任务到线程池
                futures = []
                for i in range(max_workers):
                    task_id += 1
                    # 添加任务间延迟
                    time.sleep(task_delay)
                    futures.append(
                        executor.submit(register_task, task_id, success_counter)
                    )

                # 等待所有任务完成
                complete_count = 0
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if not result:
                        with fail_counter_lock:
                            fail_counter[0] += 1
                    complete_count += 1
                    # 显示进度
                    logger.info(f"当前批次完成: {complete_count}/{len(futures)}")

                logger.info(
                    f"当前总成功次数: {success_counter[0]} | 失败次数: {fail_counter[0]}"
                )
                time.sleep(3)  # 批次间间隔时间缩短到3秒
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        logger.info(
            f"总共成功注册 {success_counter[0]} 个账号 | 失败 {fail_counter[0]} 次"
        )
    except Exception as e:
        logger.error(f"程序发生错误: {str(e)}")
    finally:
        logger.info(
            f"程序结束，总成功次数: {success_counter[0]} | 失败次数: {fail_counter[0]}"
        )