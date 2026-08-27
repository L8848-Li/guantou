import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import CommentSheet from '@/components/comments/CommentSheet.vue';

function mountSheet(props = {}) {
  return mount(CommentSheet, {
    props: {
      modelValue: false,
      targetType: 'can',
      targetId: 5,
      title: '评论 2',
      ...props,
    },
    global: {
      stubs: {
        CommentThread: {
          props: ['variant', 'targetType', 'targetId'],
          template: '<div class="thread-stub" />',
        },
      },
    },
  });
}

describe('CommentSheet 半屏评论面板（issue #219）', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing while closed and slides open when activated', async () => {
    const wrapper = mountSheet();
    expect(wrapper.find('.comment-sheet').exists()).toBe(false);

    await wrapper.setProps({ modelValue: true });
    await wrapper.vm.$nextTick();

    /* 面板先以收起态挂载，入场延迟后才加开启类，保证过渡生效 */
    expect(wrapper.find('.comment-sheet').exists()).toBe(true);
    expect(wrapper.find('.comment-sheet__panel--open').exists()).toBe(false);

    vi.advanceTimersByTime(50);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.comment-sheet__panel--open').exists()).toBe(true);
    expect(wrapper.find('.comment-sheet__mask--visible').exists()).toBe(true);
    expect(wrapper.find('.thread-stub').exists()).toBe(true);
    expect(wrapper.find('.comment-sheet__title').text()).toBe('评论 2');
  });

  it('closes via mask tap and unmounts after the exit transition', async () => {
    const wrapper = mountSheet({ modelValue: true });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    await wrapper.find('.comment-sheet__mask').trigger('tap');

    expect(wrapper.emitted('update:modelValue')).toBeTruthy();
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe(false);

    await wrapper.setProps({ modelValue: false });
    expect(wrapper.find('.comment-sheet').exists()).toBe(true);
    vi.advanceTimersByTime(400);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.comment-sheet').exists()).toBe(false);
  });

  it('closes via the header close button', async () => {
    const wrapper = mountSheet({ modelValue: true });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    await wrapper.find('.comment-sheet__close').trigger('tap');

    expect(wrapper.emitted('update:modelValue')[0][0]).toBe(false);
  });

  it('expands on drag up and closes on drag down from half height', async () => {
    const wrapper = mountSheet({ modelValue: true });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    /* 上滑展开 */
    wrapper.vm.onDragStart({ touches: [{ clientY: 500 }] });
    wrapper.vm.onDragMove({ touches: [{ clientY: 380 }] });
    wrapper.vm.onDragEnd();
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.comment-sheet__panel--expanded').exists()).toBe(true);

    /* 展开态下滑先收回半屏 */
    wrapper.vm.onDragStart({ touches: [{ clientY: 300 }] });
    wrapper.vm.onDragMove({ touches: [{ clientY: 420 }] });
    wrapper.vm.onDragEnd();
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.comment-sheet__panel--expanded').exists()).toBe(false);

    /* 半屏态下滑关闭 */
    wrapper.vm.onDragStart({ touches: [{ clientY: 300 }] });
    wrapper.vm.onDragMove({ touches: [{ clientY: 420 }] });
    wrapper.vm.onDragEnd();
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe(false);
  });

  it('supports the default theme for non-immersive pages', async () => {
    const wrapper = mountSheet({ modelValue: true, theme: 'default' });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.comment-sheet--default').exists()).toBe(true);
    expect(wrapper.find('.comment-sheet--immersive').exists()).toBe(false);
  });
});
