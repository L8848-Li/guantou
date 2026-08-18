<template>
  <view
    class="vote-row"
    :class="{ 'vote-row--supported': supported }"
  >
    <view class="vote-row__main">
      <view class="vote-row__text">
        {{ nameplate.display_text }}
      </view>
      <view
        v-if="nameplate.definition"
        class="vote-row__definition"
      >
        {{ nameplate.definition }}
      </view>
    </view>
    <view
      class="vote-row__support"
      :class="{ 'vote-row__support--active': supported }"
      role="button"
      :aria-label="`支持铭牌 ${nameplate.display_text}`"
      @tap.stop="toggle"
    >
      <view
        class="vote-row__thumb"
        aria-hidden="true"
      />
      <text class="vote-row__count">
        {{ supported ? '已支持' : '支持' }} {{ supportCount }}
      </text>
    </view>
  </view>
</template>

<script>
import { requireAuth } from '@/services/authGuard';
import { supportNameplate, unsupportNameplate } from '@/services/guantou';

export default {
  name: 'NameplateVoteRow',
  props: {
    nameplate: {
      type: Object,
      required: true,
    },
  },
  emits: ['support', 'unsupport'],
  data() {
    return {
      supported: Boolean(this.nameplate.supported_by_current_user),
      supportCount: Number(this.nameplate.support_count || 0),
      busy: false,
    };
  },
  watch: {
    nameplate(next) {
      this.supported = Boolean(next.supported_by_current_user);
      this.supportCount = Number(next.support_count || 0);
    },
  },
  methods: {
    async toggle() {
      if (this.busy) return;
      const target = !this.supported;
      if (target && !requireAuth('nameplate_support', { nameplateId: this.nameplate.id })) {
        return;
      }
      this.busy = true;
      /* 乐观更新：先改本地态，失败再回滚 */
      this.supported = target;
      this.supportCount += target ? 1 : -1;
      try {
        const response = target
          ? await supportNameplate(this.nameplate.id)
          : await unsupportNameplate(this.nameplate.id);
        if (response && Number.isFinite(Number(response.support_count))) {
          this.supportCount = Number(response.support_count);
          this.supported = Boolean(response.supported_by_current_user);
        }
        this.$emit(target ? 'support' : 'unsupport', this.nameplate.id);
      } catch (error) {
        this.supported = !target;
        this.supportCount += target ? -1 : 1;
      } finally {
        this.busy = false;
      }
    },
  },
};
</script>

<style scoped>
.vote-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 18rpx 22rpx;
  border-radius: var(--radius-md);
  background: var(--immersive-surface-color);
  border: 1rpx solid var(--immersive-border-color);
  backdrop-filter: blur(8rpx);
}

.vote-row__main {
  flex: 1;
  min-width: 0;
}

.vote-row__text {
  color: var(--on-immersive-color);
  font-size: var(--font-size-lg);
  font-weight: 800;
  letter-spacing: 2rpx;
  overflow-wrap: anywhere;
}

.vote-row__definition {
  margin-top: 6rpx;
  color: var(--on-immersive-muted-color);
  font-size: var(--font-size-xs);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
}

.vote-row__support {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 12rpx 22rpx;
  border-radius: var(--radius-pill);
  border: 1rpx solid var(--immersive-border-color);
  background: var(--immersive-surface-strong-color);
  color: var(--on-immersive-color);
  font-size: var(--font-size-xs);
  font-weight: 700;
  transition: transform 0.18s ease, background-color 0.25s ease, border-color 0.25s ease;
}

.vote-row__support:active {
  transform: scale(0.94);
}

.vote-row__support--active {
  background: var(--immersive-accent-color);
  border-color: var(--immersive-accent-color);
  color: var(--immersive-bg-color);
}

/* 纯 CSS 拇指图标（双端一致，不依赖字体/图标库） */
.vote-row__thumb {
  position: relative;
  width: 22rpx;
  height: 20rpx;
}

.vote-row__thumb::before {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 7rpx;
  height: 12rpx;
  border-radius: 2rpx;
  background: currentColor;
}

.vote-row__thumb::after {
  content: '';
  position: absolute;
  left: 9rpx;
  bottom: 0;
  width: 13rpx;
  height: 14rpx;
  border-radius: 3rpx 6rpx 3rpx 2rpx;
  background: currentColor;
  clip-path: polygon(28% 100%, 100% 100%, 100% 30%, 62% 30%, 72% 0, 34% 0, 22% 42%, 28% 100%);
}
</style>
