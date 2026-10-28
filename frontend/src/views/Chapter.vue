<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { getChapters } from "@/api/chapters";
import TopBar from "@/components/TopBar.vue";
import Empty from "@/components/Empty.vue";
import Skeleton from "@/components/Skeleton.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const chapter = ref(null);
const path = ref([]);

const provinceCode = computed(() => {
  if (auth.isLoggedIn && auth.user?.province_code) return auth.user.province_code;
  return ui.provinceCode || "SC";
});

const rate = computed(() => {
  const total = chapter.value?.question_count || 0;
  if (!total) return 0;
  return Math.round(((chapter.value.answered_count || 0) / total) * 100);
});

/** 在章节树中递归查找目标章节，同时记录父级路径用于面包屑。 */
function find(items, id, trail = []) {
  for (const item of items || []) {
    const nextTrail = [...trail, item];
    if (String(item.id) === String(id)) return { node: item, trail: nextTrail };
    const found = find(item.children, id, nextTrail);
    if (found) return found;
  }
  return null;
}

async function load() {
  loading.value = true;
  try {
    const list = await getChapters(provinceCode.value);
    const found = find(Array.isArray(list) ? list : [], route.params.id);
    chapter.value = found?.node || null;
    path.value = found?.trail || [];
  } catch (error) {
    showToast(error?.message || "加载章节失败", "error");
  } finally {
    loading.value = false;
  }
}

function startPractice(target) {
  const id = target?.id ?? chapter.value?.id;
  if (!id) return;
  if (!(target?.question_count ?? chapter.value?.question_count)) {
    showToast("该章节暂无题目", "warning");
    return;
  }
  router.push({ path: "/quiz", query: { chapter_id: id, mode: "practice" } });
}

function startRandom(target) {
  const id = target?.id ?? chapter.value?.id;
  if (!id) return;
  router.push({ path: "/quiz", query: { chapter_id: id, mode: "random" } });
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar :title="chapter?.name || '章节练习'" />

    <Skeleton v-if="loading" :rows="3" />

    <Empty v-else-if="!chapter" text="章节不存在" sub="该章节可能已被管理员调整">
      <button class="btn btn-primary" type="button" @click="router.replace('/')">返回首页</button>
    </Empty>

    <template v-else>
      <nav class="breadcrumb">
        <button
          v-for="item in path"
          :key="item.id"
          class="crumb"
          type="button"
          @click="router.push(`/chapter/${item.id}`)"
        >
          {{ item.name }}
        </button>
      </nav>

      <section class="overview card">
        <div class="overview-head">
          <span class="overview-count">{{ chapter.answered_count }}/{{ chapter.question_count }} 题</span>
          <span class="overview-rate">{{ rate }}%</span>
        </div>
        <ProgressBar :value="rate" />
        <div class="overview-actions">
          <button class="btn btn-primary" type="button" @click="startPractice()">顺序练习</button>
          <button class="btn" type="button" @click="startRandom()">随机练习</button>
        </div>
      </section>

      <section class="children">
        <h2 class="section-title">子章节</h2>
        <Empty v-if="!chapter.children?.length" text="本章暂无子章节" sub="可直接开始本章顺序练习" />
        <div v-else class="child-list">
          <button
            v-for="child in chapter.children"
            :key="child.id"
            class="child card"
            type="button"
            @click="startPractice(child)"
          >
            <div class="child-info">
              <span class="child-name">{{ child.name }}</span>
              <span class="child-meta">{{ child.answered_count }}/{{ child.question_count }} 题</span>
            </div>
            <svg class="child-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
            </svg>
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
  font-size: var(--fs-sm);
  color: var(--text-3);
}

.crumb {
  border: none;
  background: transparent;
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
  padding: 0;
}

.crumb::after {
  content: "/";
  margin-left: 4px;
  color: var(--text-3);
}

.crumb:last-child {
  color: var(--text);
  font-weight: 600;
}

.crumb:last-child::after {
  content: "";
}

.overview {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.overview-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.overview-count {
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.overview-rate {
  color: var(--primary);
  font-weight: 700;
}

.overview-actions {
  display: flex;
  gap: 8px;
}

.overview-actions .btn {
  flex: 1;
}

.section-title {
  margin-bottom: 10px;
  font-size: 1.05rem;
  font-weight: 600;
}

.child-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.child {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  text-align: left;
  cursor: pointer;
}

.child-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.child-name {
  font-weight: 600;
  color: var(--text);
}

.child-meta {
  font-size: var(--fs-xs);
  color: var(--text-2);
}

.child-arrow {
  width: 18px;
  height: 18px;
  color: var(--text-3);
}
</style>
