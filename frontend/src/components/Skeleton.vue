<script setup>
defineProps({
  rows: { type: Number, default: 3 },
});
</script>

<template>
  <div class="skeleton-list" role="status" aria-label="加载中" aria-busy="true">
    <div
      v-for="row in Math.max(1, Number(rows) || 1)"
      :key="row"
      class="card skeleton-card"
      aria-hidden="true"
    >
      <div class="skeleton skeleton-title"></div>
      <div class="skeleton skeleton-line"></div>
      <div class="skeleton skeleton-line"></div>
      <div class="skeleton skeleton-line skeleton-line-short"></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-card {
  padding: 16px;
}

.skeleton-card + .skeleton-card {
  margin-top: 12px;
}

.skeleton-title {
  width: 45%;
  height: 18px;
  margin-bottom: 4px;
}

.skeleton-line {
  width: 100%;
  height: 14px;
}

.skeleton-line-short {
  width: 62%;
}
</style>
