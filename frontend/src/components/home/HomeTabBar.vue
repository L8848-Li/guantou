<template>
  <view class="home-tab-bar">
    <view class="home-tab-bar__inner">
      <!-- 首页 -->
      <view
        class="home-tab-bar__item"
        :class="{ 'home-tab-bar__item--active': active === 'home' }"
        role="button"
        aria-label="罐头"
        @tap="openHome"
      >
        <view
          class="tab-icon tab-icon--home"
          aria-hidden="true"
        />
        <text class="home-tab-bar__label">
          罐头
        </text>
      </view>

      <!-- 图鉴 -->
      <view
        class="home-tab-bar__item"
        :class="{ 'home-tab-bar__item--active': active === 'atlas' }"
        role="button"
        aria-label="图鉴"
        @tap="openAtlas"
      >
        <view
          class="tab-icon tab-icon--atlas"
          aria-hidden="true"
        />
        <text class="home-tab-bar__label">
          图鉴
        </text>
      </view>

      <!-- 中央凸起装罐键 -->
      <view
        class="home-tab-bar__item home-tab-bar__item--center"
        role="button"
        aria-label="装罐"
        @tap="openCreate"
      >
        <view class="home-tab-bar__create">
          <view
            class="home-tab-bar__create-plus"
            aria-hidden="true"
          />
        </view>
        <text class="home-tab-bar__label home-tab-bar__label--create">
          装罐
        </text>
      </view>

      <!-- 集盒 -->
      <view
        class="home-tab-bar__item"
        :class="{ 'home-tab-bar__item--active': active === 'box' }"
        role="button"
        aria-label="集盒"
        @tap="openBox"
      >
        <view
          class="tab-icon tab-icon--box"
          aria-hidden="true"
        />
        <text class="home-tab-bar__label">
          集盒
        </text>
      </view>

      <!-- 我的 -->
      <view
        class="home-tab-bar__item"
        :class="{ 'home-tab-bar__item--active': active === 'me' }"
        role="button"
        aria-label="我的"
        @tap="openMine"
      >
        <view
          class="tab-icon tab-icon--me"
          aria-hidden="true"
        />
        <text class="home-tab-bar__label">
          我的
        </text>
      </view>
    </view>
  </view>
</template>

<script>
import { requireAuth } from '@/services/authGuard';
import {
  goAtlas, goCreateCan, goHome, goMine, goShelves,
} from '@/services/navigation';

export default {
  name: 'HomeTabBar',
  props: {
    active: {
      type: String,
      default: 'home',
    },
  },
  methods: {
    openHome() {
      if (this.active === 'home') return;
      goHome(true);
    },
    openAtlas() {
      if (this.active === 'atlas') return;
      goAtlas(true);
    },
    openCreate() {
      if (!requireAuth('record_can', { page: 'home_tab_bar' })) return;
      goCreateCan();
    },
    openBox() {
      if (this.active === 'box') return;
      goShelves(true);
    },
    openMine() {
      if (this.active === 'me') return;
      goMine(true);
    },
  },
};
</script>

<style scoped>
.home-tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  background: var(--immersive-veil-color);
  border-top: 1rpx solid var(--immersive-border-color);
  backdrop-filter: blur(18rpx);
  padding-bottom: env(safe-area-inset-bottom);
}

.home-tab-bar__inner {
  display: flex;
  align-items: flex-end;
  height: 108rpx;
}

.home-tab-bar__item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  padding-bottom: 10rpx;
}

.home-tab-bar__label {
  color: var(--on-immersive-muted-color);
  font-size: 20rpx;
  letter-spacing: 2rpx;
  transition: color 0.2s ease;
}

.home-tab-bar__item--active .home-tab-bar__label {
  color: var(--immersive-accent-color);
  font-weight: 800;
}

/* ---------- 中央凸起装罐键 ---------- */
.home-tab-bar__item--center {
  justify-content: flex-end;
}

.home-tab-bar__create {
  position: relative;
  /* 建立独立层叠上下文：保证 ::before 的 z-index: -1 光晕
   * 只沉到按钮本体之下，而不会沉到页面背景之下（H5/小程序一致） */
  isolation: isolate;
  width: 104rpx;
  height: 104rpx;
  margin-top: -58rpx;
  border-radius: 50%;
  background: linear-gradient(
    145deg,
    var(--immersive-accent-color),
    var(--immersive-bg-strong-color)
  );
  border: 6rpx solid var(--immersive-bg-color);
  /* 底座投影光晕 + 顶部内侧边缘高光，提升凸起层次 */
  box-shadow:
    0 12rpx 32rpx var(--immersive-glow-color),
    inset 0 3rpx 6rpx var(--immersive-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* 底座扩散光晕：比按钮更大一圈的柔光，固定垫底 */
.home-tab-bar__create::before {
  content: '';
  position: absolute;
  inset: -16rpx;
  border-radius: 50%;
  background: radial-gradient(circle, var(--immersive-glow-color) 0%, transparent 70%);
  z-index: -1;
  pointer-events: none;
}

/* 按下反馈：缩小同时收窄光晕，有“按进去”的触感 */
.home-tab-bar__create:active {
  transform: scale(0.92);
  box-shadow:
    0 6rpx 16rpx var(--immersive-glow-color),
    inset 0 3rpx 6rpx var(--immersive-border-color);
}

.home-tab-bar__create-plus {
  position: relative;
  width: 40rpx;
  height: 40rpx;
}

.home-tab-bar__create-plus::before,
.home-tab-bar__create-plus::after {
  content: '';
  position: absolute;
  background: var(--on-immersive-color);
  border-radius: 4rpx;
}

.home-tab-bar__create-plus::before {
  left: 17rpx;
  top: 0;
  width: 6rpx;
  height: 40rpx;
}

.home-tab-bar__create-plus::after {
  left: 0;
  top: 17rpx;
  width: 40rpx;
  height: 6rpx;
}

.home-tab-bar__label--create {
  margin-top: 2rpx;
  color: var(--on-immersive-color);
  font-weight: 800;
}

/* ---------- 纯 CSS 图标 ----------
 * 统一语言：4rpx 描边、内圆角 6~8rpx、currentColor 染色，
 * 选中态由颜色切换（muted → accent）表达，五槽位同节奏。 */
.tab-icon {
  position: relative;
  width: 40rpx;
  height: 36rpx;
  color: var(--on-immersive-muted-color);
  transition: color 0.2s ease;
}

.home-tab-bar__item--active .tab-icon {
  color: var(--immersive-accent-color);
}

/* 罐头：罐体轮廓 + 椭圆罐盖 */
.tab-icon--home::before {
  content: '';
  position: absolute;
  left: 8rpx;
  bottom: 0;
  width: 24rpx;
  height: 26rpx;
  border: 4rpx solid currentColor;
  border-radius: 6rpx;
  box-sizing: border-box;
}

.tab-icon--home::after {
  content: '';
  position: absolute;
  left: 6rpx;
  top: 0;
  width: 28rpx;
  height: 10rpx;
  border: 4rpx solid currentColor;
  border-radius: 50%;
  box-sizing: border-box;
}

/* 图鉴：卡片册（书脊 + 封面条目） */
.tab-icon--atlas {
  width: 34rpx;
  height: 34rpx;
  margin-top: 1rpx;
  border: 4rpx solid currentColor;
  border-radius: 8rpx;
  box-sizing: border-box;
}

.tab-icon--atlas::before {
  content: '';
  position: absolute;
  left: 5rpx;
  top: 0;
  bottom: 0;
  width: 4rpx;
  background: currentColor;
}

.tab-icon--atlas::after {
  content: '';
  position: absolute;
  left: 15rpx;
  top: 7rpx;
  width: 8rpx;
  height: 4rpx;
  border-radius: 2rpx;
  background: currentColor;
  box-shadow: 0 9rpx 0 currentColor;
}

/* 集盒：盒身 + 盖沿分隔线 + 提手凸点 */
.tab-icon--box {
  width: 36rpx;
  height: 32rpx;
  margin-top: 2rpx;
  border: 4rpx solid currentColor;
  border-radius: 8rpx;
  box-sizing: border-box;
}

.tab-icon--box::before {
  content: '';
  position: absolute;
  left: -4rpx;
  right: -4rpx;
  top: 8rpx;
  height: 4rpx;
  background: currentColor;
}

.tab-icon--box::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 12rpx;
  width: 10rpx;
  height: 4rpx;
  margin-left: -5rpx;
  border-radius: 2rpx;
  background: currentColor;
}

/* 我的：线框头像 + 肩部 */
.tab-icon--me::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 18rpx;
  height: 18rpx;
  border: 4rpx solid currentColor;
  border-radius: 50%;
  box-sizing: border-box;
}

.tab-icon--me::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 34rpx;
  height: 14rpx;
  border: 4rpx solid currentColor;
  border-bottom: 0;
  border-radius: 14rpx 14rpx 0 0;
  box-sizing: border-box;
}

@media (prefers-reduced-motion: reduce) {
  .tab-icon,
  .home-tab-bar__label {
    transition: none;
  }

  .home-tab-bar__create {
    transition: none;
  }
}
</style>
