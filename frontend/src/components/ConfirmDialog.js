/**
 * 确认弹窗原语（M1·设计系统）
 *
 * 统一封装 uni.showModal，供删除类等需要二次确认的操作复用，
 * 业务代码禁止再直接散落 uni.showModal 调用。
 *
 * 用法：
 *   import confirmDialog from '@/components/ConfirmDialog';
 *   const confirmed = await confirmDialog({
 *     title: '删除这个罐头？',
 *     content: '删除后无法恢复',
 *     danger: true,
 *   });
 *   if (confirmed) { ... }
 */

// uni.showModal 是原生 API，不支持 CSS 变量，
// 这里是 tokens.scss 中 --danger-color 浅色值的唯一例外引用。
const DANGER_CONFIRM_COLOR = '#d54941';

export default function confirmDialog(options = {}) {
  const {
    title = '请确认',
    content = '',
    confirmText = '确认',
    cancelText = '取消',
    danger = false,
  } = options;

  return new Promise((resolve) => {
    uni.showModal({
      title,
      content,
      confirmText,
      cancelText,
      confirmColor: danger ? DANGER_CONFIRM_COLOR : undefined,
      success: (result) => resolve(Boolean(result && result.confirm)),
      fail: () => resolve(false),
    });
  });
}
