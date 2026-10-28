<script setup>
import { onBeforeUnmount, onMounted, watch } from "vue";
import { ICONS } from "./icons";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

let previousOverflow = "";

function close() {
  emit("update:modelValue", false);
}

function onKeydown(event) {
  if (event.key === "Escape" && props.modelValue) close();
}

watch(
  () => props.modelValue,
  (open) => {
    if (typeof document === "undefined") return;
    if (open) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = previousOverflow;
    }
  },
  { immediate: true }
);

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = previousOverflow;
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="props.modelValue"
        class="modal-mask"
        @click.self="close"
      >
        <section
          class="modal-sheet"
          role="dialog"
          aria-modal="true"
          :aria-label="props.title || '弹窗'"
        >
          <header class="modal-header">
            <h2 class="modal-title">{{ props.title }}</h2>
            <button
              type="button"
              class="modal-close"
              aria-label="关闭"
              @click="close"
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
                <path v-for="d in ICONS.close" :key="d" :d="d" />
              </svg>
            </button>
          </header>

          <div class="modal-body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: var(--overlay);
}

.modal-sheet {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: var(--page-max);
  max-height: 82vh;
  max-height: 82dvh;
  overflow: hidden;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: var(--card);
  border-radius: 20px 20px 0 0;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--text);
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-close {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.modal-close svg {
  width: 21px;
  height: 21px;
}

.modal-close:active {
  background: var(--primary-soft);
}

.modal-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.modal-footer {
  display: flex;
  flex: none;
  gap: 10px;
  padding: 12px 20px calc(16px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border);
}

.modal-footer :deep(.btn) {
  flex: 1;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}

.modal-enter-active .modal-sheet,
.modal-leave-active .modal-sheet {
  transition: transform 0.26s var(--ease);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-sheet,
.modal-leave-to .modal-sheet {
  transform: translateY(100%);
}
</style>
