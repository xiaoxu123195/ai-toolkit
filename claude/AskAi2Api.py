import asyncio
import json
import time
import uuid

from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import websockets

CONFIG = {
    "WS_URI": "wss://api.inkeep.com/graphql",
    "AUTH_TOKEN": "Bearer xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "SUBSCRIBE_ID": str(uuid.uuid4()),
    "ORG_ID": "org_xxxxxxxxxxxxxxx",
    "INTEGRATION_ID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "DEFAULT_MESSAGE": "Hello.",
    "MODEL": "claude-3-5-sonnet-20241022",
}

# 是否启用上下文
ENABLE_CONTEXT = False

app = Flask(__name__)
CORS(app)


def process_messages(messages):
    # 处理上下文，将传入的 JSON 消息组转换为字符串。
    # 请自行尝试实现。
    return CONFIG["DEFAULT_MESSAGE"]


async def perform_handshake(websocket, message_input):
    init_msg = {
        "type": "connection_init",
        "payload": {"headers": {"Authorization": CONFIG["AUTH_TOKEN"]}},
    }
    await websocket.send(json.dumps(init_msg))
    while True:
        resp = json.loads(await websocket.recv())
        if resp.get("type") == "connection_ack":
            break
    subscribe_msg = {
        "id": CONFIG["SUBSCRIBE_ID"],
        "type": "subscribe",
        "payload": {
            "variables": {
                "messageInput": message_input,
                "messageContext": None,
                "organizationId": CONFIG["ORG_ID"],
                "integrationId": CONFIG["INTEGRATION_ID"],
                "chatMode": "AUTO",
                "messageAttributes": {},
                "includeAIAnnotations": False,
                "environment": "production",
            },
            "extensions": {},
            "operationName": "OnNewSessionChatResult",
            "query": (
                "subscription OnNewSessionChatResult($messageInput: String!, $messageContext: String, $organizationId: ID!, "
                "$integrationId: ID, $chatMode: ChatMode, $filters: ChatFiltersInput, $messageAttributes: JSON, $tags: [String!], "
                "$workflowId: String, $context: String, $guidance: String, $includeAIAnnotations: Boolean!, $environment: String) {"
                "  newSessionChatResult(input: {messageInput: $messageInput, messageContext: $messageContext, organizationId: $organizationId, "
                "integrationId: $integrationId, chatMode: $chatMode, messageAttributes: $messageAttributes, environment: $environment}) {"
                "    isEnd sessionId message { id content __typename }"
                "  }"
                "}"
            ),
        },
    }
    await websocket.send(json.dumps(subscribe_msg))


async def openai_compatible_stream(message_input):
    async with websockets.connect(
            CONFIG["WS_URI"], subprotocols=["graphql-transport-ws"]
    ) as websocket:
        await perform_handshake(websocket, message_input)
        created = int(time.time())
        unique_id = f"chatcmpl-{uuid.uuid4()}"
        last_content = ""
        while True:
            raw = await websocket.recv()
            message = json.loads(raw)
            if message.get("type") == "next":
                content = message["payload"]["data"]["newSessionChatResult"]["message"][
                    "content"
                ]
                delta = content[len(last_content):]
                if delta:
                    chunk = {
                        "id": unique_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": CONFIG["MODEL"],
                        "choices": [
                            {
                                "delta": {"content": delta},
                                "index": 0,
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    last_content = content
                if message["payload"]["data"]["newSessionChatResult"].get("isEnd"):
                    final_chunk = {
                        "id": unique_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": CONFIG["MODEL"],
                        "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    break
        yield "data: [DONE]\n\n"


async def openai_compatible_complete(model_name, message_input):
    async with websockets.connect(
            CONFIG["WS_URI"], subprotocols=["graphql-transport-ws"]
    ) as websocket:
        await perform_handshake(websocket, message_input)
        created = int(time.time())
        unique_id = f"chatcmpl-{uuid.uuid4()}"
        last_content = ""
        while True:
            raw = await websocket.recv()
            message = json.loads(raw)
            if message.get("type") == "next":
                content = message["payload"]["data"]["newSessionChatResult"]["message"][
                    "content"
                ]
                last_content = content
                if message["payload"]["data"]["newSessionChatResult"].get("isEnd"):
                    break
        return {
            "id": unique_id,
            "object": "chat.completion",
            "created": created,
            "model": model_name,
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "logprobs": None,
                    "message": {
                        "role": "assistant",
                        "content": last_content,
                        "refusal": None,
                    },
                }
            ],
            "system_fingerprint": None,
        }


def sync_openai_stream(message_input):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    gen = openai_compatible_stream(message_input)
    try:
        while True:
            try:
                yield loop.run_until_complete(gen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


def sync_openai_complete(model_name, message_input):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            openai_compatible_complete(model_name, message_input)
        )
    finally:
        loop.close()


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    req = request.get_json(silent=True) or {}

    if req.get("model") != CONFIG["MODEL"]:
        return jsonify({"error": "Unsupported model."}), 400

    messages = req.get("messages", [])
    if ENABLE_CONTEXT:
        processed = process_messages(messages)
        message_input = processed[-1] if processed else CONFIG["DEFAULT_MESSAGE"]
    else:
        message_input = (
            messages[-1]["content"] if messages else CONFIG["DEFAULT_MESSAGE"]
        )
    if req.get("stream"):
        return Response(sync_openai_stream(message_input), mimetype="text/event-stream")
    result = sync_openai_complete(CONFIG["MODEL"], message_input)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
