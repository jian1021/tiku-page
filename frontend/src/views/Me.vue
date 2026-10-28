<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { activate } from "@/api/members";
import { getSiteConfig, getStats } from "@/api/questions";
import { getProvinces } from "@/api/chapters";
import TopBar from "@/components/TopBar.vue";
import Modal from "@/components/Modal.vue";
import Skeleton from "@/components/Skeleton.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const stats = ref(null);
const site = ref({});
const provinces = ref([]);
const code = ref("");
const activating = ref(false);
const showProvinceModal = ref(false);
const pendingProvince = ref("");

const memberText = computed(() => {
  if (!auth.isLoggedIn) return "未登录";
  if (auth.isMember) {
    return auth.membershipExpiresAt
      ? `会员有效期至 ${formatDate(auth.membershipExpiresAt)}（剩 ${auth.memberDaysLeft} 天）`
      : "管理员账号";
  }
  return "尚未激活会员";
});

const provinceName = computed(() => {
  const value = auth.user?.province_code || ui.provinceCode;
  return provinces.value.find((item) => item.code === value)?.name || "未选择";
});

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("zh-CN");
}

async function load() {
  loading.value = true;
  try {
    const [statsData, siteData, provinceList] = await Promise.all([
      auth.isLoggedIn ? getStats().catch(() => null) : Promise.resolve(null),
      getSiteConfig().catch(() => ({})),
      getProvinces().catch(() => []),
    ]);
    stats.value = statsData;
    site.value = siteData || {};
    provinces.value = Array.isArray(provinceList) ? provinceList : [];
    pendingProvince.value = auth.user?.province_code || ui.provinceCode || "SC";
  } finally {
    loading.value = false;
  }
}

async function submitCode() {
  const value = code.value.trim();
  if (!value) {
    showToast("请输入激活码", "info");
    return;
  }
  if (!auth.isLoggedIn) {
    router.push({ name: "Login", query: { redirect: "/me" } });
    return;
  }

  activating.value = true;
  try {
    const res = await activate(value);
    await auth.fetchMe();
    code.value = "";
    showToast(`激活成功，有效期至 ${formatDate(res?.expires_at)}`, "success");
    await load();
  } catch (error) {
    showToast(error?.message || "激活失败", "error");
  } finally {
    activating.value = false;
  }
}

async function saveProvince() {
  const target = provinces.value.find((item) => item.code === pendingProvince.value);
  if (!target) return;
  if (!target.open) {
    showToast("该省份题库尚未开放", "warning");
    return;
  }

  ui.setProvinceCode(target.code);
  showProvinceModal.value = false;

  if (auth.isLoggedIn) {
    try {
      await auth.updateSettings({ province_code: target.code });
      showToast("省份已更新", "success");
    } catch (error) {
      showToast(error?.message || "保存失败", "error");
    }
  }
}

function logout() {
  auth.logout();
  showToast("已退出登录", "success");
  router.replace("/");
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="我的" :back="false" />

    <!-- 账号信息 -->
    <section class="profile card">
      <div class="avatar">{{ auth.isLoggedIn ? auth.displayName.slice(0, 1) : "客" }}</div>
      <div class="profile-info">
        <h2 class="profile-name">{{ auth.isLoggedIn ? auth.displayName : "未登录" }}</h2>
        <p class="profile-sub">{{ auth.isLoggedIn ? memberText : "登录后可同步错题、收藏与考试记录" }}</p>
      </div>
      <button v-if="!auth.isLoggedIn" class="btn btn-primary btn-sm" type="button" @click="router.push('/login')">
        登录
      </button>
      <button v-else class="btn btn-sm" type="button" @click="logout">退出</button>
    </section>

    <!-- 学习统计 -->
    <Skeleton v-if="loading" :rows="1" />
    <section v-else class="stats card">
      <h3 class="block-title">学习数据</h3>
      <div class="stats-grid">
        <div class="stat">
          <span class="stat-value">{{ stats?.answered_count ?? 0 }}</span>
          <span class="stat-label">累计答题</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ stats?.correct_rate ?? 0 }}%</span>
          <span class="stat-label">正确率</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ stats?.wrong_count ?? 0 }}</span>
          <span class="stat-label">错题本</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ stats?.favorite_count ?? 0 }}</span>
          <span class="stat-label">收藏</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ stats?.exam_count ?? 0 }}</span>
          <span class="stat-label">模拟考试</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ auth.isMember ? "有效" : "未开通" }}</span>
          <span class="stat-label">会员状态</span>
        </div>
      </div>
    </section>

    <!-- 会员激活 -->
    <section class="activate card">
      <h3 class="block-title">会员激活</h3>
      <p class="block-desc">输入激活码解锁全部题库、法规库与模拟考试。</p>
      <div class="activate-row">
        <input
          v-model="code"
          class="code-input"
          type="text"
          maxlength="64"
          placeholder="请输入激活码"
          @keyup.enter="submitCode"
        />
        <button class="btn btn-primary" type="button" :disabled="activating" @click="submitCode">
          {{ activating ? "激活中" : "激活" }}
        </button>
      </div>
    </section>

    <!-- 快捷入口 -->
    <section class="quick card">
      <button class="quick-item" type="button" @click="router.push('/wrong')">
        <span>错题本</span>
        <span class="quick-value">{{ stats?.wrong_count ?? 0 }} 题</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
        </svg>
      </button>
      <button class="quick-item" type="button" @click="router.push('/favorites')">
        <span>我的收藏</span>
        <span class="quick-value">{{ stats?.favorite_count ?? 0 }} 条</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
        </svg>
      </button>
      <button class="quick-item" type="button" @click="router.push('/exam')">
        <span>模拟考试</span>
        <span class="quick-value">{{ stats?.exam_count ?? 0 }} 次</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
        </svg>
      </button>
    </section>

    <!-- 偏好设置 -->
    <section class="settings card">
      <h3 class="block-title">偏好设置</h3>

      <div class="setting-row">
        <span>题库省份</span>
        <button class="setting-value" type="button" @click="showProvinceModal = true">
          {{ provinceName }}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
          </svg>
        </button>
      </div>

      <div class="setting-row">
        <span>夜间模式</span>
        <button
          class="switch"
          :class="{ on: ui.theme === 'dark' }"
          type="button"
          role="switch"
          :aria-checked="ui.theme === 'dark'"
          @click="ui.toggleTheme()"
        >
          <span class="switch-dot"></span>
        </button>
      </div>

      <div class="setting-row">
        <span>正文字号</span>
        <div class="seg">
          <button
            v-for="item in [{ key: 'small', label: '小' }, { key: 'medium', label: '中' }, { key: 'large', label: '大' }]"
            :key="item.key"
            class="seg-btn"
            :class="{ active: ui.fontSize === item.key }"
            type="button"
            @click="ui.setFontSize(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </section>

    <!-- 其他 -->
    <section class="links card">
      <button class="link" type="button" @click="router.push('/service')">联系客服与意见反馈</button>
      <button class="link" type="button" @click="router.push('/agreement')">用户协议</button>
      <button class="link" type="button" @click="router.push('/privacy')">隐私政策</button>
    </section>

    <p class="version">版本 {{ site.version || "1.0.0" }} · 题库内容仅供备考参考</p>

    <Modal v-model="showProvinceModal" title="选择题库省份">
      <div class="province-list">
        <button
          v-for="item in provinces"
          :key="item.code"
          class="province-item"
          :class="{ active: pendingProvince === item.code }"
          type="button"
          @click="pendingProvince = item.code"
        >
          <span>{{ item.name }}</span>
          <span v-if="!item.open" class="tag tag-status-muted">即将开放</span>
        </button>
      </div>
      <template #footer>
        <button class="btn btn-primary btn-block" type="button" @click="saveProvince">保存</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.profile {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 1.2rem;
  font-weight: 700;
  flex: none;
}

.profile-info {
  flex: 1;
  min-width: 0;
}

.profile-name {
  font-size: 1.05rem;
  font-weight: 600;
}

.profile-sub {
  color: var(--text-2);
  font-size: var(--fs-xs);
  line-height: 1.5;
}

.block-title {
  font-size: 1rem;
  font-weight: 600;
}

.block-desc {
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.stats,
.activate,
.quick,
.settings,
.links {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  text-align: center;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  color: var(--text-2);
  font-size: var(--fs-xs);
}

.activate-row {
  display: flex;
  gap: 8px;
}

.code-input {
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
}

.quick-item,
.link {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0;
  border: none;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.quick-item:last-child,
.link:last-child {
  border-bottom: none;
}

.quick-item span:first-child,
.link {
  flex: 1;
}

.quick-value {
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.quick-item svg,
.setting-value svg {
  width: 18px;
  height: 18px;
  color: var(--text-3);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 44px;
}

.setting-value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.switch {
  position: relative;
  width: 50px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--bg);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.switch.on {
  background: var(--primary);
  border-color: var(--primary);
}

.switch-dot {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--card);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
}

.switch.on .switch-dot {
  transform: translateX(20px);
}

.seg {
  display: flex;
  gap: 4px;
}

.seg-btn {
  min-width: 44px;
  min-height: 34px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--text-2);
  cursor: pointer;
}

.seg-btn.active {
  border-color: var(--primary-border);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.version {
  padding: 4px 0 8px;
  color: var(--text-3);
  font-size: var(--fs-xs);
  text-align: center;
}

.province-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 52vh;
  overflow-y: auto;
}

.province-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--radius);
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.province-item.active {
  border-color: var(--primary-border);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}
</style>
