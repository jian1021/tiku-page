<script setup>
import { useRouter } from "vue-router";
import { ICONS } from "./icons";

const props = defineProps({
  title: { type: String, default: "" },
  back: { type: Boolean, default: true },
  rightText: { type: String, default: "" },
});

const emit = defineEmits(["right"]);

const router = useRouter();

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/");
  }
}
</script>

<template>
  <header class="topbar">
    <button
      v-if="props.back"
      type="button"
      class="topbar-btn"
      aria-label="返回"
      @click="goBack"
    >
      <svg
        class="topbar-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path v-for="d in ICONS.back" :key="d" :d="d" />
      </svg>
    </button>
    <span v-else class="topbar-placeholder" aria-hidden="true"></span>

    <h1 class="topbar-title">{{ props.title }}</h1>

    <button
      v-if="props.rightText"
      type="button"
      class="topbar-btn topbar-right"
      @click="emit('right')"
    >
      {{ props.rightText }}
    </button>
    <span v-else class="topbar-placeholder" aria-hidden="true"></span>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: calc(var(--topbar-height) + env(safe-area-inset-top, 0px));
  margin: -16px -16px 16px;
  padding: env(safe-area-inset-top, 0px) 4px 0;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.topbar-btn {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text);
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.topbar-btn:active {
  background: var(--primary-soft);
}

.topbar-icon {
  width: 22px;
  height: 22px;
}

.topbar-right {
  padding: 0 8px;
  border-radius: var(--radius-sm);
  color: var(--primary);
  white-space: nowrap;
}

.topbar-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--text);
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.4;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-placeholder {
  flex: none;
  width: 44px;
  height: 44px;
}
</style>
