<script setup>
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, default: 0 },
});

const clamped = computed(() => {
  const value = Number(props.value);
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(0, value));
});
</script>

<template>
  <div
    class="progress"
    role="progressbar"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-valuenow="Math.round(clamped)"
  >
    <div class="progress-bar" :style="{ width: `${clamped}%` }"></div>
  </div>
</template>
