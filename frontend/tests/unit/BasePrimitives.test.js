import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import BaseButton from '@/components/BaseButton.vue';
import BaseField from '@/components/BaseField.vue';
import confirmDialog from '@/components/ConfirmDialog';

describe('BaseButton', () => {
  it('renders the primary variant with slot text by default', () => {
    const wrapper = mount(BaseButton, {
      slots: { default: '提交铭牌' },
    });

    expect(wrapper.classes()).toContain('base-button--primary');
    expect(wrapper.classes()).toContain('base-button--medium');
    expect(wrapper.text()).toContain('提交铭牌');
  });

  it('supports ghost and danger variants with block sizing', () => {
    const ghost = mount(BaseButton, {
      props: { variant: 'ghost', block: true },
    });
    expect(ghost.classes()).toContain('base-button--ghost');
    expect(ghost.classes()).toContain('base-button--block');

    const danger = mount(BaseButton, {
      props: { variant: 'danger', size: 'small', text: '删除' },
    });
    expect(danger.classes()).toContain('base-button--danger');
    expect(danger.classes()).toContain('base-button--small');
    expect(danger.text()).toContain('删除');
  });

  it('emits click on tap but not when disabled or loading', async () => {
    const wrapper = mount(BaseButton);
    await wrapper.trigger('tap');
    expect(wrapper.emitted('click')).toHaveLength(1);

    const disabled = mount(BaseButton, { props: { disabled: true } });
    await disabled.trigger('tap');
    expect(disabled.emitted('click')).toBeUndefined();

    const loading = mount(BaseButton, { props: { loading: true } });
    await loading.trigger('tap');
    expect(loading.emitted('click')).toBeUndefined();
  });
});

describe('BaseField', () => {
  it('renders label, required mark and error text', () => {
    const wrapper = mount(BaseField, {
      props: {
        label: '昵称',
        required: true,
        error: '昵称不能为空',
      },
    });

    expect(wrapper.find('.base-field-label').text()).toContain('昵称');
    expect(wrapper.find('.base-field-required').exists()).toBe(true);
    expect(wrapper.find('.base-field-error').text()).toBe('昵称不能为空');
    expect(wrapper.find('input').exists()).toBe(true);
  });

  it('uses textarea and emits v-model updates on input', async () => {
    const wrapper = mount(BaseField, {
      props: { type: 'textarea', modelValue: '' },
    });

    expect(wrapper.find('textarea').exists()).toBe(true);
    await wrapper.find('textarea').trigger('input', { detail: { value: '罐头释义' } });
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['罐头释义']);
    expect(wrapper.emitted('input')[0]).toEqual(['罐头释义']);
  });
});

describe('confirmDialog', () => {
  beforeEach(() => {
    globalThis.uni = { showModal: vi.fn() };
  });

  it('resolves true when the user confirms', async () => {
    uni.showModal.mockImplementation(({ success }) => success({ confirm: true }));
    await expect(confirmDialog({ title: '删除罐头？' })).resolves.toBe(true);
    expect(uni.showModal.mock.calls[0][0].title).toBe('删除罐头？');
    expect(uni.showModal.mock.calls[0][0].confirmColor).toBeUndefined();
  });

  it('resolves false when the user cancels or the modal fails', async () => {
    uni.showModal.mockImplementation(({ success }) => success({ confirm: false }));
    await expect(confirmDialog()).resolves.toBe(false);

    uni.showModal.mockImplementation(({ fail }) => fail(new Error('denied')));
    await expect(confirmDialog()).resolves.toBe(false);
  });

  it('applies the danger confirm color for destructive actions', async () => {
    uni.showModal.mockImplementation(({ success }) => success({ confirm: true }));
    await confirmDialog({ danger: true });
    expect(uni.showModal.mock.calls[0][0].confirmColor).toMatch(/^#[0-9a-f]{6}$/i);
  });
});
