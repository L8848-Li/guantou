<template>
  <view
    class="plate-card"
    :class="{
      'plate-card--supported': supported,
      'plate-card--compact': compact,
    }"
  >
    <view
      class="plate-card__body"
      role="button"
      :aria-label="`查看铭牌 ${nameplate.display_text}`"
      @tap="openDetail"
    >
      <view class="plate-card__eyebrow">
        {{ nameplate.is_primary ? '主铭牌' : '铭牌' }} · {{ dialectText }}
      </view>
      <view class="plate-card__writing">
        {{ nameplate.display_text }}
      </view>
      <view
        v-if="readingText"
        class="plate-card__reading"
      >
        {{ readingText }}
      </view>
      <view
        v-if="nameplate.definition"
        class="plate-card__definition"
      >
        {{ nameplate.definition }}
      </view>
      <view class="plate-card__source">
        {{ sourceText }} · 点按查看依据
      </view>
    </view>

    <view class="plate-card__actions">
      <view
        class="plate-card__action vote-row__support"
        :class="{
          'plate-card__action--active': supported,
          'vote-row__support--burst': supportBurst,
        }"
        role="button"
        @tap.stop="toggle"
      >
        {{ supported ? '已支持' : '支持' }} {{ supportCount }}
      </view>
      <view
        class="plate-card__action plate-card__comment"
        role="button"
        @tap.stop="openComments"
      >
        评论 {{ commentCount }}
      </view>
      <view
        class="plate-card__action plate-card__action--debate"
        role="button"
        @tap.stop="openDebate"
      >
        立论
      </view>
    </view>
  </view>
</template>

<script>
import { requireAuth } from '@/services/authGuard';
import { supportNameplate, unsupportNameplate } from '@/services/guantou';
import { openCommentSheet } from '@/services/commentSheet';
import {
  goCreateNameplate,
  goNameplateDetail,
} from '@/services/navigation';

const SOURCE_LABELS = {
  creator: '创作者自述',
  oral: '口述',
  fieldwork: '田野记录',
  book: '书籍',
  article: '论文 / 文章',
  archive: '档案',
  web: '网页',
  other: '其他来源',
};

export default {
  name: 'NameplateVoteRow',
  props: {
    nameplate: {
      type: Object,
      required: true,
    },
    canId: {
      type: [Number, String],
      default: null,
    },
    /* 紧凑形态：首页副铭牌预览用，缩小字号内边距、释义限 1 行、隐藏来源行；
     * 操作条保留（按钮小一号），支持/评论/立论与主铭牌一致可用 */
    compact: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['support', 'unsupport'],
  data() {
    return {
      supported: Boolean(this.nameplate.supported_by_current_user),
      supportCount: Number(this.nameplate.support_count || 0),
      busy: false,
      /* 支持成功时的一次性爆发反馈（与点赞同一套反馈语言） */
      supportBurst: false,
      supportBurstTimer: null,
    };
  },
  computed: {
    dialectText() {
      return this.nameplate.dialect?.name || '方言点待补';
    },
    readingText() {
      const pronunciation = this.nameplate.pronunciation || {};
      const base = pronunciation.base_romanization || '';
      const surface = pronunciation.surface_romanization
        || this.nameplate.pronunciation_text
        || pronunciation.ipa
        || '';
      if (base && surface && base !== surface) return `${base} → ${surface}`;
      return surface || base;
    },
    sourceText() {
      const type = this.nameplate.source_type || this.nameplate.source?.type || 'other';
      const title = this.nameplate.source?.title || this.nameplate.source?.attributed_to;
      return title || SOURCE_LABELS[type] || SOURCE_LABELS.other;
    },
    commentCount() {
      return Number(this.nameplate.comment_count || 0);
    },
  },
  watch: {
    nameplate(next) {
      this.supported = Boolean(next.supported_by_current_user);
      this.supportCount = Number(next.support_count || 0);
    },
  },
  beforeUnmount() {
    if (this.supportBurstTimer) clearTimeout(this.supportBurstTimer);
  },
  methods: {
    openDetail() {
      goNameplateDetail(this.nameplate.id);
    },
    openComments() {
      // 半屏评论区（见 #219）：评论属于可浏览内容，发布/回复/点赞才需登录。
      openCommentSheet({ targetType: 'nameplate', targetId: this.nameplate.id, theme: 'immersive' });
    },
    openDebate() {
      // “立论”创建竞争性观点，不代表修订或取代当前铭牌。
      if (!requireAuth('nameplate_create', {
        canId: this.canId,
        nameplateId: this.nameplate.id,
      })) return;
      goCreateNameplate(this.canId, this.nameplate.id);
    },
    async toggle() {
      if (this.busy) return;
      const target = !this.supported;
      if (target && !requireAuth('nameplate_support', {
        nameplateId: this.nameplate.id,
        canId: this.canId,
      })) return;

      this.busy = true;
      this.supported = target;
      this.supportCount += target ? 1 : -1;
      /* 乐观提交即触发反馈，失败回滚时撤销；撤销支持路径清除残留爆发态 */
      if (target) {
        this.playSupportBurst();
      } else {
        this.clearSupportBurst();
      }
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
        /* 失败回滚时同步撤除爆发反馈 */
        this.clearSupportBurst();
      } finally {
        this.busy = false;
      }
    },
    playSupportBurst() {
      /* 乐观提交即触发：先清旧定时器并复位，$nextTick 后再置位，保证
       * 700ms 窗口期内「支持→撤销→再支持」的第二次动画必然重启。
       * 代际序号让延迟置位可被 clearSupportBurst 作废：失败回滚后不会迟到置位 */
      if (this.supportBurstTimer) clearTimeout(this.supportBurstTimer);
      this.supportBurstTimer = null;
      this.supportBurst = false;
      this.supportBurstEpoch = (this.supportBurstEpoch || 0) + 1;
      const epoch = this.supportBurstEpoch;
      this.$nextTick(() => {
        /* 窗口期内被取消（失败回滚/撤销支持）或被新一轮播放覆盖则放弃置位 */
        if (epoch !== this.supportBurstEpoch) return;
        this.supportBurst = true;
        /* 动画 0.5s，留余量后撤除类名，保证不循环且可再次触发 */
        this.supportBurstTimer = setTimeout(() => {
          this.supportBurst = false;
          this.supportBurstTimer = null;
        }, 700);
      });
    },
    clearSupportBurst() {
      /* 失败回滚/撤销支持：作废尚未置位的延迟动作，并同步撤除定时器与类名 */
      this.supportBurstEpoch = (this.supportBurstEpoch || 0) + 1;
      if (this.supportBurstTimer) {
        clearTimeout(this.supportBurstTimer);
        this.supportBurstTimer = null;
      }
      this.supportBurst = false;
    },
  },
};
</script>

<style scoped>
.plate-card {
  overflow: hidden;
  border: 1rpx solid var(--immersive-border-color);
  border-radius: var(--radius-lg);
  background: var(--immersive-surface-color);
  backdrop-filter: blur(12rpx);
}

.plate-card__body {
  padding: 22rpx 24rpx 18rpx;
}

.plate-card__eyebrow {
  color: var(--immersive-accent-color);
  font-size: 19rpx;
  font-weight: 800;
  letter-spacing: 3rpx;
}

.plate-card__writing {
  margin-top: 8rpx;
  color: var(--on-immersive-color);
  font-size: 46rpx;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: 4rpx;
}

.plate-card__reading {
  margin-top: 8rpx;
  color: var(--on-immersive-color);
  font-size: 25rpx;
  letter-spacing: 2rpx;
}

.plate-card__definition {
  margin-top: 10rpx;
  color: var(--on-immersive-muted-color);
  font-size: 23rpx;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.plate-card__source {
  margin-top: 12rpx;
  color: var(--on-immersive-muted-color);
  font-size: 19rpx;
  letter-spacing: 1rpx;
}

.plate-card__actions {
  display: flex;
  gap: 1rpx;
  border-top: 1rpx solid var(--immersive-border-color);
  background: var(--immersive-border-color);
}

.plate-card__action {
  flex: 1;
  position: relative;
  padding: 17rpx 8rpx;
  background: var(--immersive-surface-strong-color);
  color: var(--on-immersive-color);
  text-align: center;
  font-size: 21rpx;
  font-weight: 800;
  transition: transform 0.18s ease, background-color 0.25s ease;
}

.plate-card__action:active {
  transform: scale(0.94);
}

.plate-card__action--active,
.plate-card__action--debate {
  background: var(--immersive-accent-color);
  color: var(--immersive-bg-color);
}

/* ---------- 支持爆发反馈（一次性，与点赞同一套语言） ---------- */
.vote-row__support--burst {
  animation: support-pop 0.5s ease-out;
}

@keyframes support-pop {
  0% {
    transform: scale(1);
  }

  35% {
    transform: scale(1.1);
  }

  100% {
    transform: scale(1);
  }
}

/* 高光一闪：按钮内侧柔光淡入淡出 */
.vote-row__support--burst::after {
  content: '';
  position: absolute;
  inset: 4rpx;
  border-radius: var(--radius-sm);
  box-shadow: 0 0 20rpx var(--immersive-glow-color);
  pointer-events: none;
  animation: support-flash 0.5s ease-out forwards;
}

@keyframes support-flash {
  0% {
    opacity: 0;
  }

  30% {
    opacity: 1;
  }

  100% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  /* 降级为纯颜色变化 */
  .vote-row__support--burst {
    animation: none;
  }

  .vote-row__support--burst::after {
    display: none;
  }

  .plate-card__action {
    transition: none;
  }
}

/* ---------- 紧凑形态（首页副铭牌） ----------
 * 通过 prop 而非 :deep() 实现：小程序端组件样式隔离，scoped 穿透不可靠；
 * 由组件自身渲染紧凑 class，双端行为一致，且默认 false 不影响既有调用方。 */
.plate-card--compact .plate-card__body {
  padding: 14rpx 20rpx 12rpx;
}

.plate-card--compact .plate-card__writing {
  margin-top: 6rpx;
  font-size: var(--font-size-lg);
  letter-spacing: 2rpx;
}

.plate-card--compact .plate-card__reading {
  margin-top: 4rpx;
  font-size: var(--font-size-xs);
}

.plate-card--compact .plate-card__definition {
  margin-top: 6rpx;
  font-size: var(--font-size-xs);
  -webkit-line-clamp: 1;
}

/* 紧凑形态下省略来源行，点按进详情页再看依据 */
.plate-card--compact .plate-card__source {
  display: none;
}

/* 紧凑形态保留操作条：按钮字号/内边距比主铭牌小一档，避免副铭牌堆高挤压播放舞台 */
.plate-card--compact .plate-card__action {
  padding: 12rpx 8rpx;
  font-size: 19rpx;
}
</style>
