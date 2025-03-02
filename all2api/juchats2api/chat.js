import fetch from 'node-fetch';
import https from 'https';
import {randomUUID} from 'crypto';

const sendCaptchaEndpoint = "https://www.juchats.com/gw/chatweb/user/email/sendCaptcha"; // 发送验证码 API 端点
const regLoginEndpoint = "https://www.juchats.com/gw/chatweb/user/email/regLogin"; // 注册端点
const tempMailNewEndpoint = 'temp-mail44.p.rapidapi.com'; // 临时邮箱 API 域名
const rapidApiKey = ''; // RapidAPI 密钥, 你申请创建的

const userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
];

const getRandomUserAgent = () => userAgents[Math.floor(Math.random() * userAgents.length)];

const generateTempEmail = () => {
    const options = {
        method: 'POST',
        hostname: tempMailNewEndpoint,
        port: null,
        path: '/api/v3/email/new',
        headers: {
            'x-rapidapi-key': rapidApiKey,
            'x-rapidapi-host': tempMailNewEndpoint,
            'Content-Type': 'application/json'
        }
    };

    return new Promise((resolve, reject) => {
        const req = https.request(options, res => {
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                try {
                    const body = Buffer.concat(chunks).toString();
                    resolve(JSON.parse(body));
                } catch (error) {
                    reject(error);
                }
            });
        });

        req.on('error', reject);
        req.write(JSON.stringify({key1: 'value', key2: 'value'}));
        req.end();
    });
};

const getEmailContent = async (email) => {
    const options = {
        method: 'GET',
        hostname: tempMailNewEndpoint,
        port: null,
        path: `/api/v3/email/${email}/messages`,
        headers: {
            'x-rapidapi-key': rapidApiKey,
            'x-rapidapi-host': tempMailNewEndpoint
        }
    };

    return new Promise((resolve, reject) => {
        const req = https.request(options, res => {
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                try {
                    const body = Buffer.concat(chunks).toString();
                    resolve(JSON.parse(body));
                } catch (error) {
                    reject(error);
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
};

const extractVerificationCode = async (email) => {
    const maxAttempts = 3; // 最大尝试次数
    const retryInterval = 20000; // 重试间隔 (毫秒)
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const emailContent = await getEmailContent(email);

            if (emailContent && emailContent.length > 0) {
                const bodyText = emailContent[0].body_text;
                const codeMatch = bodyText.match(/(\d{6})/); // 匹配 6 位数字验证码
                if (codeMatch) {
                    return codeMatch[1]; // 返回验证码
                }
            }

            attempts++;
            console.log(`尝试 ${attempts}/${maxAttempts} 获取验证码，等待 ${retryInterval / 1000} 秒...`);
            await new Promise(resolve => setTimeout(resolve, retryInterval));
        } catch (error) {
            console.error("获取邮件内容失败:", error);
            attempts++;
            console.log(`尝试 ${attempts}/${maxAttempts} 获取验证码，等待 ${retryInterval / 1000} 秒...`);
            await new Promise(resolve => setTimeout(resolve, retryInterval));
        }
    }

    console.error("多次尝试获取验证码失败。");
    return null;
};

const sendEmailCaptcha = async (email) => {
    const userAgent = getRandomUserAgent(); // 获取随机 User-Agent
    const requestId = randomUUID(); // 生成唯一请求 ID
    const headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json",
        "noninductive": "true",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not A(Brand";v="99", "Chromium";v="123", "Microsoft Edge";v="123"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "_ga=GA1.1.2059922291.1740792140; _hjSessionUser_3891016=eyJpZCI6IjVlMGI1MzY0LWVmNGYtNTQ0Mi04NzZiLTM1OGYwYjYzMTQ3YSIsImNyZWF0ZWQiOjE3NDA3OTIxNDA2MjEsImV4aXN0aW5nIjp0cnVlfQ==; _hjSession_3891016=eyJpZCI6ImExOGFiNjZjLWMyOTMtNDZjNC04MGZhLTA0ZjQ2NTA2ZDI4ZCIsImMiOjE3NDA3OTIxNDA2MjIsInMiOjEsInIiOjEsInBiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MH0=; _ga_BGPCRVYLM7=GS1.1.1740792139.1.1.1740794456.0.0.0",
        "Referer": "https://www.juchats.com/login",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "User-Agent": userAgent,
        "X-Request-ID": requestId
    };

    const body = JSON.stringify({email, type: 1});

    try {
        const response = await fetch(sendCaptchaEndpoint, {
            method: 'POST',
            headers: headers,
            body: body
        });

        if (!response.ok) {
            console.error(`发送验证码请求失败，状态码：${response.status}，内容：${await response.text()}`);
            throw new Error(`HTTP 错误! 状态码: ${response.status}`);
        }

        return await response.json(); // 解析 JSON 响应
    } catch (error) {
        console.error("发送验证码出错:", error);
        throw error;
    }
};

const registerLoginWithEmail = async (email, code, inviteCode = "") => {
    const userAgent = getRandomUserAgent();
    const requestId = randomUUID();
    const headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json",
        "noninductive": "true",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not A(Brand";v="99", "Chromium";v="123", "Microsoft Edge";v="123"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "_ga=GA1.1.2059922291.1740792140; _hjSessionUser_3891016=eyJpZCI6IjVlMGI1MzY0LWVmNGYtNTQ0Mi04NzZiLTM1OGYwYjYzMTQ3YSIsImNyZWF0ZWQiOjE3NDA3OTIxNDA2MjEsImV4aXN0aW5nIjp0cnVlfQ==; _hjSession_3891016=eyJpZCI6ImExOGFiNjZjLWMyOTMtNDZjNC04MGZhLTA0ZjQ2NTA2ZDI4ZCIsImMiOjE3NDA3OTIxNDA2MjIsInMiOjEsInIiOjEsInBiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MH0=; _ga_BGPCRVYLM7=GS1.1.1740792139.1.1.1740794456.0.0.0",
        "Referer": "https://www.juchats.com/login",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "User-Agent": userAgent,
        "X-Request-ID": requestId
    };

    const body = JSON.stringify({email, code, inviteCode});

    try {
        const response = await fetch(regLoginEndpoint, {
            method: 'POST',
            headers: headers,
            body: body
        });

        if (!response.ok) {
            console.error(`注册/登录请求失败，状态码：${response.status}，内容：${await response.text()}`);
            throw new Error(`HTTP 错误! 状态码: ${response.status}`);
        }

        return await response.json(); // 解析 JSON 响应
    } catch (error) {
        console.error("注册/登录出错:", error);
        throw error; // 抛出错误
    }
};

const main = async () => {
    let tempEmail = null;
    let verificationCode = null;
    const inviteCode = ""; // 邀请码我没试过，可能多额度？

    try {
        const tempEmailResult = await generateTempEmail(); // 生成临时邮箱
        console.log("临时邮箱结果:", tempEmailResult);

        if (tempEmailResult?.email) {
            tempEmail = tempEmailResult.email; // 获取临时邮箱地址

            const captchaResult = await sendEmailCaptcha(tempEmail); // 发送验证码
            console.log("发送验证码结果:", captchaResult);

            if (captchaResult?.code === 200) {
                verificationCode = await extractVerificationCode(tempEmail);
                if (verificationCode) {
                    console.log("提取到的验证码:", verificationCode);

                    const regLoginResult = await registerLoginWithEmail(tempEmail, verificationCode, inviteCode); // 注册/登录
                    console.log("注册/登录结果:", regLoginResult);

                    if (regLoginResult?.code === 200 && regLoginResult?.data?.token) {
                        const token = regLoginResult.data.token;
                        console.log("Token:", token);
                        return token;
                    } else {
                        console.error("注册/登录失败或响应中未找到 token。");
                    }
                } else {
                    console.error("提取验证码失败。");
                }
            } else {
                console.error("发送邮件验证码失败。");
            }
        } else {
            console.error("生成临时邮箱失败。");
        }
    } catch (error) {
        console.error("发生错误:", error);
    }
    return null;
};

main(); // 运行