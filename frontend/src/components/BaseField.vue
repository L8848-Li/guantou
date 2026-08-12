<template>
  <view class="base-field">
    <view
      v-if="label"
      class="base-field-label"
    >
      {{ label }}
      <text
        v-if="required"
        class="base-field-required"
      >
        *
      </text>
    </view>
    <textarea
      v-if="type === 'textarea'"
      class="base-field-control base-field-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :disabled="disabled"
      :auto-height="autoHeight"
      @input="handleInput"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
    />
    <input
      v-else
      class="base-field-control"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :disabled="disabled"
      @input="handleInput"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
    >
    <view
      v-if="error"
      class="base-field-error"
    >
      {{ error }}
    </view>
  </view>
</template>

<script>
/**
 * 基础输入原语（M1·设计系统）
 * 统一输入框/文本域的标签、边框、错误提示样式，全部消费全局 Token；
 * 业务页面禁止再自写 .field/.login-input 等一次性输入样式。
 */
export default {
  name: 'BaseField',
  props: {
    modelValue: {
      type: [String, Number],
      default: '',
    },
    label: {
      type: String,
      default: '',
    },
    type: {
      type: String,
      default: 'text',
      validator: (value) => ['text', 'textarea', 'number', 'digit', 'password'].includes(value),
    },
    placeholder: {
      type: String,
      default: '',
    },
    maxlength: {
      type: Number,
      default: -1,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    required: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: '',
    },
    autoHeight: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:modelValue', 'input', 'blur', 'focus'],
  methods: {
    handleInput(event) {
      const value = event.detail?.value ?? '';
      this.$emit('update:modelValue', value);
      this.$emit('input', value);
    },
  },
};
</script>

<style scoped>
.base-field {
  margin-bottom: var(--space-3);
}

.base-field-label {
  margin-bottom: var(--space-1);
  color: var(--text-color);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.base-field-required {
  margin-left: 4rpx;
  color: var(--danger-color);
}

.base-field-control {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-color);
  color: var(--text-color);
  font-size: var(--font-size-base);
  box-sizing: border-box;
}

.base-field-textarea {
  min-height: 160rpx;
  line-height: 1.6;
}

.base-field-error {
  margin-top: var(--space-1);
  color: var(--danger-color);
  font-size: var(--font-size-xs);
}
</style>
