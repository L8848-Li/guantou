let currentAudioContext = null;
let managedHandle = null;
let preloadContext = null;

const MANAGED_THROTTLE_MS = 200;

function disposeManagedHandle() {
  if (!managedHandle) return;
  const handle = managedHandle;
  managedHandle = null;
  handle.destroy();
}

function releasePreload() {
  if (!preloadContext) return;
  const context = preloadContext;
  preloadContext = null;
  context.destroy();
}

/**
 * 释放预缓冲句柄（页面 onHide/onUnload 回收路径使用）。
 */
export function releasePreloadAudio() {
  releasePreload();
}

function stopCurrentAudio() {
  disposeManagedHandle();
  if (!currentAudioContext) return;
  currentAudioContext.stop();
  if (typeof currentAudioContext.destroy === 'function') {
    currentAudioContext.destroy();
  }
  currentAudioContext = null;
}

export function playAudio(src, warn = true) {
  if (!src || src === 'null') {
    if (warn) {
      uni.showToast({
        title: '不是一个可用文件',
        icon: 'error',
      });
    }
    return;
  }

  stopCurrentAudio();
  uni.showToast({
    title: '正在播放...',
    icon: 'none',
  });
  // #ifdef H5
  const audioElement = new Audio(src);
  let webAudioContext = null;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    const resolvedUrl = new URL(src, window.location.href);
    const canUseWebAudio = AudioContextClass
      && (resolvedUrl.origin === window.location.origin || resolvedUrl.protocol === 'blob:');
    if (canUseWebAudio) {
      webAudioContext = new AudioContextClass();
      const source = webAudioContext.createMediaElementSource(audioElement);
      source.connect(webAudioContext.destination);
    }
  } catch (error) {
    webAudioContext = null;
  }
  const webPlayback = {
    stop() {
      audioElement.pause();
      audioElement.currentTime = 0;
    },
    destroy() {
      // 先置空事件回调再清 src，避免清源触发的异步迟到 error
      // 误杀后续受控播放并弹出误导性 toast。
      audioElement.onerror = null;
      audioElement.onended = null;
      audioElement.src = '';
      if (webAudioContext && typeof webAudioContext.close === 'function') {
        webAudioContext.close();
      }
    },
  };
  currentAudioContext = webPlayback;
  audioElement.onerror = () => {
    if (currentAudioContext !== webPlayback) return;
    uni.showToast({ title: '播放失败', icon: 'none' });
    stopCurrentAudio();
  };
  audioElement.onended = () => {
    if (currentAudioContext === webPlayback) stopCurrentAudio();
  };
  const playPromise = audioElement.play();
  if (playPromise && typeof playPromise.catch === 'function') {
    playPromise.catch(() => {
      if (currentAudioContext !== webPlayback) return;
      uni.showToast({ title: '播放失败', icon: 'none' });
      stopCurrentAudio();
    });
  }
  // #endif

  // #ifndef H5
  const innerAudioContext = uni.createInnerAudioContext();
  currentAudioContext = innerAudioContext;
  innerAudioContext.onError(() => {
    uni.showToast({
      title: '播放失败',
      icon: 'none',
    });
    stopCurrentAudio();
  });
  innerAudioContext.onEnded(() => {
    if (currentAudioContext === innerAudioContext) {
      currentAudioContext = null;
    }
  });

  innerAudioContext.src = src;
  innerAudioContext.play();
  // #endif
}

export function stopAudio() {
  stopCurrentAudio();
  // 页面 onHide/onUnload 调 stopAudio 时一并回收预缓冲句柄。
  releasePreload();
}

/**
 * 事件化受控播放（首页沉浸流 Issue #192 使用）。
 *
 * 与 playAudio 的区别：
 * - 不弹「正在播放...」toast，播放状态由调用方自行呈现；
 * - 返回受控句柄，回调 onEnded/onTimeUpdate/onError；
 * - 全局互斥：调用时会停掉任何其他播放（含旧 API），
 *   playAudio/stopAudio 也会停掉受控播放；
 * - onTimeUpdate 回调按约 200ms 节流。
 */
function createWebManaged(src, { onEnded, onTimeUpdate, onError }) {
  const audioElement = new Audio(src);
  audioElement.preload = 'auto';
  let lastEmitAt = 0;
  let handle = null;
  const handleTimeUpdate = () => {
    if (managedHandle !== handle) return;
    const now = Date.now();
    if (now - lastEmitAt < MANAGED_THROTTLE_MS) return;
    lastEmitAt = now;
    if (onTimeUpdate) {
      onTimeUpdate({
        currentTime: audioElement.currentTime || 0,
        duration: audioElement.duration || 0,
      });
    }
  };
  const handleEnded = () => {
    if (managedHandle !== handle) return;
    managedHandle = null;
    if (onEnded) onEnded();
  };
  const handleError = () => {
    if (managedHandle !== handle) return;
    managedHandle = null;
    if (onError) onError(new Error('playback failed'));
  };
  audioElement.addEventListener('timeupdate', handleTimeUpdate);
  audioElement.addEventListener('ended', handleEnded);
  audioElement.addEventListener('error', handleError);
  handle = {
    src,
    stop() {
      audioElement.pause();
      audioElement.currentTime = 0;
    },
    destroy() {
      audioElement.pause();
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('error', handleError);
      audioElement.src = '';
    },
  };
  const playPromise = audioElement.play();
  if (playPromise && typeof playPromise.catch === 'function') {
    playPromise.catch(() => handleError());
  }
  return handle;
}

function createNativeManaged(src, { onEnded, onTimeUpdate, onError }) {
  const innerAudioContext = uni.createInnerAudioContext();
  let lastEmitAt = 0;
  let handle = null;
  innerAudioContext.onTimeUpdate(() => {
    if (managedHandle !== handle) return;
    const now = Date.now();
    if (now - lastEmitAt < MANAGED_THROTTLE_MS) return;
    lastEmitAt = now;
    if (onTimeUpdate) {
      onTimeUpdate({
        currentTime: innerAudioContext.currentTime || 0,
        duration: innerAudioContext.duration || 0,
      });
    }
  });
  innerAudioContext.onEnded(() => {
    if (managedHandle !== handle) return;
    managedHandle = null;
    if (onEnded) onEnded();
  });
  innerAudioContext.onError(() => {
    if (managedHandle !== handle) return;
    managedHandle = null;
    if (onError) onError(new Error('playback failed'));
  });
  handle = {
    src,
    stop() {
      innerAudioContext.stop();
    },
    destroy() {
      innerAudioContext.destroy();
    },
  };
  innerAudioContext.src = src;
  innerAudioContext.play();
  return handle;
}

export function playManaged(src, callbacks = {}) {
  if (!src || src === 'null') {
    if (callbacks.onError) callbacks.onError(new Error('invalid audio source'));
    return null;
  }

  stopCurrentAudio();

  let handle = null;
  // #ifdef H5
  handle = createWebManaged(src, callbacks);
  // #endif
  // #ifndef H5
  handle = createNativeManaged(src, callbacks);
  // #endif
  managedHandle = handle;
  return handle;
}

/**
 * 预缓冲下一罐音频（最多保留 1 个，新的会顶掉旧的）。
 */
export function preload(src) {
  if (!src || src === 'null') return;
  if (managedHandle && managedHandle.src === src) return;
  releasePreload();

  // #ifdef H5
  const audioElement = new Audio();
  audioElement.preload = 'auto';
  audioElement.src = src;
  preloadContext = {
    src,
    destroy() {
      audioElement.src = '';
    },
  };
  // #endif

  // #ifndef H5
  const innerAudioContext = uni.createInnerAudioContext();
  innerAudioContext.src = src;
  preloadContext = {
    src,
    destroy() {
      innerAudioContext.destroy();
    },
  };
  // #endif
}
