<template>
  <view class="section-block">
    <view
      v-if="title || actionText"
      class="section-head"
    >
      <text class="section-title">
        {{ title }}
      </text>
      <text
        v-if="actionText"
        class="section-action"
        @tap="$emit('action')"
      >
        {{ actionText }}
      </text>
    </view>
    <slot v-if="!empty" />
    <slot
      v-else
      name="empty"
    >
      <EmptyState
        :title="emptyTitle"
        :description="emptyDescription"
        :action-text="emptyActionText"
        @action="$emit('empty-action')"
      />
    </slot>
  </view>
</template>

<script>
import EmptyState from './EmptyState.vue';

export default {
  name: 'SectionBlock',
  components: {
    EmptyState,
  },
  props: {
    title: {
      type: String,
      default: '',
    },
    actionText: {
      type: String,
      default: '',
    },
    empty: {
      type: Boolean,
      default: false,
    },
    emptyTitle: {
      type: String,
      default: '暂无内容',
    },
    emptyDescription: {
      type: String,
      default: '',
    },
    emptyActionText: {
      type: String,
      default: '',
    },
  },
  emits: ['action', 'empty-action'],
};
</script>

<style scoped>
.section-block {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 28rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.section-title {
  font-size: 30rpx;
  font-weight: 700;
}

.section-action {
  flex: 0 0 auto;
  color: var(--accent-color);
  font-size: var(--font-size-sm);
}
</style>
