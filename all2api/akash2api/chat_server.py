from flask import Flask, request, jsonify, Response
import requests
import uuid
import json
import time

app = Flask(__name__)


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
        # 获取OpenAI格式的请求数据
        data = request.json

        # 生成唯一ID
        chat_id = str(uuid.uuid4()).replace('-', '')[:16]

        # 构建Akash格式的请求数据
        akash_data = {
            "id": chat_id,
            "messages": data.get('messages', []),
            "model": data.get('model', "DeepSeek-R1"),
            "system": data.get('system_message', "You are a helpful assistant."),
            "temperature": data.get('temperature', 0.6),
            "topP": data.get('top_p', 0.95)
        }
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Cookie": "cf_clearance=vKJGV.qRcO9vXfCRQJ4EbQCz2GCAVpSA7NZl0WPkeQg-1740899894-1.2.1.1-ThHBbss1ABiccRAopEeCoQr7zI7x75ciZv0jnYt5ablSOVtel.qOVWW2QBK6qHEK6Mz3E2lgEqXMDE8sLZXZ.cTNMqlp7QB64DMbusxp12A_uAvd2aKBKYitEVoiqZK9uU24YunEQ7qDdp1QQiVkTG.TcK1B47PLqTvQ9U78kS7LlsjkfpKHZZP.KD1suh_cU5DFXclrhpgOvhudsEsRo5Lkd8ostLPb5ci_IC86Gk4SFUp49eTzMbUlNfiIXsibVPdXSBTWD4iJ66SRDqbyFMFKrxV7OXkwRS4zIoScUuGjTimuNEgFPDiUwG.bLm6zgx7r1yoQu1dM7_cca6mNg9POi.Kb6ms629nraczneJE4.nAIMgggT8DGaHpgL6Sbl3whmJEn4qn82_UYlsrhL3At4vd4iFNP2gz5rsX72cg; session_token=9f5718a6aba2390cb5f81c378421a054c6e4e145e78dbf88782d351629747161"
        }

        print(akash_data)
        # 发送请求到Akash API
        response = requests.post(
            'https://chat.akash.network/api/chat',
            json=akash_data,
            headers=headers,
            stream=True
        )

        def generate():
            content_buffer = ""
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    # 解析行数据，格式为 "type:json_data"
                    line_str = line.decode('utf-8')
                    msg_type, msg_data = line_str.split(':', 1)

                    # 处理内容类型的消息
                    if msg_type == '0':
                        # 只去掉两边的双引号
                        if msg_data.startswith('"') and msg_data.endswith('"'):
                            msg_data = msg_data.replace('\\"', '"')
                            msg_data = msg_data[1:-1]
                        msg_data = msg_data.replace("\\n", "\n")
                        content_buffer += msg_data

                        # 构建 OpenAI 格式的响应块
                        chunk = {
                            "id": f"chatcmpl-{chat_id}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": data.get('model', "DeepSeek-R1"),
                            "choices": [{
                                "delta": {"content": msg_data},
                                "index": 0,
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                    # 处理结束消息
                    elif msg_type in ['e', 'd']:
                        chunk = {
                            "id": f"chatcmpl-{chat_id}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": data.get('model', "DeepSeek-R1"),
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

                except Exception as e:
                    print(f"Error processing line: {e}")
                    continue

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'text/event-stream'
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
