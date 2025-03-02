addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  if (request.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  // 只允许 POST 请求
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  // 编码的 token 和 access_tokens
  const TOKEN = "sk-123";
  // 支持单个 token 或 token 数组
  const ACCESS_TOKENS = [
    "token1",
    "token2",
    "token3",
    // 可添加更多 token
  ];

  const authHeader = request.headers.get("Authorization");
  if (TOKEN) {
    if (!authHeader || authHeader !== `Bearer ${TOKEN}`) {
      return new Response("Unauthorized", {
        status: 401,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }
  }

  try {
    // 解析用户请求的JSON
    const requestBody = await request.json();

    const userMessages = requestBody.messages;
    const stream = requestBody.stream === "true";
    const model = requestBody.model;

    const newMessages = [
      { role: "system", content: "keep your reasoning short" },
      ...userMessages
    ];

    const fingerprint = "anon_" + Array.from(crypto.getRandomValues(new Uint8Array(16)))
      .map(b => b.toString(16).padStart(2, "0"))
      .join("");

    const newRequestBody = {
      body: {
        messages: newMessages,
        max_tokens: 3200,
        stop: ["<|eot_id|>"],
        stream: stream,
        stream_options: { include_usage: true },
        model: model
      },
      env_type: "text",
      fingerprint: fingerprint
    };

    // 从 ACCESS_TOKENS 数组中随机选择一个 token
    const randomToken = Array.isArray(ACCESS_TOKENS)
      ? ACCESS_TOKENS[Math.floor(Math.random() * ACCESS_TOKENS.length)]
      : ACCESS_TOKENS;

    const headers = new Headers({
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
      "Accept": "text/event-stream",
      "Content-Type": "application/json",
      "Cookie": "access_token=" + randomToken,
      "Origin": "https://cloud.sambanova.ai",
      "Referer": "https://cloud.sambanova.ai/"
    });

    const response = await fetch("https://cloud.sambanova.ai/api/completion", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(newRequestBody),
    });

    console.log(newRequestBody);

    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": response.headers.get("Content-Type") || "application/json",
      },
    });

    return newResponse;
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  }
}