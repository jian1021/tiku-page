<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getLaws } from "@/api/laws";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import TopBar from "@/components/TopBar.vue";
import Skeleton from "@/components/Skeleton.vue";
import Empty from "@/components/Empty.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const laws = ref([]);
const category = ref("");
const status = ref("");

// 与后端 law_documents.category 取值保持一致（中文）
const categories = [
  { value: "", label: "全部" },
  { value: "国家法律", label: "国家法律" },
  { value: "行政法规", label: "行政法规" },
  { value: "部门规章", label: "部门规章" },
  { value: "地方规定", label: "地方规定" },
];

const statuses = [
  { value: "", label: "全部" },
  { value: "effective", label: "现行有效" },
  { value: "revised", label: "已修订" },
  { value: "repealed", label: "已废止" },
];

const provinceCode = computed(() => {
  if (auth.isLoggedIn && auth.user?.province_code) return auth.user.province_code;
  return ui.provinceCode || "SC";
});

async function load() {
  loading.value = true;
  try {
    const params = { province_code: provinceCode.value };
    if (category.value) params.category = category.value;
    if (status.value) params.status = status.value;
    const data = await getLaws(params);
    laws.value = Array.isArray(data) ? data : data?.items || [];
  } catch (error) {
    showToast(error?.message || "加载失败", "error");
  } finally {
    loading.value = false;
  }
}

function statusClass(value) {
  if (value === "repealed") return "tag-status-danger";
  if (value === "revised") return "tag-status-warn";
  if (value === "effective") return "tag-status-ok";
  return "tag-status-muted";
}

function statusText(value) {
  return statuses.find((item) => item.value === value)?.label || value || "";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("zh-CN");
}

function pickCategory(value) {
  category.value = value;
  load();
}

function pickStatus(value) {
  status.value = value;
  load();
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="法规库" />

    <button class="search-bar" type="button" @click="router.push('/law/search')">
      <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path v-for="d in ICONS.search" :key="d" :d="d" />
      </svg>
      <span>搜索法规名称或条文</span>
    </button>

    <div class="filters">
      <div class="filter-group">
        <button
          v-for="item in categories"
          :key="item.value"
          class="chip"
          :class="{ active: category === item.value }"
          type="button"
          @click="pickCategory(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
      <div class="filter-group">
        <button
          v-for="item in statuses"
          :key="item.value"
          class="chip"
          :class="{ active: status === item.value }"
          type="button"
          @click="pickStatus(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <Skeleton v-if="loading" :rows="3" />
    <Empty v-else-if="laws.length === 0" text="暂无法规" sub="试试切换分类或效力状态" />

    <div v-else class="law-list">
      <button v-for="law in laws" :key="law.id" class="law-item card" type="button" @click="router.push(`/law/${law.id}`)">
        <div class="law-title">{{ law.title }}</div>
        <div class="law-meta">
          <span class="tag" :class="statusClass(law.status)">{{ statusText(law.status) }}</span>
          <span v-if="law.category" class="tag tag-status-muted">{{ law.category }}</span>
          <span v-if="law.article_count" class="meta-text">{{ law.article_count }} 条</span>
        </div>
        <div class="law-sub">
          <span v-if="law.issuer" class="meta-text">{{ law.issuer }}</span>
          <span v-if="law.publish_date" class="meta-text">{{ formatDate(law.publish_date) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  margin-bottom: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text-3);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.search-icon {
  width: 18px;
  height: 18px;
}

.filters {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--card);
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.chip.active {
  border-color: var(--primary-border);
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 600;
}

.law-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.law-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  text-align: left;
  cursor: pointer;
}

.law-title {
  color: var(--text);
  font-weight: 600;
  line-height: 1.6;
}

.law-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.law-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-text {
  color: var(--text-3);
  font-size: var(--fs-xs);
}
</style>
