<template>
  <button
    class="base-button"
    :class="rootClass"
    :disabled="disabled || loading"
    @tap="handleTap"
  >
    <text
      v-if="loading"
      class="base-button-loading"
    >
      …
    </text>
    <slot>{{ text }}</slot>
  </button>
</template>

<script>
/**
 * 基础按钮原语（M1·设计系统）
 * 样式全部消费全局 Token，随明暗主题自动切换；
 * 业务页面禁止再自写 .primary-button/.small-button 等一次性按钮样式。
 */
export default {
  name: 'BaseButton',
  props: {
    variant: {
      type: String,
      default: 'primary',
      validator: (value) => ['primary', 'ghost', 'danger'].includes(value),
    },
    size: {
      type: String,
      default: 'medium',
      validator: (value) => ['small', 'medium'].includes(value),
    },
    text: {
      type: String,
      default: '',
    },
    block: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['click'],
  computed: {
    rootClass() {
      return [
        `base-button--${this.variant}`,
        `base-button--${this.size}`,
        { 'base-button--block': this.block },
      ];
    },
  },
  methods: {
    handleTap(event) {
      if (this.disabled || this.loading) return;
      this.$emit('click', event);
    },
  },
};
</script>

<style scoped>
.base-button {
  margin: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  font-weight: 600;
  box-sizing: border-box;
}

.base-button::after {
  border: 0;
}

.base-button--medium {
  min-height: 76rpx;
  padding: 0 var(--space-4);
  font-size: var(--font-size-base);
}

.base-button--small {
  min-height: 58rpx;
  padding: 0 var(--space-3);
  font-size: var(--font-size-sm);
}

.base-button--block {
  display: flex;
  width: 100%;
}

.base-button--primary {
  background: var(--accent-color);
  color: var(--on-accent-color);
}

.base-button--ghost {
  background: transparent;
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.base-button--danger {
  background: var(--danger-color);
  color: var(--on-danger-color);
}

.base-button[disabled] {
  opacity: 0.5;
}

.base-button-loading {
  line-height: 1;
}
</style>
