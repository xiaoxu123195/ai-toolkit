(function() {
  let scrollInterval;
  const scrollAmount = 50; // 调整此值以改变滚动速度。值越小，速度越慢。

  function scrollDown() {
    window.scrollBy(0, scrollAmount);
  }

  function startScrolling() {
    if (!scrollInterval) {
      scrollInterval = setInterval(scrollDown, 1000); // 每1秒（1000毫秒）滚动一次
      console.log("已开始自动向下滚动页面。");
    } else {
      console.log("自动滚动已经在运行。");
    }
  }

  function stopScrolling() {
    if (scrollInterval) {
      clearInterval(scrollInterval);
      scrollInterval = null;
      console.log("已停止自动滚动。");
    } else {
      console.log("自动滚动未在运行。");
    }
  }


  // 将函数暴露到全局作用域，以便可以从控制台调用它们。
  window.startAutoScrollDown = startScrolling;
  window.stopAutoScrollDown = stopScrolling;

  console.log("输入 `startAutoScrollDown()` 开始滚动，`stopAutoScrollDown()` 停止滚动。");
})();