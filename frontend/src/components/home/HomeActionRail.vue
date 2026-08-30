<template>
  <view class="action-rail">
    <!-- 作者头像 + 关注角标 -->
    <view
      class="action-rail__author"
      @tap="openAuthor"
    >
      <image
        v-if="authorAvatar"
        class="action-rail__avatar"
        :src="authorAvatar"
        mode="aspectFill"
      />
      <view
        v-else
        class="action-rail__avatar action-rail__avatar--ghost"
      />
      <view
        class="action-rail__follow"
        :class="{ 'action-rail__follow--done': following }"
        :aria-label="following ? '已关注作者' : '关注作者'"
        @tap.stop="toggleFollow"
      >
        <view
          v-if="following"
          class="action-rail__check"
          aria-hidden="true"
        />
        <view
          v-else
          class="action-rail__plus"
          aria-hidden="true"
        />
      </view>
    </view>

    <!-- 赞：纯 CSS 实心爱心，激活态走情感暖色 + pop/光环/粒子反馈 -->
    <view
      class="action-rail__item"
      role="button"
      aria-label="点赞"
      @tap="toggleLike"
    >
      <view
        class="action-rail__bubble"
        :class="{
          'action-rail__bubble--liked': liked,
          'action-rail__bubble--burst': likeBurst,
        }"
      >
        <view
          class="action-rail__heart"
          :class="{ 'action-rail__heart--pop': likeBurst }"
          aria-hidden="true"
        />
      </view>
      <text
        class="action-rail__count"
        :class="{
          'action-rail__count--liked': liked,
          'action-rail__count--pop': likeBurst,
        }"
      >
        {{ formatCount(likeCount) }}
      </text>
    </view>

    <!-- 评论 -->
    <view
      class="action-rail__item"
      role="button"
      aria-label="评论"
      @tap="openComments"
    >
      <view class="action-rail__bubble">
        <view
          class="action-rail__comment-icon"
          aria-hidden="true"
        />
      </view>
      <text class="action-rail__count">
        {{ formatCount(can.comment_count || 0) }}
      </text>
    </view>

    <!-- 分享 -->
    <button
      class="action-rail__share-button"
      open-type="share"
      aria-label="分享"
      @tap="share"
    >
      <view class="action-rail__bubble">
        <view
          class="action-rail__share-icon"
          aria-hidden="true"
        />
      </view>
      <text class="action-rail__count">
        分享
      </text>
    </button>
  </view>
</template>

<script>
import { requireAuth } from '@/services/authGuard';
import { likeCan, unlikeCan } from '@/services/canSocial';
import { followUser, unfollowUser } from '@/services/following';
import { toUserPage } from '@/routers/user';
import { shareCanOnWeb } from '@/utils/shareCan';
import { openCommentSheet } from '@/services/commentSheet';

export default {
  name: 'HomeActionRail',
  props: {
    can: {
      type: Object,
      required: true,
    },
  },
  emits: ['share'],
  data() {
    return {
      liked: Boolean(this.can.liked_by_me),
      likeCount: Number(this.can.like_count || 0),
      likeBusy: false,
      following: Boolean(this.can.recorder_followed_by_me),
      followBusy: false,
      /* 点赞爆发反馈（一次性动画，定时撤除类名以便下次重触发） */
      likeBurst: false,
      likeBurstTimer: null,
    };
  },
  computed: {
    authorAvatar() {
      return this.can.recorder ? this.can.recorder.avatar : '';
    },
  },
  watch: {
    can(next) {
      this.liked = Boolean(next.liked_by_me);
      this.likeCount = Number(next.like_count || 0);
      this.following = Boolean(next.recorder_followed_by_me);
    },
  },
  beforeUnmount() {
    if (this.likeBurstTimer) clearTimeout(this.likeBurstTimer);
  },
  methods: {
    formatCount(value) {
      const count = Number(value || 0);
      if (count >= 10000) return `${(count / 10000).toFixed(1)}w`;
      if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
      return String(count);
    },
    openAuthor() {
      if (this.can.recorder && this.can.recorder.id) {
        toUserPage(this.can.recorder.id);
      }
    },
    async toggleFollow() {
      if (this.followBusy || !this.can.recorder) return;
      // 作者即本人时不提供关注自己。
      const myId = uni.getStorageSync('id');
      if (myId && Number(this.can.recorder.id) === Number(myId)) return;
      if (!requireAuth('follow', { page: 'home_feed', canId: this.can.id })) return;
      this.followBusy = true;
      const target = !this.following;
      this.following = target;
      try {
        if (target) {
          await followUser(this.can.recorder.id);
        } else {
          await unfollowUser(this.can.recorder.id);
        }
      } catch (error) {
        this.following = !target;
      } finally {
        this.followBusy = false;
      }
    },
    async toggleLike() {
      if (!requireAuth('like', { page: 'home_feed', canId: this.can.id })) return;
      if (this.likeBusy) return;
      this.likeBusy = true;
      const target = !this.liked;
      this.liked = target;
      this.likeCount += target ? 1 : -1;
      /* 乐观提交即触发反馈，失败回滚时撤销；取消赞路径清除残留爆发态 */
      if (target) {
        this.playLikeBurst();
      } else {
        this.clearLikeBurst();
      }
      try {
        const response = target ? await likeCan(this.can.id) : await unlikeCan(this.can.id);
        if (response && Number.isFinite(Number(response.like_count))) {
          this.liked = Boolean(response.liked);
          this.likeCount = Number(response.like_count);
        }
      } catch (error) {
        this.liked = !target;
        this.likeCount += target ? -1 : 1;
        /* 失败回滚时同步撤除爆发反馈 */
        this.clearLikeBurst();
      } finally {
        this.likeBusy = false;
      }
    },
    openComments() {
      // 半屏评论区（见 #219）：评论属于可浏览内容，发布/回复/点赞才需登录（见 #202）。
      openCommentSheet({ targetType: 'can', targetId: this.can.id, theme: 'immersive' });
    },
    async share() {
      this.$emit('share', this.can);
      // #ifdef H5
      await shareCanOnWeb(this.can);
      // #endif
    },
    playLikeBurst() {
      /* 乐观提交即触发：先清旧定时器并复位，$nextTick 后再置位，保证
       * 800ms 窗口期内「赞→取消→再赞」的第二次动画必然重启。
       * 代际序号让延迟置位可被 clearLikeBurst 作废：失败回滚后不会迟到置位 */
      if (this.likeBurstTimer) clearTimeout(this.likeBurstTimer);
      this.likeBurstTimer = null;
      this.likeBurst = false;
      this.likeBurstEpoch = (this.likeBurstEpoch || 0) + 1;
      const epoch = this.likeBurstEpoch;
      this.$nextTick(() => {
        /* 窗口期内被取消（失败回滚/取消赞）或被新一轮播放覆盖则放弃置位 */
        if (epoch !== this.likeBurstEpoch) return;
        this.likeBurst = true;
        /* 动画时长 0.6s，留一档余量后撤除类名，保证不循环且可再次触发 */
        this.likeBurstTimer = setTimeout(() => {
          this.likeBurst = false;
          this.likeBurstTimer = null;
        }, 800);
      });
    },
    clearLikeBurst() {
      /* 失败回滚/取消赞：作废尚未置位的延迟动作，并同步撤除定时器与类名 */
      this.likeBurstEpoch = (this.likeBurstEpoch || 0) + 1;
      if (this.likeBurstTimer) {
        clearTimeout(this.likeBurstTimer);
        this.likeBurstTimer = null;
      }
      this.likeBurst = false;
    },
  },
};
</script>

<style scoped>
.action-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 34rpx;
  /* v-if 挂载即播放：淡入 + 轻微右滑入，缓解互动栏瞬现感 */
  animation: action-rail-enter 0.2s ease-out;
}

@keyframes action-rail-enter {
  from {
    opacity: 0;
    transform: translateX(20rpx);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .action-rail {
    animation: none;
  }
}

/* ---------- 头像与关注 ---------- */
.action-rail__author {
  position: relative;
  margin-bottom: 8rpx;
}

.action-rail__avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  border: 3rpx solid var(--on-immersive-color);
  background: var(--immersive-surface-color);
}

.action-rail__avatar--ghost {
  opacity: 0.5;
}

.action-rail__follow {
  position: absolute;
  left: 50%;
  bottom: -18rpx;
  transform: translateX(-50%);
  width: 38rpx;
  height: 38rpx;
  border-radius: 50%;
  background: var(--immersive-accent-color);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.25s ease, transform 0.18s ease;
}

.action-rail__follow:active {
  transform: translateX(-50%) scale(0.88);
}

.action-rail__follow--done {
  background: var(--immersive-surface-strong-color);
  border: 1rpx solid var(--immersive-border-color);
}

/* 纯 CSS 加号 */
.action-rail__plus {
  position: relative;
  width: 20rpx;
  height: 20rpx;
}

.action-rail__plus::before,
.action-rail__plus::after {
  content: '';
  position: absolute;
  background: var(--immersive-bg-color);
  border-radius: 2rpx;
}

.action-rail__plus::before {
  left: 8rpx;
  top: 0;
  width: 4rpx;
  height: 20rpx;
}

.action-rail__plus::after {
  left: 0;
  top: 8rpx;
  width: 20rpx;
  height: 4rpx;
}

/* 纯 CSS 对勾 */
.action-rail__check {
  width: 16rpx;
  height: 8rpx;
  border-left: 4rpx solid var(--on-immersive-color);
  border-bottom: 4rpx solid var(--on-immersive-color);
  transform: rotate(-45deg);
  margin-top: -4rpx;
}

/* ---------- 互动项 ---------- */
.action-rail__item,
.action-rail__share-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.action-rail__share-button {
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  line-height: normal;
  font-size: inherit;
}

.action-rail__share-button::after {
  border: 0;
}

.action-rail__bubble {
  position: relative;
  width: 84rpx;
  height: 84rpx;
  border-radius: 50%;
  background: var(--immersive-surface-color);
  border: 1rpx solid var(--immersive-border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.18s ease, background-color 0.25s ease, border-color 0.25s ease;
}

.action-rail__item:active .action-rail__bubble {
  transform: scale(0.88);
}

/* 点赞激活：暖色描边接管，品牌绿仅留给结构性强调 */
.action-rail__bubble--liked {
  background: var(--immersive-surface-strong-color);
  border-color: var(--immersive-like-color);
}

/* 纯 CSS 实心爱心：与气泡/分享同为 ~40rpx 图标宽，节奏一致 */
.action-rail__heart {
  position: relative;
  width: 40rpx;
  height: 36rpx;
  color: var(--immersive-icon-color);
  transition: color 0.25s ease;
}

.action-rail__heart::before,
.action-rail__heart::after {
  content: '';
  position: absolute;
  top: 0;
  width: 20rpx;
  height: 32rpx;
  border-radius: 20rpx 20rpx 0 0;
  background: currentColor;
}

.action-rail__heart::before {
  left: 20rpx;
  transform: rotate(-45deg);
  transform-origin: 0 100%;
}

.action-rail__heart::after {
  left: 0;
  transform: rotate(45deg);
  transform-origin: 100% 100%;
}

.action-rail__bubble--liked .action-rail__heart {
  color: var(--immersive-like-color);
}

/* 已赞按压时暖色加深一档（派生态令牌消费点） */
.action-rail__item:active .action-rail__bubble--liked .action-rail__heart {
  color: var(--immersive-like-strong-color);
}

.action-rail__count {
  color: var(--on-immersive-muted-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  letter-spacing: 1rpx;
  transition: color 0.25s ease;
}

.action-rail__count--liked {
  color: var(--immersive-like-color);
}

/* ---------- 点赞爆发反馈（一次性，尊重 reduced-motion） ---------- */
.action-rail__heart--pop {
  animation: rail-like-pop 0.6s ease-out;
}

@keyframes rail-like-pop {
  0% {
    transform: scale(1);
  }

  35% {
    transform: scale(1.32);
  }

  65% {
    transform: scale(0.9);
  }

  100% {
    transform: scale(1);
  }
}

.action-rail__count--pop {
  animation: rail-count-pop 0.5s ease-out;
}

@keyframes rail-count-pop {
  0% {
    transform: translateY(0);
  }

  40% {
    transform: translateY(-8rpx) scale(1.12);
  }

  100% {
    transform: translateY(0) scale(1);
  }
}

/* 光环一闪：气泡外圈扩散淡出 */
.action-rail__bubble--burst::after {
  content: '';
  position: absolute;
  inset: -4rpx;
  border-radius: 50%;
  border: 3rpx solid var(--immersive-like-glow-color);
  pointer-events: none;
  animation: rail-like-ring 0.6s ease-out forwards;
}

@keyframes rail-like-ring {
  0% {
    transform: scale(0.75);
    opacity: 0.9;
  }

  100% {
    transform: scale(1.45);
    opacity: 0;
  }
}

/* 轻量粒子：单元素 + box-shadow 复刻六点星散，比多节点更便宜 */
.action-rail__bubble--burst::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 6rpx;
  height: 6rpx;
  margin: -3rpx 0 0 -3rpx;
  border-radius: 50%;
  background: var(--immersive-like-color);
  box-shadow:
    0 -36rpx 0 var(--immersive-like-color),
    31rpx -18rpx 0 var(--immersive-like-glow-color),
    31rpx 18rpx 0 var(--immersive-like-color),
    0 36rpx 0 var(--immersive-like-glow-color),
    -31rpx 18rpx 0 var(--immersive-like-color),
    -31rpx -18rpx 0 var(--immersive-like-glow-color);
  pointer-events: none;
  animation: rail-like-sparks 0.6s ease-out forwards;
}

@keyframes rail-like-sparks {
  0% {
    transform: scale(0.35);
    opacity: 0;
  }

  25% {
    opacity: 1;
  }

  100% {
    transform: scale(1.15);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .action-rail__heart--pop,
  .action-rail__count--pop,
  .action-rail__bubble--burst::before,
  .action-rail__bubble--burst::after {
    /* 降级为纯颜色变化：光环/粒子直接不渲染 */
    animation: none;
  }

  .action-rail__bubble--burst::before,
  .action-rail__bubble--burst::after {
    display: none;
  }
}

/* 纯 CSS 气泡图标：4rpx 描边，与爱心/转发箭头同语言 */
.action-rail__comment-icon {
  position: relative;
  width: 40rpx;
  height: 32rpx;
  border: 4rpx solid var(--immersive-icon-color);
  border-radius: 14rpx;
  box-sizing: border-box;
}

.action-rail__comment-icon::after {
  content: '';
  position: absolute;
  left: 6rpx;
  bottom: -10rpx;
  width: 0;
  height: 0;
  border-top: 10rpx solid var(--immersive-icon-color);
  border-left: 10rpx solid transparent;
}

/* 纯 CSS 转发箭头 */
.action-rail__share-icon {
  position: relative;
  width: 40rpx;
  height: 34rpx;
}

.action-rail__share-icon::before {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 30rpx;
  height: 24rpx;
  border: 4rpx solid var(--immersive-icon-color);
  border-top: 0;
  border-radius: 0 0 10rpx 10rpx;
  box-sizing: border-box;
}

.action-rail__share-icon::after {
  content: '';
  position: absolute;
  right: 2rpx;
  top: 0;
  width: 14rpx;
  height: 14rpx;
  border-top: 4rpx solid var(--immersive-icon-color);
  border-right: 4rpx solid var(--immersive-icon-color);
  transform: rotate(12deg);
}
</style>
