**使用方法:**

1.  **打开浏览器的开发者控制台。**（通常通过按F12，或右键点击页面并选择“检查”或“检查元素”，然后转到“控制台”选项卡。）

2.  **将上述整个代码块粘贴到控制台中。** 按Enter。这将定义函数。你应该会看到消息：“输入 `startAutoScrollDown()` 开始滚动，`stopAutoScrollDown()` 停止滚动。”

3.  **开始滚动：** 在控制台中输入 `startAutoScrollDown()` 并按Enter。

4.  **停止滚动：** 在控制台中输入 `stopAutoScrollDown()` 并按Enter。

**说明:**

*   **(IIFE - 立即调用的函数表达式)：** 整个代码被包装在 `(function() { ... })();` 中。这创建了一个自执行的匿名函数。这有助于避免变量污染全局作用域。

*   **`scrollInterval`：** 此变量存储定时器的ID。它初始化为 `null`，用于启动和停止滚动。

*   **`scrollAmount`：** 此变量确定每次间隔页面向下滚动的像素数。你可以调整此值以改变滚动速度。值越小，滚动越慢。

*   **`scrollDown()`：** 此函数使用 `window.scrollBy(0, scrollAmount)` 向下滚动页面。`scrollBy` 相对于当前位置滚动。`0` 表示没有水平滚动，`scrollAmount` 表示垂直滚动。

*   **`startScrolling()`：**
    *   检查 `scrollInterval` 是否已经设置（即滚动已经在进行中）。如果是，则什么也不做并记录一条消息。
    *   如果 `scrollInterval` 为 `null`，则表示滚动未激活。然后它使用 `setInterval(scrollDown, 1000)` 每1000毫秒（1秒）调用一次 `scrollDown()` 函数。`setInterval` 返回的ID存储在 `scrollInterval` 中。
    *   记录一条消息到控制台，指示滚动已开始。

*   **`stopScrolling()`：**
    *   检查 `scrollInterval` 是否已设置（即滚动是否处于活动状态）。如果没有，则什么也不做并记录一条消息。
    *   如果 `scrollInterval` 已设置，它使用 `clearInterval(scrollInterval)` 停止定时器。
    *   将 `scrollInterval` 重置为 `null`，表示滚动不再处于活动状态。
    *   记录一条消息到控制台，指示滚动已停止。

*   **`window.startAutoScrollDown = startScrolling;` 和 `window.stopAutoScrollDown = stopScrolling;`：** 这部分至关重要。它通过将 `startScrolling` 和 `stopScrolling` 函数分配给 `window` 对象的属性，使这些函数可以从浏览器控制台访问。没有这部分，你将无法调用这些函数。

**重要说明:**

*   该脚本会持续向下滚动页面。你需要使用 `stopAutoScrollDown()` 手动停止它。
*   调整 `scrollAmount` 以适应你的需求。值越小，滚动越平滑且越慢。
*   该脚本可能在某些网站上表现不佳，因为某些网站有自定义的滚动行为。
*   这是一个用于演示的简单脚本。你可以增强它，例如自动滚动到页面底部，或在页面上添加一个按钮来开始和停止滚动。