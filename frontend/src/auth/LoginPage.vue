<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { showToast } from "@/composables/useToast";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const phone = ref("");
const password = ref("");
const loading = ref(false);
const errorText = ref("");

const PHONE_RE = /^1[3-9]\d{9}$/;

async function submit() {
  errorText.value = "";

  if (!PHONE_RE.test(phone.value.trim())) {
    errorText.value = "请输入正确的手机号";
    return;
  }
  if (password.value.length < 6) {
    errorText.value = "密码至少 6 位";
    return;
  }

  loading.value = true;
  try {
    await auth.login(phone.value.trim(), password.value);
    showToast("登录成功", "success");
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    router.replace(redirect);
  } catch (error) {
    errorText.value = error?.message || "登录失败，请稍后重试";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="page auth-page">
    <header class="auth-header">
      <h1 class="auth-title">专家库考试助手</h1>
      <p class="auth-sub">政府采购评审专家入库考试备考平台</p>
    </header>

    <form class="auth-form card" @submit.prevent="submit">
      <label class="field">
        <span class="field-label">手机号</span>
        <input
          v-model="phone"
          class="field-input"
          type="tel"
          inputmode="numeric"
          maxlength="11"
          autocomplete="tel"
          placeholder="请输入 11 位手机号"
        />
      </label>

      <label class="field">
        <span class="field-label">密码</span>
        <input
          v-model="password"
          class="field-input"
          type="password"
          autocomplete="current-password"
          placeholder="请输入密码"
        />
      </label>

      <p v-if="errorText" class="field-error" role="alert">{{ errorText }}</p>

      <button class="btn btn-primary btn-block" type="submit" :disabled="loading">
        {{ loading ? "登录中" : "登录" }}
      </button>

      <div class="auth-links">
        <button class="link-btn" type="button" @click="router.push('/register')">还没有账号？立即注册</button>
      </div>
    </form>

    <p class="auth-tip">
      登录即表示同意
      <button class="text-link" type="button" @click="router.push('/agreement')">用户协议</button>
      与
      <button class="text-link" type="button" @click="router.push('/privacy')">隐私政策</button>
    </p>

    <button class="back-home" type="button" @click="router.replace('/')">先随便看看</button>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 32px;
}

.auth-header {
  text-align: center;
}

.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
}

.auth-sub {
  margin-top: 4px;
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.field-input {
  min-height: 46px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
  outline: none;
}

.field-input:focus {
  border-color: var(--primary);
}

.field-error {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  color: var(--danger);
  font-size: var(--fs-sm);
}

.auth-links {
  text-align: center;
}

.link-btn {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.auth-tip {
  text-align: center;
  color: var(--text-3);
  font-size: var(--fs-xs);
  line-height: 1.8;
}

.text-link {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: inherit;
  cursor: pointer;
}

.back-home {
  align-self: center;
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}
</style>
