<template>
  <view
    class="entity-card"
    @tap="$emit('open', item)"
  >
    <view
      v-if="type"
      class="entity-type"
    >
      {{ type }}
    </view>
    <view class="entity-title">
      {{ title }}
    </view>
    <view
      v-if="description"
      class="entity-description"
    >
      {{ description }}
    </view>
    <view
      v-if="meta"
      class="entity-meta"
    >
      {{ meta }}
    </view>
  </view>
</template>

<script>
export default {
  name: 'EntityCard',
  props: {
    item: {
      type: Object,
      default: () => ({}),
    },
    type: {
      type: String,
      default: '',
    },
    title: {
      type: String,
      required: true,
    },
    description: {
      type: String,
      default: '',
    },
    meta: {
      type: String,
      default: '',
    },
  },
  emits: ['open'],
};
</script>

<style scoped>
.entity-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin-bottom: 18rpx;
  box-sizing: border-box;
}

.entity-type {
  color: var(--accent-color);
  font-size: var(--font-size-xs);
  margin-bottom: var(--space-1);
}

.entity-title {
  font-size: 34rpx;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.entity-description {
  margin-top: 10rpx;
  color: var(--text-secondary-color);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.entity-meta {
  margin-top: 14rpx;
  color: var(--muted-color);
  font-size: var(--font-size-xs);
}
</style>
