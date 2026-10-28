<script setup>
import { ICONS } from "./icons";

defineProps({
  text: { type: String, default: "暂无内容" },
  sub: { type: String, default: "" },
});
</script>

<template>
  <div class="empty">
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path v-for="d in ICONS.empty" :key="d" :d="d" />
    </svg>
    <p class="empty-text">{{ text }}</p>
    <p v-if="sub" class="empty-sub">{{ sub }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty-text {
  color: var(--text-2);
  font-size: 1rem;
  font-weight: 500;
}

.empty-sub {
  max-width: 28em;
  color: var(--text-3);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.empty :deep(.btn) {
  margin-top: 6px;
}
</style>
