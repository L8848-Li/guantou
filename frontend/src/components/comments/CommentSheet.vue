<template>
  <view
    v-if="rendered"
    class="comment-sheet"
    :class="`comment-sheet--${theme}`"
  >
    <view
      class="comment-sheet__mask"
      :class="{ 'comment-sheet__mask--visible': open }"
      aria-hidden="true"
      @tap="close"
    />
    <view
      class="comment-sheet__panel"
      :class="{
        'comment-sheet__panel--open': open,
        'comment-sheet__panel--expanded': expanded,
      }"
      :style="panelStyle"
      role="dialog"
      aria-label="评论面板"
    >
      <view
        class="comment-sheet__drag"
        aria-label="拖动展开或收起评论面板"
        @touchstart="onDragStart"
        @touchmove.prevent="onDragMove"
        @touchend="onDragEnd"
        @touchcancel="onDragEnd"
      >
        <view
          class="comment-sheet__handle"
          aria-hidden="true"
        />
      </view>
      <view class="comment-sheet__header">
        <text class="comment-sheet__title">
          {{ title }}
        </text>
        <view
          class="comment-sheet__close"
          role="button"
          aria-label="关闭评论面板"
          @tap="close"
        >
          ✕
        </view>
      </view>
      <view class="comment-sheet__body">
        <CommentThread
          v-if="open"
          variant="sheet"
          :target-type="targetType"
          :target-id="targetId"
          @created="$emit('created', $event)"
        />
      </view>
    </view>
  </view>
</template>

<script>
import CommentThread from '@/components/CommentThread.vue';

const CLOSE_THRESHOLD = 80;
const EXPAND_THRESHOLD = -80;
const EXIT_DURATION = 320;
/* 入场延迟：等初始 translateY(100%) 完成一次样式提交后再加开启类，
 * 否则挂载与开启同帧合并会导致入场过渡被跳过（关闭不受影响） */
const ENTER_DELAY = 32;

export default {
  name: 'CommentSheet',
  components: { CommentThread },
  props: {
    modelValue: {
      type: Boolean,
      default: false,
    },
    targetType: {
      type: String,
      required: true,
      validator: (value) => ['can', 'nameplate'].includes(value),
    },
    targetId: {
      type: [Number, String],
      default: null,
    },
    title: {
      type: String,
      default: '评论',
    },
    /* 沉浸主题消费 --immersive-*（首页 .immersive-shell 子树），
     * 常规主题消费明暗 token；两套色板经 --ct-* 变量注入面板子树 */
    theme: {
      type: String,
      default: 'immersive',
      validator: (value) => ['immersive', 'default'].includes(value),
    },
  },
  emits: ['update:modelValue', 'created'],
  data() {
    return {
      /* 支持以开启态直接挂载（如测试与恢复场景） */
      rendered: this.modelValue,
      open: this.modelValue,
      expanded: false,
      dragging: false,
      dragOffset: 0,
      startY: 0,
      enterTimer: null,
      exitTimer: null,
    };
  },
  computed: {
    panelStyle() {
      if (!this.dragOffset) return {};
      return {
        transform: `translateY(${this.dragOffset}px)`,
        transition: 'none',
      };
    },
  },
  watch: {
    modelValue(next) {
      if (next) {
        if (this.exitTimer) {
          clearTimeout(this.exitTimer);
          this.exitTimer = null;
        }
        this.rendered = true;
        this.$nextTick(() => {
          if (this.enterTimer) clearTimeout(this.enterTimer);
          this.enterTimer = setTimeout(() => {
            this.enterTimer = null;
            /* 32ms 内若已关闭则不再开启，避免残留开启态 */
            if (this.modelValue) this.open = true;
          }, ENTER_DELAY);
        });
      } else {
        if (this.enterTimer) {
          clearTimeout(this.enterTimer);
          this.enterTimer = null;
        }
        this.open = false;
        this.expanded = false;
        this.dragOffset = 0;
        this.exitTimer = setTimeout(() => {
          if (!this.modelValue) this.rendered = false;
          this.exitTimer = null;
        }, EXIT_DURATION);
      }
    },
  },
  beforeUnmount() {
    if (this.enterTimer) clearTimeout(this.enterTimer);
    if (this.exitTimer) clearTimeout(this.exitTimer);
  },
  methods: {
    close() {
      this.$emit('update:modelValue', false);
    },
    onDragStart(event) {
      const touch = event.touches && event.touches[0];
      if (!touch) return;
      this.dragging = true;
      this.startY = touch.clientY;
    },
    onDragMove(event) {
      if (!this.dragging) return;
      const touch = event.touches && event.touches[0];
      if (!touch) return;
      this.dragOffset = touch.clientY - this.startY;
    },
    onDragEnd() {
      if (!this.dragging) return;
      this.dragging = false;
      const offset = this.dragOffset;
      this.dragOffset = 0;
      if (offset > CLOSE_THRESHOLD) {
        /* 下滑：展开态先收回半屏，半屏态直接关闭 */
        if (this.expanded) {
          this.expanded = false;
        } else {
          this.close();
        }
      } else if (offset < EXPAND_THRESHOLD && !this.expanded) {
        this.expanded = true;
      }
    },
  },
};
</script>

<style scoped>
.comment-sheet {
  position: fixed;
  inset: 0;
  z-index: 90;
  pointer-events: none;
}

.comment-sheet__mask {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.28s ease-out;
  pointer-events: auto;
}

.comment-sheet--immersive .comment-sheet__mask {
  background: var(--immersive-veil-color);
}

.comment-sheet--default .comment-sheet__mask {
  background: var(--veil-color);
}

.comment-sheet__mask--visible {
  opacity: 1;
}

.comment-sheet__panel {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 50vh;
  display: flex;
  flex-direction: column;
  border-radius: 28rpx 28rpx 0 0;
  transform: translateY(100%);
  transition: transform 0.28s ease-out, height 0.28s ease-out;
  pointer-events: auto;
  overflow: hidden;
}

.comment-sheet__panel--open {
  transform: translateY(0);
}

.comment-sheet__panel--expanded {
  height: 82vh;
}

/* 沉浸主题（首页 .immersive-shell 子树）：固定深色面板 */
.comment-sheet--immersive .comment-sheet__panel {
  background: var(--immersive-bg-soft-color);
  border: 1rpx solid var(--immersive-border-color);
  border-bottom: 0;
  /* 注入 CommentThread 消费的 --ct-* 主题变量 */
  --ct-text: var(--on-immersive-color);
  --ct-muted: var(--on-immersive-muted-color);
  --ct-border: var(--immersive-border-color);
  --ct-surface: var(--immersive-surface-color);
  --ct-accent: var(--immersive-accent-color);
  --ct-on-accent: var(--immersive-bg-color);
}

/* 常规主题：跟随明暗 token */
.comment-sheet--default .comment-sheet__panel {
  background: var(--surface-color);
  border: 1rpx solid var(--border-color);
  border-bottom: 0;
}

.comment-sheet__drag {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  padding: 14rpx 0 6rpx;
}

.comment-sheet__handle {
  width: 72rpx;
  height: 8rpx;
  border-radius: var(--radius-pill);
}

.comment-sheet--immersive .comment-sheet__handle {
  background: var(--immersive-surface-strong-color);
}

.comment-sheet--default .comment-sheet__handle {
  background: var(--surface-subtle-color);
}

.comment-sheet__header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6rpx 28rpx 14rpx;
}

.comment-sheet__title {
  font-size: var(--font-size-base);
  font-weight: 900;
  letter-spacing: 1rpx;
}

.comment-sheet--immersive .comment-sheet__title {
  color: var(--on-immersive-color);
}

.comment-sheet--default .comment-sheet__title {
  color: var(--text-color);
}

.comment-sheet__close {
  width: 52rpx;
  height: 52rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26rpx;
}

.comment-sheet--immersive .comment-sheet__close {
  background: var(--immersive-surface-color);
  border: 1rpx solid var(--immersive-border-color);
  color: var(--on-immersive-muted-color);
}

.comment-sheet--default .comment-sheet__close {
  background: var(--surface-subtle-color);
  border: 1rpx solid var(--border-color);
  color: var(--muted-color);
}

.comment-sheet__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

@media (prefers-reduced-motion: reduce) {
  .comment-sheet__mask,
  .comment-sheet__panel {
    transition: none;
  }
}
</style>
