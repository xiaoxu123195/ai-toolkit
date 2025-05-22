// 生成随机的5位小写字母和数字组合
function generateRandomCode(length = 5) {
    const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
}

// 从响应文本中提取referral链接
function extractReferralLink(text) {
    // 匹配形如https://cursor.com/referral?code=VWF8EBCTHVDT的链接
    // code是大写字母和数字的组合
    const regex = /https:\/\/cursor\.com\/referral\?code=[A-Z0-9]+/g;
    const matches = text.match(regex);
    return matches ? matches[0] : null;
}

// 创建一个全局变量来存储interval ID，便于停止
let intervalId = null;

// 停止函数
function stopFetching() {
    if (intervalId !== null) {
        clearInterval(intervalId);
        console.log("已停止自动获取链接");
        intervalId = null;
    } else {
        console.log("没有正在运行的获取任务");
    }
}

// 主函数，每0.5秒执行一次
function startFetching() {
    // 如果已经在运行，先停止
    if (intervalId !== null) {
        stopFetching();
    }

    // 使用当前页面的cookie
    const cookies = document.cookie;

    // 使用当前页面URL作为referer
    const referer = window.location.href;

    console.log("开始执行，每0.5秒尝试一次...");
    console.log("输入 stopFetching() 可以停止执行");

    // 使用setInterval定期执行
    intervalId = setInterval(async () => {
        // 生成随机五位码
        const randomCode = generateRandomCode();

        try {
            // 构建URL，将rsc参数替换为随机生成的代码
            const url = `https://www.perplexity.ai/account/pro-perks?_rsc=${randomCode}`;

            // 发送请求
            const response = await fetch(url, {
                "headers": {
                },
                "method": "GET",
                "credentials": "include" // 确保包含凭证
            });

            // 获取响应文本
            const responseText = await response.text();

            // 提取referral链接
            const referralLink = extractReferralLink(responseText);

            // 如果找到链接，则输出并停止
            if (referralLink) {
                console.log(`${referralLink}`);
                // 找到链接后不停止，继续尝试获取更多链接
            }
        } catch (error) {
            // 失败时不输出任何内容
        }
    }, 500); // 每0.5秒执行一次
}

// 将函数暴露到全局作用域，以便用户可以手动调用
window.startFetching = startFetching;
window.stopFetching = stopFetching;

// 自动开始执行
startFetching();
