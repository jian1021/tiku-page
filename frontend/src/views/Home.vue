<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { getChapters, getProvinces } from "@/api/chapters";
import { getStats } from "@/api/questions";
import Modal from "@/components/Modal.vue";
import Skeleton from "@/components/Skeleton.vue";
import Empty from "@/components/Empty.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const provinces = ref([]);
const chapters = ref([]);
const stats = ref(null);
const showProvinceModal = ref(false);
const pendingProvince = ref(null);

const provinceCode = computed(() => {
  if (auth.isLoggedIn && auth.user?.province_code) return auth.user.province_code;
  return ui.provinceCode || "SC";
});

const currentProvinceName = computed(() => {
  const found = provinces.value.find((item) => item.code === provinceCode.value);
  return found?.name || "四川省";
});

const currentProvinceOpen = computed(() => {
  const found = provinces.value.find((item) => item.code === provinceCode.value);
  return found ? Boolean(found.open) : true;
});

/** 章节题量合计（含子章节） */
const totalQuestions = computed(() =>
  chapters.value.reduce((sum, item) => sum + (item.question_count || 0), 0)
);

/** 已答合计 */
const answeredQuestions = computed(() =>
  chapters.value.reduce((sum, item) => sum + (item.answered_count || 0), 0)
);

const overallRate = computed(() => {
  if (!totalQuestions.value) return 0;
  return Math.round((answeredQuestions.value / totalQuestions.value) * 100);
});

const entries = computed(() => [
  { key: "order", title: "顺序练习", icon: ICONS.list, count: `${totalQuestions.value} 题` },
  { key: "random", title: "随机练习", icon: ICONS.refresh, count: `${totalQuestions.value} 题` },
  { key: "wrong", title: "错题本", icon: ICONS.star, count: `${stats.value?.wrong_count ?? 0} 题` },
  { key: "year", title: "只看真题", icon: ICONS.award, count: "按年份" },
]);

async function load() {
  loading.value = true;
  try {
    provinces.value = await getProvinces();
    ui.provinces = provinces.value;

    // 游客首次进入默认四川省，与后端已开放题库保持一致
    if (!auth.isLoggedIn && !ui.provinceCode) ui.setProvinceCode("SC");

    chapters.value = (await getChapters(provinceCode.value)) || [];

    if (auth.isLoggedIn) {
      stats.value = await getStats();
    }
  } catch (error) {
    showToast(error?.message || "加载失败", "error");
  } finally {
    loading.value = false;
  }
}

function openProvinceModal() {
  pendingProvince.value = provinceCode.value;
  showProvinceModal.value = true;
}

async function confirmProvince() {
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
    } catch (error) {
      showToast(error?.message || "省份保存失败", "error");
    }
  }

  await load();
}

function goPractice(mode) {
  if (!currentProvinceOpen.value) {
    showToast("该省份题库尚未开放", "warning");
    return;
  }
  // 统一成后端认得的两种模式：只有 random 打乱，其余都按章节顺序
  const query = { mode: mode === "random" ? "random" : "practice" };
  if (mode === "year") query.year_only = "true";
  router.push({ path: "/quiz", query });
}

function goWrong() {
  router.push("/wrong");
}

function goChapter(chapter) {
  if (!chapter.question_count) {
    showToast("该章节暂无题目", "warning");
    return;
  }
  router.push({ path: `/chapter/${chapter.id}` });
}

onMounted(load);
</script>

<template>
  <div class="page">
    <!-- 顶部：法规搜索 + 省份 -->
    <header class="home-header">
      <button class="search-box" type="button" @click="router.push('/law')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.search" :key="d" :d="d" />
        </svg>
        <span class="search-placeholder">搜索法规条文</span>
      </button>

      <button class="province-chip" type="button" @click="openProvinceModal">
        {{ currentProvinceName }}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.chevronDown" :key="d" :d="d" />
        </svg>
      </button>
    </header>

    <!-- 学习概览 -->
    <section v-if="auth.isLoggedIn" class="overview card">
      <div class="overview-item">
        <span class="overview-value">{{ answeredQuestions }}</span>
        <span class="overview-label">已练题目</span>
      </div>
      <div class="overview-item">
        <span class="overview-value">{{ stats?.correct_rate ?? 0 }}%</span>
        <span class="overview-label">正确率</span>
      </div>
      <div class="overview-item">
        <span class="overview-value">{{ stats?.wrong_count ?? 0 }}</span>
        <span class="overview-label">待巩固</span>
      </div>
    </section>

    <!-- 游客 / 非会员提示 -->
    <section v-if="!auth.isLoggedIn || !auth.isMember" class="activation-banner">
      <div class="banner-text">
        <strong>{{ auth.isLoggedIn ? "激活后解锁全部题库" : "登录后可同步学习记录" }}</strong>
        <span>{{ auth.isLoggedIn ? "非会员仅可练习免费题目" : "手机号登录即可保存错题与收藏" }}</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" @click="router.push(auth.isLoggedIn ? '/me' : '/login')">
        {{ auth.isLoggedIn ? "去激活" : "去登录" }}
      </button>
    </section>

    <div v-if="!currentProvinceOpen" class="closed-tip card">
      当前省份题库正在建设中，可切换至四川省先行练习。
    </div>

    <!-- 四个练习入口 -->
    <section class="entry-grid">
      <button
        v-for="entry in entries"
        :key="entry.key"
        class="entry-card card"
        type="button"
        @click="entry.key === 'wrong' ? goWrong() : goPractice(entry.key)"
      >
        <span class="entry-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in entry.icon" :key="d" :d="d" />
          </svg>
        </span>
        <span class="entry-title">{{ entry.title }}</span>
        <span class="entry-count">{{ entry.count }}</span>
      </button>
    </section>

    <!-- 章节练习 -->
    <section class="chapter-section">
      <div class="section-head">
        <h2 class="section-title">章节练习</h2>
        <div class="section-progress">
          <ProgressBar :value="overallRate" />
          <span class="progress-text">{{ answeredQuestions }}/{{ totalQuestions }}</span>
        </div>
      </div>

      <Skeleton v-if="loading" :rows="3" />
      <Empty v-else-if="chapters.length === 0" text="暂无章节" sub="题库正在建设中，敬请期待" />
      <div v-else class="chapter-list">
        <article v-for="chapter in chapters" :key="chapter.id" class="chapter-card card">
          <button class="chapter-header" type="button" @click="goChapter(chapter)">
            <div class="chapter-info">
              <div class="chapter-name">{{ chapter.name }}</div>
              <div class="chapter-sub">{{ chapter.answered_count }}/{{ chapter.question_count }} 题</div>
            </div>
            <span class="chapter-rate">{{ chapter.question_count ? Math.round((chapter.answered_count / chapter.question_count) * 100) : 0 }}%</span>
            <svg class="chapter-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
            </svg>
          </button>

          <div v-if="chapter.children?.length" class="sub-list">
            <button
              v-for="child in chapter.children"
              :key="child.id"
              class="sub-item"
              type="button"
              @click="router.push(`/chapter/${child.id}`)"
            >
              <span class="sub-name">{{ child.name }}</span>
              <span class="sub-count">{{ child.question_count }} 题</span>
            </button>
          </div>
        </article>
      </div>
    </section>

    <!-- 省份选择 -->
    <Modal v-model="showProvinceModal" title="选择省份">
      <div class="province-list">
        <button
          v-for="p in provinces"
          :key="p.code"
          class="province-item"
          :class="{ active: p.code === pendingProvince }"
          type="button"
          @click="pendingProvince = p.code"
        >
          <span>{{ p.name }}</span>
          <span v-if="!p.open" class="tag tag-status-muted">即将开放</span>
        </button>
      </div>
      <template #footer>
        <button class="btn btn-primary btn-block" type="button" @click="confirmProvince">确定</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.home-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text-3);
  cursor: pointer;
}

.search-box svg {
  width: 18px;
  height: 18px;
}

.search-placeholder {
  font-size: var(--fs-sm);
}

.province-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}

.province-chip svg {
  width: 16px;
  height: 16px;
  color: var(--text-3);
}

.overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
  text-align: center;
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.overview-value {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--primary);
}

.overview-label {
  font-size: var(--fs-xs);
  color: var(--text-2);
}

.activation-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  border: 1px solid var(--primary-border);
  border-radius: var(--radius);
  background: var(--primary-soft);
}

.banner-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--fs-sm);
  color: var(--text);
}

.banner-text span {
  color: var(--text-2);
}

.closed-tip {
  margin-bottom: 12px;
  color: var(--accent);
  font-size: var(--fs-sm);
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.entry-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 18px 12px;
  cursor: pointer;
}

.entry-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--primary-soft);
  color: var(--primary);
}

.entry-icon svg {
  width: 22px;
  height: 22px;
}

.entry-title {
  font-weight: 600;
  color: var(--text);
}

.entry-count {
  font-size: var(--fs-xs);
  color: var(--text-2);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 600;
}

.section-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 130px;
}

.progress-text {
  font-size: var(--fs-xs);
  color: var(--text-2);
  white-space: nowrap;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chapter-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
}

.chapter-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.chapter-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chapter-name {
  font-weight: 600;
  color: var(--text);
}

.chapter-sub {
  font-size: var(--fs-xs);
  color: var(--text-2);
}

.chapter-rate {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--primary);
}

.chapter-arrow {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  flex: none;
}

.sub-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
}

.sub-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--bg);
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.sub-count {
  color: var(--text-3);
  font-size: var(--fs-xs);
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
