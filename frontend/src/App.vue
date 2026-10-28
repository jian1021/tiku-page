<script setup>
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import TabBar from "./components/TabBar.vue";
import Toast from "./components/Toast.vue";
import { useUiStore } from "./stores/ui";
import { useAuthStore } from "./stores/auth";

const route = useRoute();
const ui = useUiStore();
const auth = useAuthStore();

// 底部导航仅在四个主页面显示
const showTabBar = computed(() => route.meta?.tab === true);
const shellClass = computed(() => ({
  "theme-dark": ui.theme === "dark",
  [`font-${ui.fontSize}`]: true,
  "has-tab": showTabBar.value,
}));

onMounted(() => {
  ui.init();
  auth.init();
});
</script>

<template>
  <div id="app-shell" :class="shellClass">
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </main>

    <TabBar v-if="showTabBar" />
    <Toast />
  </div>
</template>

<style scoped>
.app-main {
  width: 100%;
  max-width: var(--page-max);
  margin: 0 auto;
}

/* 底部有导航时给内容留出安全距离 */
#app-shell.has-tab .app-main {
  padding-bottom: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px));
}
</style>
