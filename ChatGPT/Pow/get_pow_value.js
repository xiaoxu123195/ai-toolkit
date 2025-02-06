// ==UserScript==
// @name         ChatGPT降智风险检测✅（优化版）（添加教程版）
// @namespace    https://github.com/KoriIku/chatgpt-degrade-checker
// @homepage     https://github.com/KoriIku/chatgpt-degrade-checker
// @author       修改自KoriIku，然后又由 monkeyji 修改
// @icon         data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHBhdGggZmlsbD0iIzJjM2U1MCIgZD0iTTMyIDJDMTUuNDMyIDIgMiAxNS40MzIgMiAzMnMxMy40MzIgMzAgMzAgMzAgMzAtMTMuNDMyIDMwLTMwUzQ4LjU2OCAyIDMyIDJ6bTAgNTRjLTEzLjIzMyAwLTI0LTEwLjc2Ny0yNC0yNFMxOC43NjcgOCAzMiA4czI0IDEwLjc2NyAyNCAyNFM0NS4yMzMgNTYgMzIgNTZ6Ii8+PHBhdGggZmlsbD0iIzNkYzJmZiIgZD0iTTMyIDEyYy0xMS4wNDYgMC0yMCA4Ljk1NC0yMCAyMHM4Ljk1NCAyMCAyMCAyMCAyMC04Ljk1NCAyMC0yMFM0My4wNDYgMTIgMzIgMTJ6bTAgMzZjLTguODM3IDAtMTYtNy4xNjMtMTYtMTZzNy4xNjMtMTYgMTYtMTYgMTYgNy4xNjMgMTYgMTZTNDAuODM3IDQ4IDMyIDQ4eiIvPjxwYXRoIGZpbGw9IiMwMGZmN2YiIGQ9Ik0zMiAyMGMtNi42MjcgMC0xMiA1LjM3My0xMiAxMnM1LjM3MyAxMiAxMiAxMiAxMi01LjM3MyAxMi0xMlMzOC42MjcgMjAgMzIgMjB6bTAgMjBjLTQuNDE4IDAtOC0zLjU4Mi04LThzMy41ODItOCA4LTggOCAzLjU4MiA4IDgtMy41ODIgOC04IDh6Ii8+PGNpcmNsZSBmaWxsPSIjZmZmIiBjeD0iMzIiIGN5PSIzMiIgcj0iNCIvPjwvc3ZnPg==
// @version      1.3
// @description  ChatGPT会对某些IP进行无提示的服务降级，Plus用户模型会降至4-Mini，此脚本检测账号IP情况用于让你判断是否降智✅。
// @match        *://chatgpt.com/*
// @match        https://go.gptdsb.com/**
// @match        https://gpt.github.cn.com/**
// @match        https://go.gptdie.com/**
// @match        https://chat.openai.com/**
// @match        https://chatgpt.com/**
// @match        https://*.oaifree.com/**
// @match        https://share.github.cn.com/**
// @match        https://cc.plusai.me/**
// @match        https://chat.chatgptplus.cn/**
// @match        https://chat.rawchat.cc/**
// @match        https://chat.sharedchat.cn/**
// @match        https://chat.gptdsb.com/**
// @match        https://chat.freegpts.org/**
// @match        https://gpt.github.cn.com/**
// @match        https://chat.aicnn.xyz/**
// @match        https://*.xyhelper.com.cn/**
// @match        https://oai.aitopk.com/**
// @match        https://www.opkfc.com/**
// @match        https://bus.hematown.com/**
// @match        https://chatgpt.dairoot.cn/**
// @match        https://plus.aivvm.com/**
// @match        https://sharechat.aischat.xyz/**
// @match        https://web.tu-zi.com/**
// @match        https://chat1.2233.ai/**
// @match        https://2233.ai/**
// @match        https://yesiamai.com/**
// @match        https://www.azs.ai/**
// @match        https://gpt.universalbus.cn/**
// @match        https://aichatru.ru/**
// @match        https://chatgptchatapp.com/**
// @grant        none
// @license AGPLv3
// @downloadURL https://update.greasyfork.org/scripts/523077/ChatGPT%E9%99%8D%E6%99%BA%E9%A3%8E%E9%99%A9%E6%A3%80%E6%B5%8B%E2%9C%85%EF%BC%88%E4%BC%98%E5%8C%96%E7%89%88%EF%BC%89%EF%BC%88%E6%B7%BB%E5%8A%A0%E6%95%99%E7%A8%8B%E7%89%88%EF%BC%89.user.js
// @updateURL https://update.greasyfork.org/scripts/523077/ChatGPT%E9%99%8D%E6%99%BA%E9%A3%8E%E9%99%A9%E6%A3%80%E6%B5%8B%E2%9C%85%EF%BC%88%E4%BC%98%E5%8C%96%E7%89%88%EF%BC%89%EF%BC%88%E6%B7%BB%E5%8A%A0%E6%95%99%E7%A8%8B%E7%89%88%EF%BC%89.meta.js
// ==/UserScript==

(function() {
    'use strict';

    // 创建显示框
    const displayBox = document.createElement('div');
    displayBox.style.position = 'fixed';
    displayBox.style.top = '50%';
    displayBox.style.right = '20px';
    displayBox.style.transform = 'translateY(-50%)';
    displayBox.style.width = '350px';
    displayBox.style.padding = '10px';
    displayBox.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    displayBox.style.color = '#fff';
    displayBox.style.fontSize = '14px';
    displayBox.style.borderRadius = '8px';
    displayBox.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.3)';
    displayBox.style.zIndex = '10000';
    displayBox.style.transition = 'all 0.3s ease';
    displayBox.style.display = 'none';

    displayBox.innerHTML = `
        <div style="margin-bottom: 10px;">
            <strong>PoW 信息</strong>
        </div>
        <div id="content">
            PoW难度: <span id="difficulty">N/A</span><span id="difficulty-level" style="margin-left: 3px"></span>
            <span id="difficulty-tooltip" style="
                cursor: pointer;
                color: #fff;
                font-size: 12px;
                display: inline-block;
                width: 14px;
                height: 14px;
                line-height: 14px;
                text-align: center;
                border-radius: 50%;
                border: 1px solid #fff;
                margin-left: 3px;
            ">?</span><br>
            PoW数值: <span id="pow-value">N/A</span><br>
            IP质量: <span id="ip-quality">N/A</span><br>
            <span id="persona-container" style="display: none">
            用户类型: <span id="persona">N/A</span></span>
            “PoW难度” 默认是十六进制<br>
            “PoW数值” 是 Pow难度 转换后的具体数值<br>
            Pow 可以简单等价为信任度，越高越好。<br>
            过低的信任值可能导致模型被降级，例如 o1 模型不思考，4o 模型不识图<br>
            <span style="color: #EB4E4A" >建议切换不同的节点并刷新验证，令信任度保持在五位数以上才能降低模型被降智的可能性，最好保持在 20000 以上</span>
        </div>
        <div style="
            margin-top: 12px;
            padding-top: 8px;
            border-top: 0.5px solid rgba(255, 255, 255, 0.15);
            font-size: 10px;
            color: rgba(255, 255, 255, 0.5);
            text-align: center;
            letter-spacing: 0.3px;
        ">
            ChatGPT Degrade Checker
    </div>`;
    document.body.appendChild(displayBox);

    // 创建收缩状态的指示器
    const collapsedIndicator = document.createElement('div');
    collapsedIndicator.style.position = 'fixed';
    collapsedIndicator.style.top = '50%';
    collapsedIndicator.style.right = '20px';
    collapsedIndicator.style.transform = 'translateY(-50%)';
    collapsedIndicator.style.width = '32px';
    collapsedIndicator.style.height = '32px';
    collapsedIndicator.style.backgroundColor = 'transparent';
    collapsedIndicator.style.borderRadius = '50%';
    collapsedIndicator.style.cursor = 'pointer';
    collapsedIndicator.style.zIndex = '10000';
    collapsedIndicator.style.padding = '4px';
    collapsedIndicator.style.display = 'flex';
    collapsedIndicator.style.alignItems = 'center';
    collapsedIndicator.style.justifyContent = 'center';
    collapsedIndicator.style.transition = 'all 0.3s ease';

    // 使用SVG作为指示器
    collapsedIndicator.innerHTML = `
    <svg id="status-icon" width="32" height="32" viewBox="0 0 64 64" style="transition: all 0.3s ease;">
        <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#3498db;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#2ecc71;stop-opacity:1" />
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        <g id="icon-group" filter="url(#glow)">
            <circle cx="32" cy="32" r="28" fill="url(#gradient)" stroke="#fff" stroke-width="2"/>
            <circle cx="32" cy="32" r="20" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="100">
                <animateTransform
                    attributeName="transform"
                    attributeType="XML"
                    type="rotate"
                    from="0 32 32"
                    to="360 32 32"
                    dur="8s"
                    repeatCount="indefinite"/>
            </circle>
            <circle cx="32" cy="32" r="12" fill="none" stroke="#fff" stroke-width="2">
                <animate
                    attributeName="r"
                    values="12;14;12"
                    dur="2s"
                    repeatCount="indefinite"/>
            </circle>
            <circle id="center-dot" cx="32" cy="32" r="4" fill="#fff">
                <animate
                    attributeName="r"
                    values="4;6;4"
                    dur="2s"
                    repeatCount="indefinite"/>
            </circle>
        </g>
    </svg>`;
    document.body.appendChild(collapsedIndicator);

    // 鼠标悬停事件
    collapsedIndicator.addEventListener('mouseenter', function() {
        displayBox.style.display = 'block';
        collapsedIndicator.style.opacity = '0';
    });

    displayBox.addEventListener('mouseleave', function() {
        displayBox.style.display = 'none';
        collapsedIndicator.style.opacity = '1';
    });

    // 创建提示框
    const tooltip = document.createElement('div');
    tooltip.id = 'tooltip';
    tooltip.innerText = '这个值越小，代表PoW难度越高，ChatGPT认为你的IP风险越高。';
    tooltip.style.position = 'fixed';
    tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
    tooltip.style.color = '#fff';
    tooltip.style.padding = '8px 12px';
    tooltip.style.borderRadius = '5px';
    tooltip.style.fontSize = '12px';
    tooltip.style.visibility = 'hidden';
    tooltip.style.zIndex = '10001';
    tooltip.style.width = '240px';
    tooltip.style.lineHeight = '1.4';
    tooltip.style.pointerEvents = 'none';
    document.body.appendChild(tooltip);

    // 显示提示
    document.getElementById('difficulty-tooltip').addEventListener('mouseenter', function(event) {
        tooltip.style.visibility = 'visible';

        const tooltipWidth = 240;
        const windowWidth = window.innerWidth;
        const mouseX = event.clientX;
        const mouseY = event.clientY;

        let leftPosition = mouseX - tooltipWidth - 10;
        if (leftPosition < 10) {
            leftPosition = mouseX + 20;
        }

        let topPosition = mouseY - 40;

        tooltip.style.left = `${leftPosition}px`;
        tooltip.style.top = `${topPosition}px`;
    });

    // 隐藏提示
    document.getElementById('difficulty-tooltip').addEventListener('mouseleave', function() {
        tooltip.style.visibility = 'hidden';
    });

    // 更新difficulty指示器
    function updateDifficultyIndicator(difficulty) {
        const difficultyLevel = document.getElementById('difficulty-level');
        const ipQuality = document.getElementById('ip-quality');

        if (difficulty === 'N/A') {
            setIconColors('#888', '#666');
            difficultyLevel.innerText = '';
            ipQuality.innerHTML = 'N/A';
            return;
        }

        const cleanDifficulty = difficulty.replace('0x', '').replace(/^0+/, '');
        const hexLength = cleanDifficulty.length;
        const hex2num = parseInt(cleanDifficulty, 16); // 将十六进制字符串转换为数字
        let color, secondaryColor, textColor, level, qualityText;

        if (hexLength <= 2) {
            color = '#F44336';
            secondaryColor = '#d32f2f';
            textColor = '#ff6b6b';
            level = '(困难)';
            qualityText = '高风险';
        } else if (hexLength === 3) {
            color = '#FFC107';
            secondaryColor = '#ffa000';
            textColor = '#ffd700';
            level = '(中等)';
            qualityText = '中等';
        } else if (hexLength === 4) {
            color = '#8BC34A';
            secondaryColor = '#689f38';
            textColor = '#9acd32';
            level = '(简单)';
            qualityText = '良好';
        } else {
            color = '#4CAF50';
            secondaryColor = '#388e3c';
            textColor = '#98fb98';
            level = '(极易)';
            qualityText = '优秀';
        }
        setIconColors(color, secondaryColor);
        difficultyLevel.innerHTML = `<span style="color: ${textColor}">${level}</span>`;
        ipQuality.innerHTML = `<span style="color: ${textColor}">${qualityText}</span>`;
        document.getElementById('pow-value').innerText = hex2num;
    }

    function setIconColors(primaryColor, secondaryColor) {
        const gradient = document.querySelector('#gradient');
        gradient.innerHTML = `
            <stop offset="0%" style="stop-color:${primaryColor};stop-opacity:1" />
            <stop offset="100%" style="stop-color:${secondaryColor};stop-opacity:1" />
        `;
    }

    // 拦截 fetch 请求
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options) {
        const response = await originalFetch(resource, options);

        if ((resource.includes('/backend-api/sentinel/chat-requirements')||resource.includes('backend-anon/sentinel/chat-requirements')) && options.method === 'POST') {
            const clonedResponse = response.clone();
            clonedResponse.json().then(data => {
                const difficulty = data.proofofwork ? data.proofofwork.difficulty : 'N/A';
                const persona = data.persona || 'N/A';
                document.getElementById('difficulty').innerText = difficulty;

                const personaContainer = document.getElementById('persona-container');
                if (persona && !persona.toLowerCase().includes('free')) {
                    personaContainer.style.display = 'block';
                    document.getElementById('persona').innerText = persona;
                } else {
                    personaContainer.style.display = 'none';
                }

                updateDifficultyIndicator(difficulty);
            }).catch(e => console.error('解析响应时出错:', e));
        }
        return response;
    };
})();
