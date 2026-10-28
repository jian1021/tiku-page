<script setup>
import { computed } from "vue";
import { toastState } from "../composables/useToast";
import { ICONS } from "./icons";

const iconPaths = computed(() => {
  const map = {
    success: ICONS.check,
    error: ICONS.close,
    warning: ICONS.warning,
    info: ICONS.info,
  };
  return map[toastState.type] || ICONS.info;
});
</script>

<template>
  <Transition name="toast">
    <div
      v-if="toastState.visible"
      class="toast"
      :class="`toast-${toastState.type}`"
      role="status"
      aria-live="polite"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path v-for="d in iconPaths" :key="d" :d="d" />
      </svg>
      <span>{{ toastState.message }}</span>
    </div>
  </Transition>
</template>

<style scoped>
.toast {
  position: fixed;
  top: calc(16px + env(safe-area-inset-top, 0px));
  left: 50%;
  z-index: 4000;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: calc(100vw - 32px);
  min-height: 44px;
  padding: 10px 16px;
  transform: translateX(-50%);
  border-radius: var(--radius);
  background: var(--text);
  color: var(--bg);
  font-size: 0.95rem;
  line-height: 1.5;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  pointer-events: none;
}

.toast svg {
  flex: none;
  width: 20px;
  height: 20px;
}

.toast-success {
  background: var(--primary);
  color: var(--primary-contrast);
}

.toast-error {
  background: var(--danger);
  color: var(--card);
}

.toast-warning {
  background: var(--accent);
  color: var(--card);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s var(--ease);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}
</style>
