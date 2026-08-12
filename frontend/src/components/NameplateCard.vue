<template>
  <view :class="['plate', plate.is_primary ? 'primary-plate' : '']">
    <view class="plate-title">
      <text class="plate-text">
        {{ plate.display_text || plate.text_content || '未命名铭牌' }}
      </text>
      <text
        v-if="plate.is_primary"
        class="primary"
      >
        主铭牌
      </text>
    </view>
    <view class="plate-def">
      {{ plate.definition || '暂无释义' }}
    </view>
    <view
      v-if="plate.pronunciation_text"
      class="plate-source"
    >
      原样读音：{{ plate.pronunciation_text }}
    </view>
    <view class="plate-source">
      来源：{{ sourceText }}
    </view>
    <view
      v-if="plate.dialect"
      class="plate-source"
    >
      方言：{{ plate.dialect.qualified_code || plate.dialect.name }}
    </view>
    <button
      class="vote"
      :disabled="plate.status !== 'active'"
      @tap.stop="$emit(plate.supported_by_current_user ? 'unsupport' : 'support', plate.id)"
    >
      {{ plate.supported_by_current_user ? '取消支持' : '支持这张铭牌' }} · {{ plate.weight || 0 }}
    </button>
  </view>
</template>

<script>
export default {
  name: 'NameplateCard',
  props: {
    plate: {
      type: Object,
      required: true,
    },
  },
  emits: ['support', 'unsupport'],
  computed: {
    sourceText() {
      const source = this.plate.source || {};
      return [
        source.title,
        source.attributed_to,
        source.locator,
        source.note,
        this.plate.source_type,
      ].filter(Boolean).join(' · ') || '未注明';
    },
  },
};
</script>

<style scoped>
.plate {
  padding: 20rpx 0;
  border-bottom: 1px solid var(--border-color);
}

.primary-plate {
  background: var(--accent-subtle-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20rpx;
  margin-bottom: var(--space-2);
}

.plate-title {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  font-size: 32rpx;
  font-weight: 700;
}

.plate-text {
  min-width: 0;
  overflow-wrap: anywhere;
}

.primary {
  flex: 0 0 auto;
  color: var(--accent-color);
  font-size: var(--font-size-xs);
  background: var(--accent-subtle-color);
  padding: 4rpx 12rpx;
  border-radius: var(--radius-pill);
}

.plate-def,
.plate-source {
  margin-top: var(--space-1);
  color: var(--text-secondary-color);
  line-height: 1.5;
}

.plate-source {
  font-size: var(--font-size-xs);
  color: var(--muted-color);
}

.vote {
  margin: 14rpx 0 0;
  font-size: var(--font-size-xs);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  color: var(--text-color);
}

.vote[disabled] {
  color: var(--muted-color);
  background: var(--surface-subtle-color);
}
</style>
