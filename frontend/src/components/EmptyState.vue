<template>
  <view class="empty-state">
    <view class="empty-title">
      {{ title }}
    </view>
    <view
      v-if="description"
      class="empty-description"
    >
      {{ description }}
    </view>
    <button
      v-if="actionText"
      class="empty-action"
      @tap="$emit('action')"
    >
      {{ actionText }}
    </button>
  </view>
</template>

<script>
export default {
  name: 'EmptyState',
  props: {
    title: {
      type: String,
      required: true,
    },
    description: {
      type: String,
      default: '',
    },
    actionText: {
      type: String,
      default: '',
    },
  },
  emits: ['action'],
};
</script>

<style scoped>
.empty-state {
  padding: 72rpx var(--space-3);
  text-align: center;
  color: var(--muted-color);
}

.empty-title {
  font-size: 30rpx;
  font-weight: 700;
  color: var(--text-secondary-color);
}

.empty-description {
  margin-top: 12rpx;
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.empty-action {
  margin-top: var(--space-3);
  width: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-color);
  color: var(--on-accent-color);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  padding: 0 28rpx;
}
</style>
