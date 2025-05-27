(function() {
  'use strict';

  // --- 配置参数 ---
  const scrollStep = 10; // 每次滚动的像素数 (可以调整)
  const scrollInterval = 150; // 滚动间隔时间，单位毫秒 (可以调整)
  // -----------------

  let intervalId = null;

  function autoScroll() {
    // 向下滚动
    window.scrollBy(0, scrollStep);

    // 检查是否已滚动到底部
    // window.innerHeight: 浏览器窗口的视口（viewport）高度
    // window.scrollY: 页面垂直方向已滚动的像素值
    // document.body.offsetHeight: 整个HTML文档的高度
    if ((window.innerHeight + Math.ceil(window.scrollY)) >= document.body.offsetHeight) {
      console.log('已滚动到底部。');
      stopAutoScroll(); // 如果想在到底后停止，就取消这行注释
    }
  }

  function startAutoScroll() {
    if (intervalId === null) {
      intervalId = setInterval(autoScroll, scrollInterval);
      console.log('自动滚动已启动。如需停止，请在控制台输入: stopAutoScroll()');
    } else {
      console.log('自动滚动已在运行中。');
    }
  }

  // 将停止函数暴露到全局作用域，方便手动停止
  window.stopAutoScroll = function() {
    if (intervalId !== null) {
      clearInterval(intervalId);
      intervalId = null;
      console.log('自动滚动已停止。');
    } else {
      console.log('自动滚动尚未启动。');
    }
  };

  // 自动开始滚动
  startAutoScroll();

  // 你也可以不自动开始，而是手动在控制台输入:
  // startAutoScroll()

})();