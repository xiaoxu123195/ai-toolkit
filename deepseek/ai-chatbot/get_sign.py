import time
import hashlib

def generate_sign(conversation_id: str):
    """
    根据传入的 input_str 生成 sign 和 currentTime
      - currentTime 为当前的毫秒时间戳
      - sign 为 MD5(input_str + currentTime + "@!~chatbot.0868") 的16进制字符串表示
    """
    current_time = int(time.time() * 1000)
    message = conversation_id + str(current_time) + "@!~chatbot.0868"
    sign = hashlib.md5(message.encode('utf-8')).hexdigest()
    return current_time, sign

if __name__ == '__main__':
# 调用示例（本示例仅作原理展示）  conversation_id 的生成逻辑就是 uuidv4
    conversation_id = "2b38300f-e9e6-437a-9562-aa62cc5cf3b4"
    current_time, sign = generate_sign(conversation_id)
    print("currentTime:", current_time)
    print("sign:", sign)
