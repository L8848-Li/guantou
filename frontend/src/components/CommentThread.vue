<template>
  <view
    class="comment-thread"
    :class="{ 'comment-thread--sheet': isSheet }"
  >
    <view class="comment-thread__composer">
      <view
        v-if="replyTarget"
        class="comment-thread__reply-hint"
      >
        <text class="comment-thread__reply-hint-text">
          回复 @{{ replyTargetName }}
        </text>
        <text
          class="comment-thread__reply-hint-cancel"
          role="button"
          aria-label="取消回复"
          @tap="cancelReply"
        >
          ✕
        </text>
      </view>

      <!-- 半屏面板形态：底部单行输入条 -->
      <view
        v-if="isSheet"
        class="comment-thread__composer-bar"
      >
        <input
          v-model="draft"
          class="comment-thread__input"
          :maxlength="500"
          placeholder="友好讨论，说说你的看法……"
          confirm-type="send"
          @confirm="submit"
        >
        <view
          class="comment-thread__send"
          :class="{ 'comment-thread__send--busy': submitting }"
          role="button"
          aria-label="发送评论"
          @tap="submit"
        >
          {{ submitting ? '发送中' : '发送' }}
        </view>
      </view>

      <!-- 整页形态：顶部多行输入区（保持既有布局） -->
      <template v-else>
        <BaseField
          v-model="draft"
          name="comment"
          type="textarea"
          :maxlength="500"
          placeholder="说说你的依据、读法或补充……"
          indicator
          autosize
        />
        <BaseButton
          block
          text="发表评论"
          :loading="submitting"
          @click="submit"
        />
      </template>
    </view>

    <view class="comment-thread__scroll">
      <view
        v-if="!isSheet"
        class="comment-thread__rule"
      >
        讨论观点，也尊重每一种真实使用。
      </view>

      <BaseLoading
        v-if="loading && !comments.length"
        text="正在翻阅评论"
      />
      <view
        v-else-if="errorMessage && !comments.length"
        class="comment-thread__error"
      >
        <text class="comment-thread__error-text">
          {{ errorMessage }}
        </text>
        <BaseButton
          class="comment-thread__retry"
          variant="ghost"
          size="small"
          text="重试"
          @click="retry"
        />
      </view>
      <EmptyState
        v-else-if="!comments.length"
        :title="isSheet ? '还没有评论' : '还没有评论，来留下第一条依据'"
      />
      <view v-else>
        <view
          v-for="comment in comments"
          :key="comment.id"
          class="comment-row"
        >
          <image
            v-if="comment.author.avatar"
            class="comment-row__avatar"
            :src="comment.author.avatar"
            mode="aspectFill"
          />
          <view
            v-else
            class="comment-row__avatar comment-row__avatar--empty"
          />
          <view class="comment-row__body">
            <view class="comment-row__head">
              <text class="comment-row__author">
                {{ comment.author.nickname || comment.author.username }}
              </text>
              <text class="comment-row__time">
                {{ formatTime(comment.created_at) }}
              </text>
            </view>
            <view class="comment-row__content">
              {{ comment.content }}
            </view>
            <view class="comment-row__actions">
              <text
                :class="{ 'comment-row__liked': comment.liked_by_me }"
                @tap="toggleLike(comment)"
              >
                {{ comment.liked_by_me ? '已赞' : '赞' }} {{ comment.like_count || 0 }}
              </text>
              <text @tap="startReply(comment)">
                回复
              </text>
              <text
                v-if="canDelete(comment)"
                @tap="remove(comment)"
              >
                删除
              </text>
            </view>

            <!-- 二重层级：回复折叠区 -->
            <view
              v-if="Number(comment.reply_count || 0) > 0 || thread(comment.id).items.length"
              class="comment-row__replies"
            >
              <view
                class="comment-row__replies-toggle"
                role="button"
                @tap="toggleReplies(comment)"
              >
                {{ repliesToggleText(comment) }}
              </view>
              <template v-if="thread(comment.id).open">
                <view
                  v-for="reply in thread(comment.id).items"
                  :key="reply.id"
                  class="comment-row comment-row--reply"
                >
                  <image
                    v-if="reply.author.avatar"
                    class="comment-row__avatar comment-row__avatar--sm"
                    :src="reply.author.avatar"
                    mode="aspectFill"
                  />
                  <view
                    v-else
                    class="comment-row__avatar comment-row__avatar--sm comment-row__avatar--empty"
                  />
                  <view class="comment-row__body">
                    <view class="comment-row__head">
                      <text class="comment-row__author">
                        {{ reply.author.nickname || reply.author.username }}
                      </text>
                      <text class="comment-row__time">
                        {{ formatTime(reply.created_at) }}
                      </text>
                    </view>
                    <view class="comment-row__content">
                      {{ replyAt(reply) }}{{ reply.content }}
                    </view>
                    <view class="comment-row__actions">
                      <text
                        :class="{ 'comment-row__liked': reply.liked_by_me }"
                        @tap="toggleLike(reply)"
                      >
                        {{ reply.liked_by_me ? '已赞' : '赞' }} {{ reply.like_count || 0 }}
                      </text>
                      <text @tap="startReply(reply)">
                        回复
                      </text>
                      <text
                        v-if="canDelete(reply)"
                        @tap="remove(reply)"
                      >
                        删除
                      </text>
                    </view>
                  </view>
                </view>
                <view
                  v-if="thread(comment.id).hasMore && thread(comment.id).items.length"
                  class="comment-row__replies-more"
                  role="button"
                  @tap="loadReplies(comment)"
                >
                  {{ thread(comment.id).loading ? '加载中…' : '展开更多回复' }}
                </view>
              </template>
            </view>
          </view>
        </view>
        <BaseButton
          v-if="hasMore"
          block
          variant="ghost"
          text="加载更多"
          :loading="loading"
          @click="loadMore"
        />
      </view>
    </view>
  </view>
</template>

<script>
import BaseButton from '@/components/BaseButton.vue';
import BaseField from '@/components/BaseField.vue';
import BaseLoading from '@/components/BaseLoading.vue';
import EmptyState from '@/components/EmptyState.vue';
import {
  createCanComment,
  createNameplateComment,
  deleteCanComment,
  likeCanComment,
  listCanComments,
  listNameplateComments,
  unlikeCanComment,
} from '@/services/canSocial';
import { requireAuth } from '@/services/authGuard';

const EMPTY_THREAD = Object.freeze({
  open: false,
  loading: false,
  items: [],
  page: 0,
  hasMore: true,
});

export default {
  name: 'CommentThread',
  components: {
    BaseButton,
    BaseField,
    BaseLoading,
    EmptyState,
  },
  props: {
    targetType: {
      type: String,
      required: true,
      validator: (value) => ['can', 'nameplate'].includes(value),
    },
    targetId: {
      type: [Number, String],
      required: true,
    },
    /* page：整页评论（顶部输入区）；sheet：半屏面板内嵌（底部输入条） */
    variant: {
      type: String,
      default: 'page',
      validator: (value) => ['page', 'sheet'].includes(value),
    },
  },
  emits: ['created'],
  data() {
    return {
      draft: '',
      comments: [],
      replyThreads: {},
      replyTarget: null,
      page: 0,
      hasMore: true,
      loading: false,
      submitting: false,
      errorMessage: '',
    };
  },
  computed: {
    isSheet() {
      return this.variant === 'sheet';
    },
    replyTargetName() {
      const author = this.replyTarget && this.replyTarget.author;
      return (author && (author.nickname || author.username)) || '';
    },
  },
  mounted() {
    this.loadMore();
  },
  methods: {
    authContext() {
      return this.targetType === 'nameplate'
        ? { page: 'nameplate_comments', nameplateId: this.targetId }
        : { page: 'can_comments', canId: this.targetId };
    },
    thread(commentId) {
      return this.replyThreads[commentId] || EMPTY_THREAD;
    },
    repliesToggleText(comment) {
      const thread = this.thread(comment.id);
      if (thread.open) return '收起回复';
      const count = Number(comment.reply_count || thread.items.length);
      return `查看 ${count} 条回复`;
    },
    replyAt(reply) {
      return reply.reply_to_nickname ? `@${reply.reply_to_nickname} ` : '';
    },
    async loadMore() {
      if (this.loading || !this.hasMore) return;
      this.loading = true;
      this.errorMessage = '';
      try {
        const nextPage = this.page + 1;
        const response = this.targetType === 'nameplate'
          ? await listNameplateComments(this.targetId, { page: nextPage })
          : await listCanComments(this.targetId, { page: nextPage });
        const items = response.results || response || [];
        this.comments = this.comments.concat(items);
        this.page = nextPage;
        this.hasMore = Boolean(response.next);
      } catch (error) {
        this.errorMessage = error.message || '评论加载失败';
        uni.showToast({ title: error.message || '评论加载失败', icon: 'none' });
      } finally {
        this.loading = false;
      }
    },
    async retry() {
      await this.loadMore();
    },
    /* ---------- 二重回复 ---------- */
    toggleReplies(comment) {
      const existing = this.thread(comment.id);
      if (existing.items.length) {
        this.replyThreads[comment.id] = { ...existing, open: !existing.open };
        return;
      }
      this.loadReplies(comment);
    },
    async loadReplies(comment) {
      const existing = this.thread(comment.id);
      if (existing.loading) return;
      const nextPage = existing.page + 1;
      this.replyThreads[comment.id] = { ...existing, open: true, loading: true };
      try {
        const params = { page: nextPage, parent_id: comment.id };
        const response = this.targetType === 'nameplate'
          ? await listNameplateComments(this.targetId, params)
          : await listCanComments(this.targetId, params);
        const items = response.results || response || [];
        this.replyThreads[comment.id] = {
          open: true,
          loading: false,
          items: existing.items.concat(items),
          page: nextPage,
          hasMore: Boolean(response.next),
        };
      } catch (error) {
        this.replyThreads[comment.id] = { ...existing, loading: false };
        uni.showToast({ title: error.message || '回复加载失败', icon: 'none' });
      }
    },
    startReply(comment) {
      this.replyTarget = comment;
    },
    cancelReply() {
      this.replyTarget = null;
    },
    insertReply(comment) {
      const rootId = Number(comment.parent_id);
      const existing = this.thread(rootId);
      this.replyThreads[rootId] = {
        ...existing,
        open: true,
        items: [...existing.items, comment],
      };
      this.comments = this.comments.map((item) => (item.id === rootId
        ? { ...item, reply_count: Number(item.reply_count || 0) + 1 }
        : item));
    },
    patchComment(commentId, patch) {
      this.comments = this.comments.map((item) => (item.id === commentId
        ? { ...item, ...patch }
        : item));
      const rootId = Object.keys(this.replyThreads).find(
        (key) => this.replyThreads[key].items.some((item) => item.id === commentId),
      );
      if (rootId) {
        const existing = this.replyThreads[rootId];
        this.replyThreads[rootId] = {
          ...existing,
          items: existing.items.map((item) => (item.id === commentId
            ? { ...item, ...patch }
            : item)),
        };
      }
    },
    /* ---------- 发布 / 点赞 / 删除 ---------- */
    async submit() {
      const content = String(this.draft || '').trim();
      if (!content) {
        uni.showToast({ title: '先写下评论', icon: 'none' });
        return;
      }
      const action = this.targetType === 'nameplate' ? 'nameplate_comment' : 'comment';
      if (!requireAuth(action, this.authContext())) return;
      this.submitting = true;
      /* 回复的回复由服务端收敛到一级；前端只传直接目标 */
      const parentId = this.replyTarget
        ? Number(this.replyTarget.parent_id) || this.replyTarget.id
        : null;
      try {
        const comment = this.targetType === 'nameplate'
          ? await createNameplateComment(this.targetId, content, parentId)
          : await createCanComment(this.targetId, content, parentId);
        if (this.replyTarget) {
          this.insertReply(comment);
        } else {
          this.comments = [comment, ...this.comments];
        }
        this.draft = '';
        this.replyTarget = null;
        this.$emit('created', comment);
      } finally {
        this.submitting = false;
      }
    },
    async toggleLike(comment) {
      const action = this.targetType === 'nameplate' ? 'nameplate_comment' : 'comment_like';
      if (!requireAuth(action, this.authContext())) return;
      const result = comment.liked_by_me
        ? await unlikeCanComment(comment.id)
        : await likeCanComment(comment.id);
      this.patchComment(comment.id, {
        liked_by_me: result.liked,
        like_count: result.like_count,
      });
    },
    async remove(comment) {
      await deleteCanComment(comment.id);
      if (comment.parent_id) {
        const rootId = Number(comment.parent_id);
        const existing = this.replyThreads[rootId];
        if (existing.items.length) {
          this.replyThreads[rootId] = {
            ...existing,
            items: existing.items.filter((item) => item.id !== comment.id),
          };
        }
        this.comments = this.comments.map((item) => (item.id === rootId
          ? { ...item, reply_count: Math.max(0, Number(item.reply_count || 0) - 1) }
          : item));
      } else {
        this.comments = this.comments.filter((item) => item.id !== comment.id);
      }
    },
    canDelete(comment) {
      return Number(comment.author?.id) === Number(uni.getStorageSync('id'));
    },
    formatTime(value) {
      return String(value || '').replace('T', ' ').slice(0, 16);
    },
  },
};
</script>

<style scoped>
.comment-thread__composer {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  padding: 24rpx;
  border: 1rpx solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--surface-color);
}

.comment-thread__rule {
  padding: 28rpx 4rpx 14rpx;
  color: var(--muted-color);
  font-size: 22rpx;
  letter-spacing: 1rpx;
}

.comment-thread__error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1rpx solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
}

.comment-thread__error-text {
  min-width: 0;
  flex: 1;
  color: var(--danger-color);
  font-size: var(--font-size-sm);
}

.comment-thread__retry {
  flex: 0 0 auto;
  margin: 0;
}

.comment-row {
  display: flex;
  gap: 18rpx;
  padding: 26rpx 0;
  border-bottom: 1rpx solid var(--border-color);
}

.comment-row__avatar {
  width: 58rpx;
  height: 58rpx;
  border-radius: 50%;
  background: var(--surface-subtle-color);
}

.comment-row__avatar--sm {
  width: 46rpx;
  height: 46rpx;
}

.comment-row__body {
  min-width: 0;
  flex: 1;
}

.comment-row__head,
.comment-row__actions {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
}

.comment-row__author {
  color: var(--text-color);
  font-size: 24rpx;
  font-weight: 800;
}

.comment-row__time,
.comment-row__actions {
  color: var(--muted-color);
  font-size: 20rpx;
}

.comment-row__content {
  margin-top: 10rpx;
  color: var(--text-color);
  font-size: 27rpx;
  line-height: 1.6;
  white-space: pre-wrap;
}

.comment-row__actions {
  justify-content: flex-start;
  margin-top: 14rpx;
}

.comment-row__liked {
  color: var(--accent-color);
  font-weight: 800;
}

/* ---------- 二重回复折叠区 ---------- */
.comment-row__replies {
  margin-top: 16rpx;
  padding-left: 8rpx;
}

.comment-row__replies-toggle,
.comment-row__replies-more {
  color: var(--accent-color);
  font-size: 22rpx;
  font-weight: 700;
  padding: 6rpx 0;
}

.comment-row--reply {
  padding: 18rpx 0;
  border-bottom: 0;
}

/* ---------- 半屏面板形态（CommentSheet 内嵌） ----------
 * 颜色经 CommentSheet 注入的 --ct-* 变量适配沉浸/常规两套主题，
 * 未注入时回落到常规主题 token。 */
.comment-thread--sheet {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.comment-thread--sheet .comment-thread__composer {
  order: 2;
  flex: 0 0 auto;
  gap: 12rpx;
  margin: 0;
  padding: 16rpx 24rpx calc(16rpx + env(safe-area-inset-bottom));
  border: 0;
  border-top: 1rpx solid var(--ct-border, var(--border-color));
  border-radius: 0;
  background: transparent;
}

.comment-thread--sheet .comment-thread__scroll {
  order: 1;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 24rpx;
  -webkit-overflow-scrolling: touch;
}

.comment-thread__reply-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  padding: 8rpx 4rpx 0;
}

.comment-thread__reply-hint-text {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ct-accent, var(--accent-color));
  font-size: 22rpx;
}

.comment-thread__reply-hint-cancel {
  flex: 0 0 auto;
  color: var(--ct-muted, var(--muted-color));
  font-size: 24rpx;
  padding: 4rpx 12rpx;
}

.comment-thread__composer-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.comment-thread__input {
  flex: 1;
  min-width: 0;
  height: 68rpx;
  padding: 0 24rpx;
  border-radius: var(--radius-pill);
  border: 1rpx solid var(--ct-border, var(--border-color));
  background: var(--ct-surface, var(--surface-subtle-color));
  color: var(--ct-text, var(--text-color));
  font-size: 26rpx;
}

.comment-thread__send {
  flex: 0 0 auto;
  padding: 14rpx 32rpx;
  border-radius: var(--radius-pill);
  background: var(--ct-accent, var(--accent-color));
  color: var(--ct-on-accent, var(--on-accent-color));
  font-size: 26rpx;
  font-weight: 800;
}

.comment-thread__send--busy {
  opacity: 0.6;
}

/* sheet 内列表与回复的配色跟随面板主题 */
.comment-thread--sheet .comment-row {
  border-bottom-color: var(--ct-border, var(--border-color));
}

.comment-thread--sheet .comment-row__author,
.comment-thread--sheet .comment-row__content {
  color: var(--ct-text, var(--text-color));
}

.comment-thread--sheet .comment-row__time,
.comment-thread--sheet .comment-row__actions {
  color: var(--ct-muted, var(--muted-color));
}

.comment-thread--sheet .comment-row__liked,
.comment-thread--sheet .comment-row__replies-toggle,
.comment-thread--sheet .comment-row__replies-more {
  color: var(--ct-accent, var(--accent-color));
}

.comment-thread--sheet .comment-row__avatar {
  background: var(--ct-surface, var(--surface-subtle-color));
}

.comment-thread--sheet .comment-thread__error {
  border-color: var(--ct-border, var(--border-color));
  background: var(--ct-surface, var(--surface-color));
}
</style>
