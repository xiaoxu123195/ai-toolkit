// ==UserScript==
// @name         auto write card info
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @author       king, nudejs, bin, 南风知我意, duck duck
// @match        *://*/c/pay/*
// @match        https://buy.stripe.com/*
// @grant        GM_addStyle
// @grant        GM_xmlhttpRequest
// @license      MIT
// @description none
// @downloadURL https://update.greasyfork.org/scripts/509394/auto%20write%20card%20info.user.js
// @updateURL https://update.greasyfork.org/scripts/509394/auto%20write%20card%20info.meta.js
// ==/UserScript==

(function () {
    'use strict';

    console.log('信用卡自动填写和生成器脚本已启动');

    // ────────── 配置常量 ──────────
    const CONFIG = {
        toggleBtnText: '信用卡工具',
        addressApiUrl: 'https://ipapi.emo.blue/?key=69ae022212045fa9518cb3447983af70',
        storageKey: 'autoWriteCardInfoTheme'
    };

    // ────────── 插入样式 ──────────
    GM_addStyle(`
    /* 全局颜色变量 - 使用CSS变量以便深色模式切换 */
    :root {
        --bg-color: rgba(255, 255, 255, 0.95);
        --panel-bg: rgba(255, 255, 255, 0.95);
        --text-color: #333333;
        --text-secondary: #666666;
        --input-bg: rgba(240, 240, 242, 0.95);
        --input-focus-bg: rgba(230, 230, 232, 0.95);
        --input-border-color: rgba(0, 0, 0, 0.1);
        --button-primary-bg: #50e3c2;
        --button-primary-text: #000000;
        --button-secondary-bg: rgba(80, 227, 194, 0.2);
        --button-secondary-text: #50e3c2;
        --button-secondary-hover: rgba(80, 227, 194, 0.3);
        --menu-item-hover: rgba(240, 240, 242, 0.95);
        --switch-bg: #cccccc;
        --version-badge-bg: rgba(240, 240, 242, 0.95);
    }

    /* 深色模式特定样式 - 当.dark-mode类被添加时生效 */
    .dark-mode {
        --bg-color: rgba(18, 18, 20, 0.95);
        --panel-bg: rgba(28, 28, 30, 0.95);
        --text-color: #ffffff;
        --text-secondary: #a0a0a0;
        --input-bg: rgba(38, 38, 40, 0.95);
        --input-focus-bg: rgba(48, 48, 50, 0.95);
        --input-border-color: rgba(255, 255, 255, 0.15);
        --button-primary-bg: #50e3c2;
        --button-primary-text: #000000;
        --button-secondary-bg: rgba(80, 227, 194, 0.2);
        --button-secondary-text: #50e3c2;
        --button-secondary-hover: rgba(80, 227, 194, 0.3);
        --menu-item-hover: rgba(48, 48, 50, 0.95);
        --switch-bg: #333333;
        --version-badge-bg: rgba(38, 38, 40, 0.95);
    }

    /* 响应式断点 */
    @media (max-width: 768px) {
        #cardTools {
            max-width: 90% !important;
            width: 90% !important;
            right: 5% !important;
            left: 5% !important;
            top: 10px !important;
            padding: 12px !important;
        }

        .card-tool-header h2 {
            font-size: 18px !important;
        }

        .primary-button, .secondary-button, .full-width-button {
            padding: 10px 16px !important;
            font-size: 13px !important;
        }

        .input-field label {
            font-size: 13px !important;
        }

        input, textarea {
            padding: 10px !important;
            font-size: 13px !important;
        }

        .menu-button {
            padding: 10px !important;
            font-size: 14px !important;
        }

        #toggleBtn {
            padding: 6px 10px !important;
            font-size: 12px !important;
        }
    }

    @media (max-width: 480px) {
        #cardTools {
            max-width: 95% !important;
            width: 95% !important;
            right: 2.5% !important;
            left: 2.5% !important;
            padding: 10px !important;
        }

        .button-row {
            flex-direction: column !important;
            gap: 8px !important;
        }

        .primary-button, .secondary-button {
            width: 100% !important;
        }

        .card-tool-header {
            margin-bottom: 12px !important;
        }

        .content-panel {
            padding: 12px !important;
            margin-bottom: 12px !important;
        }

        .panel-header {
            margin-bottom: 12px !important;
        }

        .footer {
            flex-direction: column !important;
            gap: 8px !important;
            align-items: flex-start !important;
        }

        .theme-switch {
            width: 100% !important;
            justify-content: space-between !important;
        }
    }

    /* 主容器样式 */
    #cardTools {
        max-width: 350px;
        border-radius: 16px;
        position: fixed;
        top: 60px;
        right: 20px;
        z-index: 9999;
        background-color: var(--bg-color);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
        padding: 16px;
        display: none; /* 默认收起状态 */
    }

    /* 工具标题 */
    .card-tool-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .card-tool-header h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: var(--text-color);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }

    .version-badge {
        background: linear-gradient(135deg, #ff7676, #ff4848);
        color: white;
        font-size: 12px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        box-shadow: 0 2px 4px rgba(255, 72, 72, 0.3);
    }

    /* 内容面板 */
    .content-panel {
        background-color: var(--panel-bg);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--input-border-color);
    }

    /* 菜单按钮 */
    .menu-button {
        display: flex;
        align-items: center;
        width: 100%;
        padding: 12px;
        margin-bottom: 10px;
        border: 1px solid var(--input-border-color);
        border-radius: 10px;
        background-color: var(--input-bg);
        color: var(--text-color);
        font-size: 15px;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .menu-button:hover {
        background-color: var(--menu-item-hover);
        border-color: var(--button-primary-bg);
    }

    .menu-button .icon {
        display: flex;
        margin-right: 10px;
        color: var(--button-primary-bg);
    }

    /* 面板头部 */
    .panel-header {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
    }

    .back-button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        padding: 0;
        margin-right: 10px;
        border: none;
        border-radius: 50%;
        background-color: var(--button-primary-bg);
        color: var(--button-primary-text);
        cursor: pointer;
    }

    .panel-header span {
        font-size: 16px;
        font-weight: 500;
        color: var(--text-color);
    }

    /* 表单输入 */
    .input-field {
        margin-bottom: 16px;
    }

    .input-field label {
        display: block;
        margin-bottom: 6px;
        font-size: 14px;
        color: var(--text-secondary);
    }

    input, textarea {
        width: 100%;
        padding: 12px;
        border: 1px solid var(--input-border-color);
        border-radius: 10px;
        background-color: var(--input-bg);
        color: var(--text-color);
        font-size: 14px;
        transition: all 0.2s ease;
    }

    input:focus, textarea:focus {
        outline: none;
        background-color: var(--input-focus-bg);
        border-color: var(--button-primary-bg);
    }

    /* 按钮样式 */
    .button-row {
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
    }

    .primary-button, .secondary-button, .full-width-button {
        padding: 12px 20px;
        border: none;
        border-radius: 10px;
        font-weight: 500;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .primary-button:hover, .full-width-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .secondary-button:hover {
        background-color: var(--button-secondary-hover);
        transform: translateY(-1px);
    }

    /* 输出区域 */
    .output-field {
        margin-bottom: 16px;
    }

    .output-field textarea {
        min-height: 100px;
        resize: vertical;
    }

    /* 全宽按钮 */
    .full-width-button {
        width: 100%;
        padding: 12px 0;
        border: none;
        border-radius: 10px;
        background-color: var(--button-primary-bg);
        color: var(--button-primary-text);
        font-weight: 500;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .full-width-button:hover {
        opacity: 0.9;
    }

    /* 提示文本 */
    .hint-text {
        margin-top: 0;
        margin-bottom: 10px;
        font-size: 13px;
        color: var(--text-secondary);
    }

    /* 页脚 */
    .footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .theme-switch {
        display: flex;
        align-items: center;
    }

    .switch-label {
        margin-right: 10px;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .version-text {
        font-size: 12px;
        color: var(--text-secondary);
        background-color: var(--version-badge-bg);
        padding: 3px 8px;
        border-radius: 10px;
    }

    /* 开关样式 */
    .switch {
        position: relative;
        display: inline-block;
        width: 46px;
        height: 24px;
        margin-left: 8px;
    }

    .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: var(--switch-bg);
        transition: 0.4s;
        border-radius: 24px;
        border: 1px solid var(--input-border-color);
    }

    .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 2px;
        bottom: 2px;
        background-color: white;
        transition: 0.4s;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    input:checked + .slider {
        background-color: var(--button-primary-bg);
    }

    input:checked + .slider:before {
        transform: translateX(22px);
    }

    /* 深色模式下的特殊组件样式调整 */
    .dark-mode #toggleBtn {
        background-color: rgba(80, 227, 194, 0.2);
        color: var(--button-primary-bg);
    }

    /* 切换按钮样式 */
    #toggleBtn {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 10000; /* 确保始终在最上层 */
        padding: 8px 12px;
        border: none;
        border-radius: 8px;
        background-color: var(--button-primary-bg);
        color: var(--button-primary-text);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    #toggleBtn:hover {
        opacity: 0.9;
    }

    @media (hover: none) {
        .primary-button:hover, .secondary-button:hover, .full-width-button:hover, .menu-button:hover, #toggleBtn:hover {
            transform: none;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .primary-button:active, .secondary-button:active, .full-width-button:active, .menu-button:active, #toggleBtn:active {
            transform: scale(0.98);
        }
    }

    @supports (padding-top: env(safe-area-inset-top)) {
        #cardTools {
            padding-top: calc(16px + env(safe-area-inset-top));
            padding-right: calc(16px + env(safe-area-inset-right));
            padding-bottom: calc(16px + env(safe-area-inset-bottom));
            padding-left: calc(16px + env(safe-area-inset-left));
            top: calc(60px + env(safe-area-inset-top)); /* 调整安全区域 */
        }

        #toggleBtn {
            top: calc(10px + env(safe-area-inset-top));
            right: calc(10px + env(safe-area-inset-right));
        }
    }
    `);

    // ────────── 创建 DOM 元素 ──────────
    // 创建 Toggle 按钮
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'toggleBtn';
    toggleBtn.textContent = CONFIG.toggleBtnText;
    document.body.appendChild(toggleBtn);

    // 创建主要容器，并使用新页面 HTML
    const container = document.createElement('div');
    container.id = 'cardTools';
    container.style.display = 'none'; // 默认收起状态
    container.innerHTML = `
        <div class="card-tool-header">
            <h2>信用卡工具</h2>
            <span class="version-badge">Pro</span>
        </div>

        <!-- 主菜单 -->
        <div id="mainMenu" class="content-panel">
            <button id="generatorBtn" class="menu-button">
                <span class="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M3 10H21M7 15H8M12 15H13M3 18V8C3 6.89543 3.89543 6 5 6H19C20.1046 6 21 6.89543 21 8V18C21 19.1046 20.1046 20 19 20H5C3.89543 20 3 19.1046 3 18Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </span>
                <span>卡号生成器</span>
            </button>

            <button id="autofillBtn" class="menu-button">
                <span class="icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M9 5H7C5.89543 5 5 5.89543 5 7V19C5 20.1046 5.89543 21 7 21H17C18.1046 21 19 20.1046 19 19V7C19 5.89543 18.1046 5 17 5H15M9 5C9 6.10457 9.89543 7 11 7H13C14.1046 7 15 6.10457 15 5M9 5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5M12 12H15M12 16H15M9 12H9.01M9 16H9.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </span>
                <span>自动填写信用卡</span>
            </button>
        </div>

        <!-- 卡号生成器面板 -->
        <div id="cardGenerator" class="content-panel" style="display:none;">
            <div class="panel-header">
                <button class="back-button" aria-label="返回">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M15 19L8 12L15 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <span>卡号生成器</span>
            </div>

            <div class="input-field">
                <label for="binInput">BIN码</label>
                <input type="text" id="binInput" placeholder="输入bin码 (例如: 4xxxxx)">
            </div>

            <div class="input-field">
                <label for="quantity">生成数量</label>
                <input type="number" id="quantity" value="10" min="1" max="100">
            </div>

            <div class="button-row">
                <button type="button" id="generateBtn" class="primary-button">生成卡号</button>
                <button type="button" id="clearBtn" class="secondary-button">清除</button>
            </div>

            <div class="output-field">
                <textarea id="generatedCards" rows="5" readonly placeholder="生成的卡号将显示在这里..."></textarea>
            </div>

            <button id="copyAndFillBtn" class="full-width-button">复制并跳转</button>
        </div>

        <!-- 自动填写信用卡面板 -->
        <div id="autofillPanel" class="content-panel" style="display:none;">
            <div class="panel-header">
                <button class="back-button backBtn" aria-label="返回">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M15 19L8 12L15 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <span>自动填写信用卡</span>
            </div>

            <p class="hint-text">粘贴包含卡信息的文本，系统将自动识别</p>
            <textarea id="card-input" rows="4" placeholder="例如: 4242 4242 4242 4242 | 12/24 | 123"></textarea>

            <button id="submit-button" class="full-width-button">自动填写支付</button>
        </div>

        <!-- 主题切换 -->
        <div class="footer">
            <div class="theme-switch">
                <label for="themeSwitch" class="switch-label">深色模式</label>
                <label class="switch">
                    <input type="checkbox" id="themeSwitch">
                    <span class="slider"></span>
                </label>
            </div>
            <span class="version-text">v2.0</span>
        </div>
    `;
    document.body.appendChild(container);

    // ────────── 状态变量 ──────────
    let generatedCards = [];
    let captchaDetectorInitialized = false;

    // ────────── 辅助函数 ──────────
    function $(id) {
        return document.getElementById(id);
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function setNativeValue(element, value) {
        const valueSetter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value')?.set;
        if (valueSetter) {
            valueSetter.call(element, value);
        } else {
            element.value = value;
        }
        ['input', 'change', 'blur'].forEach(eventType => {
            element.dispatchEvent(new Event(eventType, { bubbles: true }));
        });
        await delay(50);
    }

    // 根据 BIN 判断 CVV 长度
    function getCvvLength(bin) {
        return (bin.startsWith('34') || bin.startsWith('37')) ? 4 : 3;
    }

    // 解析 BIN 输入（格式：bin|MM|YY|CVV，可缺 CVV 和有效期）
    function parseBinInput(input) {
        const parts = input.split('|').map(p => p.trim());
        return {
            bin: parts[0] || '',
            expiryDate: (parts[1] && parts[2]) ? `${parts[1]}|${parts[2]}` : '',
            cvv: parts[3] || ''
        };
    }

    // 验证输入数据
    function validateInputs(bin, expiryDate, cvv) {
        if (bin.length < 6 || bin.length > 12 || !/^\d+$/.test(bin)) {
            throw new Error("BIN 必须是 6-12 位数字");
        }
        if (expiryDate && !isValidExpiryDate(expiryDate)) {
            throw new Error("时间格式无效，请使用 MM|YY 格式，月份为01-12");
        }
        const cvvLength = getCvvLength(bin);
        if (cvv && (!/^\d{3,4}$/.test(cvv) || cvv.length !== cvvLength)) {
            throw new Error(`CVV 必须是 ${cvvLength} 位数字，或为空`);
        }
    }

    function isValidExpiryDate(date) {
        if (!/^\d{2}\|\d{2}$/.test(date)) return false;
        const [month, year] = date.split('|');
        const m = parseInt(month, 10);
        return m >= 1 && m <= 12;
    }

    // 生成单个卡号
    function generateCard(bin, cvvLength, fixedCVV, fixedExpiryDate) {
        let number = bin;
        const targetLength = (cvvLength === 4) ? 15 : 16;
        while (number.length < targetLength - 1) {
            number += Math.floor(Math.random() * 10);
        }
        number += generateCheckDigit(number);
        const cvv = fixedCVV || generateRandomCVV(cvvLength);
        const expiryDate = fixedExpiryDate || generateRandomExpiryDate();
        return { number, expiryDate, cvv };
    }

    // Luhn 算法校验位生成
    function generateCheckDigit(number) {
        let sum = 0;
        let shouldDouble = true;
        for (let i = number.length - 1; i >= 0; i--) {
            let digit = parseInt(number.charAt(i), 10);
            if (shouldDouble) {
                digit *= 2;
                if (digit > 9) digit -= 9;
            }
            sum += digit;
            shouldDouble = !shouldDouble;
        }
        return ((10 - (sum % 10)) % 10).toString();
    }

    function generateRandomCVV(length) {
        return Math.floor(Math.random() * (10 ** length)).toString().padStart(length, '0');
    }

    function generateRandomExpiryDate() {
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        let year = currentYear + Math.floor(Math.random() * 5);
        let month = (year === currentYear)
            ? currentMonth + Math.floor(Math.random() * (13 - currentMonth))
            : Math.floor(Math.random() * 12) + 1;
        return `${month.toString().padStart(2, '0')}|${(year % 100).toString().padStart(2, '0')}`;
    }

    // 生成卡号逻辑
    function generateCards() {
        const binInput = $('binInput').value.trim();
        const quantity = parseInt($('quantity').value);
        try {
            const { bin, expiryDate, cvv } = parseBinInput(binInput);
            validateInputs(bin, expiryDate, cvv);
            generatedCards = [];
            const cvvLength = getCvvLength(bin);
            for (let i = 0; i < quantity; i++) {
                const card = generateCard(bin, cvvLength, cvv, expiryDate);
                generatedCards.push(`${card.number}|${card.expiryDate}|${card.cvv}`);
            }
            $('generatedCards').value = generatedCards.join('\n');
            // 同时更新自动填写面板的内容
            $('card-input').value = generatedCards.join('\n');
        } catch (error) {
            alert(error.message);
        }
    }

    // 清除卡号生成器面板输入
    function clearInputs() {
        $('binInput').value = "";
        $('quantity').value = "10";
        $('generatedCards').value = "";
    }

    // 复制文本并切换到自动填写面板
    function copyAndFill() {
        const allCards = $('generatedCards').value;
        navigator.clipboard.writeText(allCards).then(() => {
            $('card-input').value = allCards;
            showPanel('autofillPanel');
        }).catch(err => {
            console.error('无法复制文本: ', err);
        });
    }

    // ────────── 辅助：获取邮箱输入框 ──────────
    function getEmailInput() {
        // 1. 尝试使用常规选择器获取 input[type="email"] 或者 id 为 email 的元素
        let emailInput = document.querySelector('input[type="email"]') || document.getElementById('email');
        if (!emailInput) {
            // 2. 尝试使用指定Xpath查找
            try {
                const xpath = "/html/body/div[1]/div/div/div[2]/main/div/form/div[1]/div/div/div[1]/div[1]/div/div/div/div/div[2]/div/div[1]";
                let xpathResult = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                emailInput = xpathResult.singleNodeValue;
            } catch (e) {
                console.error("使用XPath查找邮箱输入框失败:", e);
            }
        }
        return emailInput;
    }

    // ────────── 地址生成辅助函数 ──────────
    function generateRandomAddress() {
        // 美国常见街道名称
        const streets = [
            "Main Street", "Park Avenue", "Oak Drive", "Maple Road", "Cedar Lane",
            "Pine Street", "Elm Street", "Washington Avenue", "Lake View Drive", "River Road",
            "Highland Avenue", "Valley View Road", "Forest Drive", "Sunset Boulevard", "Mountain View Drive"
        ];

        // 美国常见城市
        const cities = [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
            "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte"
        ];

        // 美国州及缩写
        const states = [
            {name: "California", abbr: "CA"}, {name: "Texas", abbr: "TX"},
            {name: "Florida", abbr: "FL"}, {name: "New York", abbr: "NY"},
            {name: "Pennsylvania", abbr: "PA"}, {name: "Illinois", abbr: "IL"},
            {name: "Ohio", abbr: "OH"}, {name: "Georgia", abbr: "GA"},
            {name: "North Carolina", abbr: "NC"}, {name: "Michigan", abbr: "MI"}
        ];

        // 生成随机数字
        const streetNumber = Math.floor(Math.random() * 9000) + 1000;
        const randomStreet = streets[Math.floor(Math.random() * streets.length)];
        const randomCity = cities[Math.floor(Math.random() * cities.length)];
        const randomState = states[Math.floor(Math.random() * states.length)];
                const zipCode = Math.floor(Math.random() * 90000) + 10000; // 5位数邮编

        return {
            address: `${streetNumber} ${randomStreet}`,
            city: randomCity,
            postalCode: zipCode.toString(),
            state: randomState.name,
            stateCode: randomState.abbr,
            country: "US"
        };
    }


    // 从 API 获取地址信息,如果失败则生成随机地址
    async function fetchAddressFromApi() {
        return new Promise((resolve) => {
            console.log('正在从 API 获取地址信息...');
            GM_xmlhttpRequest({
                method: 'GET',
                url: CONFIG.addressApiUrl,
                timeout: 5000, // 设置5秒超时
                onload: function (response) {
                    try {
                        if (response.status !== 200) {
                            throw new Error(`API响应错误: ${response.status}`);
                        }
                        const data = JSON.parse(response.responseText);
                        console.log('API返回数据:', data);
                        if (data && data.location && data.location.length > 0) {
                            const locationInfo = data.location[0];
                            console.log('使用的地址信息:', locationInfo);
                            resolve({
                                address: locationInfo.line1,
                                city: locationInfo.city,
                                postalCode: locationInfo.postal_code,
                                state: locationInfo.province,
                                country: locationInfo.country_iso2
                            });
                        } else {
                            throw new Error('API返回的数据中没有找到地址信息');
                        }
                    } catch (error) {
                        console.warn('处理 API 返回数据失败，使用随机生成的地址:', error);
                        const randomAddress = generateRandomAddress();
                        console.log('随机生成的地址:', randomAddress);
                        resolve(randomAddress);
                    }
                },
                onerror: function (error) {
                    console.warn('获取地址信息请求失败，使用随机生成的地址:', error);
                    const randomAddress = generateRandomAddress();
                    console.log('随机生成的地址:', randomAddress);
                    resolve(randomAddress);
                },
                ontimeout: function () {
                    console.warn('获取地址信息请求超时，使用随机生成的地址');
                    const randomAddress = generateRandomAddress();
                    console.log('随机生成的地址:', randomAddress);
                    resolve(randomAddress);
                }
            });
        });
    }

    // 自动填写逻辑
    async function handleAutoFill() {
        const cardInput = $('card-input').value.trim();
        const lines = processCardData(cardInput).split('\n').filter(line => line.trim() !== '');
        if (lines.length === 0) {
            alert('卡队列已空');
            return;
        }

        const cardData = lines.shift();
        $('card-input').value = lines.join('\n');

        const parts = cardData.split('|').map(p => p.trim());
        let cardNumber, month, year, cvc;
        if (parts.length >= 4) {
            [cardNumber, month, year, cvc] = parts;
        } else if (parts.length === 1) {
            cardNumber = parts[0];
            const now = new Date();
            month = (now.getMonth() + 1).toString().padStart(2, '0');
            year = (now.getFullYear() + 1).toString().slice(-2);
            cvc = '000';
        } else {
            alert('卡号格式不正确，应为：卡号|月|年|CVC 或者 卡号');
            return;
        }
        if (year.length === 4) year = year.slice(-2);
        console.log(`填入卡号信息：${cardNumber} | ${month}/${year} | ${cvc}`);

        try {
            // 获取邮箱输入框，适配不同页面定位
            const emailInput = getEmailInput();
            if (!emailInput) throw new Error('未找到邮箱输入框');
            // 判断是否具有 value 属性，否则尝试读取 innerText
            const emailValue = ('value' in emailInput && emailInput.value.trim()) || emailInput.innerText.trim();
            const emailName = emailValue.split('@')[0] || 'DefaultName';

            // 获取地址信息（API 或随机生成）
            const addressInfo = await fetchAddressFromApi();
            console.log('使用的地址信息:', addressInfo);

            // 填写主要表单字段
            const fields = {
                cardNumber: $('cardNumber'),
                cardExpiry: $('cardExpiry'),
                cardCvc: $('cardCvc'),
                billingName: $('billingName'),
                countrySelect: $('billingCountry')
            };

            if (Object.values(fields).every(field => field)) {
                await setNativeValue(fields.cardNumber, cardNumber);
                console.log('卡号已填写');
                await setNativeValue(fields.cardExpiry, `${month}/${year}`);
                console.log('到期日已填写');
                await setNativeValue(fields.cardCvc, cvc);
                console.log('CVC已填写');
                await setNativeValue(fields.billingName, emailName);
                console.log(`姓名已填写: ${emailName}`);
            } else {
                console.error('未找到主要表单字段，请确认页面是否正确。');
                alert('未找到主要表单字段，请确认页面是否正确。');
                return;
            }

            // 填写地址信息（如存在）
            const addressMappings = [
                { id: 'billingAddressLine1', value: addressInfo.address, label: '地址' },
                { id: 'billingLocality', value: addressInfo.city, label: '城市' },
                { id: 'billingPostalCode', value: addressInfo.postalCode, label: '邮政编码' },
                { id: 'billingAdministrativeArea', value: addressInfo.state || addressInfo.stateCode, label: '州/省' }
            ];
            for (const mapping of addressMappings) {
                const element = $(mapping.id);
                if (element && mapping.value) {
                    await setNativeValue(element, mapping.value);
                    console.log(`${mapping.label}已填写: ${mapping.value}`);
                }
            }

            SubmitClick();
        } catch (error) {
            console.error('填写表单时出错:', error);
            alert('填写表单时出错，请检查控制台日志。');
        }
    }


    // 处理卡号文本数据，提取符合格式的卡信息
    function processCardData(text) {
        text = text.replace(/\//g, '|');
        const matches = text.match(/(\d{15,16})\|?(\d{1,2})\|?(\d{2,4})\|?(\d{3,4})/g);
        return matches?.join('\n') || text;
    }

    // 模拟点击提交按钮
    function SubmitClick() {
        const submitButton = document.querySelector("button[data-testid='hosted-payment-submit-button']");
        if (submitButton) {
            submitButton.click();
            console.log("提交按钮已点击!");
        } else {
            console.log("提交按钮未找到。");
        }
    }



    // ────────── 面板显示控制 ──────────
    function toggleContainer() {
        const cardTools = $('cardTools');
        cardTools.style.display = (cardTools.style.display === 'none' || cardTools.style.display === '') ? 'block' : 'none';
        if (cardTools.style.display === 'block') {
            showPanel('mainMenu');
        }
    }
    function showPanel(panelId) {
        ['mainMenu', 'cardGenerator', 'autofillPanel'].forEach(id => {
            $(id).style.display = (id === panelId) ? 'block' : 'none';
        });
    }

    // ────────── 主题切换逻辑 ──────────
    function toggleTheme() {
        const themeSwitch = $('themeSwitch');
        const isDarkMode = themeSwitch.checked;

        if (isDarkMode) {
            document.documentElement.classList.add('dark-mode');
            localStorage.setItem(CONFIG.storageKey, 'dark');
        } else {
            document.documentElement.classList.remove('dark-mode');
            localStorage.setItem(CONFIG.storageKey, 'light');
        }

        // 切换标签：当选中时（深色模式激活）应显示"浅色模式"
        const label = document.querySelector('.switch-label');
        label.textContent = isDarkMode ? '浅色模式' : '深色模式';
    }

    function updateThemeLabel() {
        const themeSwitch = $('themeSwitch');
        const isDarkMode = themeSwitch.checked;
        const label = document.querySelector('.switch-label');
        label.textContent = isDarkMode ? '浅色模式' : '深色模式';
    }

    function initializeTheme() {
        const savedTheme = localStorage.getItem(CONFIG.storageKey);
        const themeSwitch = $('themeSwitch');
        if (savedTheme === 'dark') {
            document.documentElement.classList.add('dark-mode');
            themeSwitch.checked = true;
        } else {
            document.documentElement.classList.remove('dark-mode');
            themeSwitch.checked = false;
        }
        updateThemeLabel();
    }

    // ────────── Stripe 验证码检测器 ──────────
    function setupStripeCaptchaDetector() {
        console.log('🤖 Stripe 验证码检测器已启动');
        let captchaDetected = false;
        let captchaCompleted = false;
        let processingCard = false;

        function checkAndProcessNextCard() {
            if (captchaCompleted && !processingCard) {
                processingCard = true;
                console.log('✅ 验证码验证已完成，等待3秒后处理下一张卡...');
                setTimeout(() => {
                    console.log('🔄 处理下一张卡...');
                    handleAutoFill();
                    setTimeout(() => {
                        captchaDetected = false;
                        captchaCompleted = false;
                        processingCard = false;
                    }, 2000);
                }, 3000);
            }
        }

        const captchaObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType !== Node.ELEMENT_NODE) continue;
                        if (isCaptchaElement(node) && !captchaDetected) {
                            console.log('🔍 检测到验证码开始');
                            captchaDetected = true;
                        }
                    }
                }
                if (captchaDetected && mutation.removedNodes.length > 0) {
                    for (const node of mutation.removedNodes) {
                        if (node.nodeType !== Node.ELEMENT_NODE) continue;
                        if (isCaptchaElement(node)) {
                            console.log('👍 验证码框被移除，可能已完成验证');
                            captchaCompleted = true;
                            checkAndProcessNextCard();
                        }
                    }
                }
            }
        });

        captchaObserver.observe(document.documentElement, { childList: true, subtree: true });
        console.log('✅ Stripe 验证码检测器设置完成，等待验证码移除...');
    }

    function isCaptchaElement(node) {
        return node.matches && (
            node.matches('[data-hcaptcha-widget-id], iframe[src*="hcaptcha"], .h-captcha, #h-captcha, iframe[src*="stripe"], [data-stripe-captcha]') ||
            (node.querySelector && node.querySelector('[data-hcaptcha-widget-id], iframe[src*="hcaptcha"], .h-captcha, #h-captcha, iframe[src*="stripe"], [data-stripe-captcha]'))
        );
    }

    // ────────── 事件绑定 ──────────
    function bindEvents() {
        // 卡号生成器：绑定生成与清除按钮
        $('generateBtn').addEventListener('click', generateCards);
        $('clearBtn').addEventListener('click', clearInputs);
        $('copyAndFillBtn').addEventListener('click', copyAndFill);

        // 主菜单按钮
        $('generatorBtn').addEventListener('click', () => showPanel('cardGenerator'));
        $('autofillBtn').addEventListener('click', () => showPanel('autofillPanel'));

        // 自动填写面板中的提交按钮
        $('submit-button').addEventListener('click', () => {
            handleAutoFill();
            if (!captchaDetectorInitialized) {
                setupStripeCaptchaDetector();
                captchaDetectorInitialized = true;
                console.log('🔧 首次点击支付按钮，验证码检测器已启动');
            }
        });

        // 绑定所有返回按钮
        document.querySelectorAll('.back-button').forEach(btn => {
            btn.addEventListener('click', () => showPanel('mainMenu'));
        });

        // Toggle 按钮与主题开关
        toggleBtn.addEventListener('click', toggleContainer);
        $('themeSwitch').addEventListener('change', toggleTheme);
    }

    // ────────── 初始化 ──────────
    function init() {
        bindEvents();
        initializeTheme();
        $('cardTools').style.display = 'none';
    }
    init();
})();

