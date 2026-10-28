<script setup>
import { useRoute } from "vue-router";
import { ICONS } from "./icons";

const route = useRoute();

const tabs = [
  { path: "/", label: "练习", icon: "book" },
  { path: "/exam", label: "考试", icon: "exam" },
  { path: "/service", label: "服务", icon: "service" },
  { path: "/me", label: "我的", icon: "user" },
];

function isActive(path) {
  if (path === "/") return route.path === "/";
  return route.path === path || route.path.startsWith(`${path}/`);
}
</script>

<template>
  <nav class="tabbar" aria-label="主导航">
    <router-link
      v-for="tab in tabs"
      :key="tab.path"
      :to="tab.path"
      class="tabbar-item"
      :class="{ active: isActive(tab.path) }"
      :aria-current="isActive(tab.path) ? 'page' : undefined"
    >
      <svg
        class="tabbar-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path v-for="d in ICONS[tab.icon]" :key="d" :d="d" />
      </svg>
      <span class="tabbar-label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.tabbar {
  position: fixed;
  left: 50%;
  bottom: 0;
  z-index: 100;
  display: flex;
  width: 100%;
  max-width: var(--page-max);
  height: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px));
  padding-bottom: env(safe-area-inset-bottom, 0px);
  transform: translateX(-50%);
  background: var(--card);
  border-top: 1px solid var(--border);
  box-shadow: 0 -2px 12px rgba(22, 35, 31, 0.04);
}

.tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: 56px;
  color: var(--text-2);
  text-decoration: none;
  -webkit-tap-highlight-color: transparent;
  transition: color 0.15s ease;
}

.tabbar-icon {
  width: 23px;
  height: 23px;
}

.tabbar-label {
  font-size: 0.72rem;
  font-weight: 500;
  line-height: 1.3;
}

.tabbar-item.active {
  color: var(--primary);
}

.tabbar-item.active .tabbar-icon {
  stroke-width: 2.1;
}

.tabbar-item:active {
  color: var(--primary);
}
</style>
