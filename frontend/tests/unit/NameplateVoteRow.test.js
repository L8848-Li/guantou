import { mount } from '@vue/test-utils';
import {
  afterEach, beforeEach, describe, expect, it, vi,
} from 'vitest';

vi.mock('@/services/guantou', () => ({
  supportNameplate: vi.fn(),
  unsupportNameplate: vi.fn(),
}));

vi.mock('@/services/authGuard', () => ({
  requireAuth: vi.fn(() => true),
}));

vi.mock('@/services/commentSheet', () => ({
  openCommentSheet: vi.fn(),
}));

import NameplateVoteRow from '@/components/home/NameplateVoteRow.vue';
import { supportNameplate, unsupportNameplate } from '@/services/guantou';
import { requireAuth } from '@/services/authGuard';
import { openCommentSheet } from '@/services/commentSheet';

function setupUni(token = 'token-value') {
  globalThis.uni = {
    getStorageSync: vi.fn((key) => (key === 'token' ? token : '')),
    setStorageSync: vi.fn(),
    removeStorageSync: vi.fn(),
    navigateTo: vi.fn(),
    showToast: vi.fn(),
  };
  globalThis.getCurrentPages = vi.fn(() => []);
}

function mountRow(overrides = {}, extraProps = {}) {
  return mount(NameplateVoteRow, {
    props: {
      nameplate: {
        id: 7,
        display_text: '巴适',
        definition: '舒服',
        support_count: 3,
        supported_by_current_user: false,
        ...overrides,
      },
      ...extraProps,
    },
  });
}

describe('NameplateVoteRow optimistic voting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupUni();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('supports optimistically, then adopts the server counts', async () => {
    let resolveSupport;
    supportNameplate.mockImplementation(
      () => new Promise((resolve) => {
        resolveSupport = resolve;
      }),
    );
    const wrapper = mountRow();

    await wrapper.find('.vote-row__support').trigger('tap');

    // 乐观更新：请求返回前本地票数已经 +1
    expect(wrapper.vm.supportCount).toBe(4);
    expect(wrapper.vm.supported).toBe(true);
    expect(wrapper.text()).toContain('已支持');

    resolveSupport({ support_count: 10, supported_by_current_user: true });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(supportNameplate).toHaveBeenCalledWith(7);
    expect(wrapper.vm.supportCount).toBe(10);
    expect(wrapper.emitted('support')).toBeTruthy();
  });

  it('rolls back when the support request fails', async () => {
    supportNameplate.mockRejectedValue(new Error('boom'));
    const wrapper = mountRow();

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.supported).toBe(false);
    expect(wrapper.vm.supportCount).toBe(3);
    expect(wrapper.emitted('support')).toBeFalsy();
  });

  it('clears the burst feedback when the support request fails', async () => {
    vi.useFakeTimers();
    supportNameplate.mockRejectedValue(new Error('boom'));
    const wrapper = mountRow();

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    // 失败回滚：乐观态撤销的同时撤除爆发反馈类名与定时器
    expect(wrapper.vm.supported).toBe(false);
    expect(wrapper.vm.supportBurst).toBe(false);
    expect(wrapper.find('.vote-row__support').classes())
      .not.toContain('vote-row__support--burst');

    // 撤除定时器已清理：时间推进后不会残留状态变化副作用（无异常即可）
    vi.advanceTimersByTime(800);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(false);
  });

  it('unsupports with an optimistic decrement', async () => {
    unsupportNameplate.mockResolvedValue({});
    const wrapper = mountRow({ supported_by_current_user: true, support_count: 6 });

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(unsupportNameplate).toHaveBeenCalledWith(7);
    expect(wrapper.vm.supported).toBe(false);
    expect(wrapper.vm.supportCount).toBe(5);
    expect(wrapper.emitted('unsupport')).toBeTruthy();
  });

  it('plays the one-shot burst feedback when a support lands, then clears it', async () => {
    vi.useFakeTimers();
    supportNameplate.mockResolvedValue({ support_count: 4, supported_by_current_user: true });
    const wrapper = mountRow();

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.supportBurst).toBe(true);
    expect(wrapper.find('.vote-row__support').classes()).toContain('vote-row__support--burst');

    // 动画结束后撤除类名：不循环，可再次触发；撤销支持不播放
    vi.advanceTimersByTime(800);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(false);

    unsupportNameplate.mockResolvedValue({});
    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(false);
  });

  it('restarts the burst on a quick support → unsupport → support sequence', async () => {
    vi.useFakeTimers();
    supportNameplate.mockResolvedValue({ support_count: 4, supported_by_current_user: true });
    unsupportNameplate.mockResolvedValue({});
    const wrapper = mountRow();

    // 第一次支持：爆发反馈置位，仍在撤除窗口内
    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(true);
    vi.advanceTimersByTime(100);

    // 撤销支持：立即清除残留爆发态与撤除定时器，不留窗口
    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(false);
    expect(wrapper.find('.vote-row__support').classes())
      .not.toContain('vote-row__support--burst');

    // 再次支持：类名先移除后重新附加，第二次动画必然重启
    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(true);
    expect(wrapper.find('.vote-row__support').classes())
      .toContain('vote-row__support--burst');

    // 新的撤除定时器生效：窗口结束后再次自动清除类名（不循环）
    vi.advanceTimersByTime(800);
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.supportBurst).toBe(false);
  });

  it('keeps a busy lock to avoid double voting', async () => {
    let resolveSupport;
    supportNameplate.mockImplementation(
      () => new Promise((resolve) => {
        resolveSupport = resolve;
      }),
    );
    const wrapper = mountRow();

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.find('.vote-row__support').trigger('tap');

    expect(supportNameplate).toHaveBeenCalledTimes(1);
    resolveSupport({ support_count: 4, supported_by_current_user: true });
    await wrapper.vm.$nextTick();
  });

  it('passes canId into the auth journey context when support requires login', async () => {
    requireAuth.mockReturnValue(true);
    supportNameplate.mockResolvedValue({});
    const wrapper = mountRow({}, { canId: 33 });

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();

    expect(requireAuth).toHaveBeenCalledWith('nameplate_support', {
      nameplateId: 7,
      canId: 33,
    });
    expect(supportNameplate).toHaveBeenCalledWith(7);
  });

  it('stops when the auth guard intercepts (guest support)', async () => {
    requireAuth.mockReturnValue(false);
    const wrapper = mountRow({}, { canId: 33 });

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();

    expect(requireAuth).toHaveBeenCalledWith('nameplate_support', {
      nameplateId: 7,
      canId: 33,
    });
    expect(supportNameplate).not.toHaveBeenCalled();
    expect(wrapper.vm.supported).toBe(false);
    expect(wrapper.vm.supportCount).toBe(3);
  });

  it('renders the full action bar in compact form and keeps voting wired', async () => {
    requireAuth.mockReturnValue(true);
    supportNameplate.mockResolvedValue({});
    const wrapper = mountRow({}, { compact: true, canId: 33 });

    /* Issue #218：副铭牌紧凑形态保留操作条，三按钮与主铭牌同构可用 */
    expect(wrapper.find('.plate-card__actions').exists()).toBe(true);
    expect(wrapper.find('.vote-row__support').text()).toContain('支持 3');
    expect(wrapper.find('.plate-card__comment').text()).toContain('评论 0');
    expect(wrapper.find('.plate-card__action--debate').text()).toBe('立论');

    await wrapper.find('.vote-row__support').trigger('tap');
    await wrapper.vm.$nextTick();

    expect(requireAuth).toHaveBeenCalledWith('nameplate_support', {
      nameplateId: 7,
      canId: 33,
    });
    expect(supportNameplate).toHaveBeenCalledWith(7);
    expect(wrapper.vm.supportCount).toBe(4);
  });

  it('routes the body and debate, and opens the comment sheet for comments', async () => {
    requireAuth.mockReturnValue(true);
    const wrapper = mountRow({}, { canId: 33 });

    await wrapper.find('.plate-card__body').trigger('tap');
    await wrapper.find('.plate-card__comment').trigger('tap');
    await wrapper.find('.plate-card__action--debate').trigger('tap');

    expect(uni.navigateTo).toHaveBeenNthCalledWith(1, {
      url: '/pages/nameplates/details?id=7',
    });
    // 评论改为半屏浮层（见 #219），不再整页跳转。
    expect(openCommentSheet).toHaveBeenCalledWith({
      targetType: 'nameplate',
      targetId: 7,
      theme: 'immersive',
    });
    expect(uni.navigateTo).toHaveBeenNthCalledWith(2, {
      url: '/pages/nameplates/create?can_id=33&reference_id=7',
    });
  });
});
