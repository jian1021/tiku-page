import { createApp } from "vue";
import { createPinia } from "pinia";
import router from "./router";
import App from "./App.vue";
import { useUiStore } from "./stores/ui";

// 设计令牌与全局样式（必须早于页面组件样式加载）
import "./styles/global.css";

const pinia = createPinia();
const app = createApp(App);
app.use(pinia);
app.use(router);

// 挂载前应用主题与字号，避免首屏闪白
useUiStore(pinia).init();

app.mount("#app");

// 注册 Service Worker，启用 PWA 与离线访问（仅生产构建生效）
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // 注册失败不影响主流程
    });
  });
}
