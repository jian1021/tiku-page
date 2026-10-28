import { computed, reactive } from "vue";

/**
 * 极简全局提示。
 * 用法：
 *   import { showToast } from "@/composables/useToast";
 *   showToast("已保存", "success");
 */
export const toastState = reactive({
  message: "",
  type: "info",
  visible: false,
});

// 兼容常用命名：既可直接读取 toastState，也可读取 toast
export const toast = toastState;
export const toastMessage = computed(() => toastState.message);
export const toastType = computed(() => toastState.type);
export const toastVisible = computed(() => toastState.visible);

// 简写导出，兼容直接使用 message / useToast 的写法
export const message = toastMessage;
export const type = toastType;
export const visible = toastVisible;

let timer = null;

const TYPES = ["info", "success", "error", "warning"];

export function hideToast() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  toastState.visible = false;
}

/**
 * 显示提示。
 * @param {string} text 提示文案
 * @param {"info"|"success"|"error"|"warning"} type 类型
 * @param {number} duration 持续时间（毫秒）
 */
export function showToast(text, type = "info", duration = 2200) {
  if (!text) return;

  if (timer) {
    clearTimeout(timer);
    timer = null;
  }

  toastState.message = String(text);
  toastState.type = TYPES.includes(type) ? type : "info";
  toastState.visible = true;

  const wait = Number(duration);
  if (Number.isFinite(wait) && wait > 0) {
    timer = setTimeout(() => {
      toastState.visible = false;
      timer = null;
    }, wait);
  }
}

export function useToast() {
  return {
    toast: toastState,
    toastMessage,
    toastType,
    toastVisible,
    showToast,
    hideToast,
  };
}
