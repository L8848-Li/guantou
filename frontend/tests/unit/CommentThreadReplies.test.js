import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/services/authGuard', () => ({
  requireAuth: vi.fn(() => true),
}));
vi.mock('@/services/canSocial', () => ({
  createCanComment: vi.fn(),
  createNameplateComment: vi.fn(),
  deleteCanComment: vi.fn(),
  likeCanComment: vi.fn(),
  listCanComments: vi.fn(),
  listNameplateComments: vi.fn(),
  unlikeCanComment: vi.fn(),
}));

import CommentThread from '@/components/CommentThread.vue';
import { requireAuth } from '@/services/authGuard';
import {
  createCanComment,
  deleteCanComment,
  likeCanComment,
  listCanComments,
} from '@/services/canSocial';

function setupUni(storage = {}) {
  globalThis.uni = {
    getStorageSync: vi.fn(
      (key) => (Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : ''),
    ),
    showToast: vi.fn(),
  };
}

function authorFixture(id = 99) {
  return { id, nickname: `用户${id}`, username: `user${id}`, avatar: '' };
}

function rootFixture(overrides = {}) {
  return {
    id: 101,
    can_id: 5,
    nameplate_id: null,
    parent_id: null,
    author: authorFixture(1),
    content: '一级评论',
    like_count: 1,
    liked_by_me: false,
    reply_count: 2,
    reply_to_nickname: '',
    created_at: '2026-08-27T10:00:00',
    ...overrides,
  };
}

function replyFixture(overrides = {}) {
  return {
    id: 202,
    can_id: 5,
    nameplate_id: null,
    parent_id: 101,
    author: authorFixture(2),
    content: '回复内容',
    like_count: 0,
    liked_by_me: false,
    reply_count: 0,
    reply_to_nickname: '',
    created_at: '2026-08-27T10:05:00',
    ...overrides,
  };
}

function mountThread(props = {}) {
  return mount(CommentThread, {
    props: { targetType: 'can', targetId: 5, ...props },
  });
}

describe('CommentThread 二重回复层级（issue #219）', () => {
  beforeEach(() => {
    setupUni();
    requireAuth.mockReturnValue(true);
    listCanComments.mockImplementation((canId, params = {}) => {
      if (params.parent_id) {
        return Promise.resolve({ results: [replyFixture()], next: null });
      }
      return Promise.resolve({ results: [rootFixture()], next: null });
    });
  });

  it('lists top-level comments and expands replies via parent_id', async () => {
    const wrapper = mountThread();
    await flushPromises();

    expect(wrapper.text()).toContain('一级评论');
    expect(wrapper.find('.comment-row__replies-toggle').text()).toContain('查看 2 条回复');

    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await flushPromises();

    expect(listCanComments).toHaveBeenCalledWith(5, { page: 1, parent_id: 101 });
    expect(wrapper.text()).toContain('回复内容');
    expect(wrapper.find('.comment-row__replies-toggle').text()).toBe('收起回复');
  });

  it('collapses replies without refetching when toggled again', async () => {
    const wrapper = mountThread();
    await flushPromises();

    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await flushPromises();
    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await flushPromises();

    const replyFetches = listCanComments.mock.calls.filter(
      ([, params]) => params && params.parent_id,
    );
    expect(replyFetches).toHaveLength(1);
  });

  it('submits a reply with parent_id and inserts it into the expanded thread', async () => {
    createCanComment.mockResolvedValue(replyFixture({ id: 303, content: '新回复' }));
    const wrapper = mountThread();
    await flushPromises();

    wrapper.vm.startReply(rootFixture());
    wrapper.vm.draft = '新回复';
    await wrapper.vm.submit();
    await flushPromises();

    expect(createCanComment).toHaveBeenCalledWith(5, '新回复', 101);
    expect(wrapper.vm.replyThreads[101].open).toBe(true);
    expect(wrapper.vm.replyThreads[101].items.map((item) => item.id)).toContain(303);
    expect(wrapper.vm.comments[0].reply_count).toBe(3);
  });

  it('flattens a reply to a reply back to the root thread', async () => {
    createCanComment.mockResolvedValue(
      replyFixture({ id: 404, content: '对回复的回复', reply_to_nickname: '用户2' }),
    );
    const wrapper = mountThread();
    await flushPromises();

    /* 直接对一条回复发起回复：前端只传直接目标，服务端收敛到一级 */
    wrapper.vm.startReply(replyFixture());
    wrapper.vm.draft = '对回复的回复';
    await wrapper.vm.submit();
    await flushPromises();

    expect(createCanComment).toHaveBeenCalledWith(5, '对回复的回复', 101);
    expect(wrapper.vm.replyThreads[101].items.map((item) => item.id)).toContain(404);
  });

  it('blocks guest reply publishing via the auth guard', async () => {
    requireAuth.mockReturnValue(false);
    const wrapper = mountThread();
    await flushPromises();

    wrapper.vm.startReply(rootFixture());
    wrapper.vm.draft = '游客的回复';
    await wrapper.vm.submit();

    expect(requireAuth).toHaveBeenCalledWith('comment', { page: 'can_comments', canId: 5 });
    expect(createCanComment).not.toHaveBeenCalled();
  });

  it('updates like state inside nested replies', async () => {
    likeCanComment.mockResolvedValue({ liked: true, like_count: 7 });
    const wrapper = mountThread();
    await flushPromises();

    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await flushPromises();

    await wrapper.vm.toggleLike(replyFixture());

    expect(wrapper.vm.replyThreads[101].items[0].liked_by_me).toBe(true);
    expect(wrapper.vm.replyThreads[101].items[0].like_count).toBe(7);
  });

  it('removes a reply and decrements the root reply_count', async () => {
    deleteCanComment.mockResolvedValue({});
    const wrapper = mountThread();
    await flushPromises();

    await wrapper.find('.comment-row__replies-toggle').trigger('tap');
    await flushPromises();
    await wrapper.vm.remove(replyFixture());

    expect(deleteCanComment).toHaveBeenCalledWith(202);
    expect(wrapper.vm.replyThreads[101].items).toHaveLength(0);
    expect(wrapper.vm.comments[0].reply_count).toBe(1);
  });

  it('renders the sheet variant with a bottom composer bar', async () => {
    const wrapper = mountThread({ variant: 'sheet' });
    await flushPromises();

    expect(wrapper.classes()).toContain('comment-thread--sheet');
    expect(wrapper.find('.comment-thread__composer-bar').exists()).toBe(true);
    expect(wrapper.find('.comment-thread__rule').exists()).toBe(false);
  });
});
