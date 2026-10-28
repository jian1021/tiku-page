<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getWrong, removeWrong as apiRemoveWrong } from "@/api/wrong";
import TopBar from "@/components/TopBar.vue";
import Empty from "@/components/Empty.vue";
import Skeleton from "@/components/Skeleton.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();

const loading = ref(true);
const groups = ref([]);
const total = ref(0);
const expanded = ref([]);
const removing = ref(null);

const isEmpty = computed(() => !loading.value && groups.value.length === 0);

async function load() {
  loading.value = true;
  try {
    const data = await getWrong();
    groups.value = Array.isArray(data) ? data : data?.groups || [];
    total.value = data?.total ?? groups.value.reduce((sum, g) => sum + g.items.length, 0);
    if (groups.value.length && expanded.value.length === 0) {
      expanded.value = [groups.value[0].chapter_id ?? "unknown"];
    }
  } catch (error) {
    showToast(error?.message || "加载错题失败", "error");
  } finally {
    loading.value = false;
  }
}

function toggle(chapterId) {
  const key = chapterId ?? "unknown";
  const set = new Set(expanded.value);
  set.has(key) ? set.delete(key) : set.add(key);
  expanded.value = [...set];
}

async function remove(questionId) {
  if (removing.value) return;
  removing.value = questionId;
  try {
    await apiRemoveWrong(questionId);
    showToast("已移出错题本", "success");
    await load();
  } catch (error) {
    showToast(error?.message || "操作失败", "error");
  } finally {
    removing.value = null;
  }
}

function redo(group) {
  if (!group.chapter_id) {
    showToast("该题目所属章节已删除，无法重做", "warning");
    return;
  }
  router.push({ path: "/quiz", query: { chapter_id: group.chapter_id, mode: "practice" } });
}

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const diff = Date.now() - date.getTime();
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`;
  return date.toLocaleDateString("zh-CN");
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="错题本" right-text="收藏夹" @right="router.push('/favorites')" />

    <Skeleton v-if="loading" :rows="3" />
    <Empty v-else-if="isEmpty" text="暂无错题" sub="练习中答错的题目会自动收录到这里">
      <button class="btn btn-primary" type="button" @click="router.push('/')">去练习</button>
    </Empty>

    <template v-else>
      <p class="summary">共 {{ total }} 道错题，按章节分组</p>

      <section v-for="group in groups" :key="group.chapter_id ?? 'unknown'" class="group card">
        <button class="group-head" type="button" @click="toggle(group.chapter_id)">
          <span class="group-name">{{ group.chapter_name || "未分类" }}</span>
          <span class="group-count">{{ group.items.length }} 题</span>
          <svg class="group-arrow" :class="{ open: expanded.includes(group.chapter_id ?? 'unknown') }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in ICONS.chevronDown" :key="d" :d="d" />
          </svg>
        </button>

        <div v-if="expanded.includes(group.chapter_id ?? 'unknown')" class="group-body">
          <article v-for="item in group.items" :key="item.question.id" class="wrong-item">
            <p class="stem">{{ item.question.stem }}</p>
            <div class="meta">
              <span class="tag tag-status-danger">错 {{ item.wrong_count }} 次</span>
              <span class="time">{{ formatTime(item.last_wrong_at) }}</span>
            </div>
            <div class="actions">
              <button class="btn btn-ghost btn-sm" type="button" @click="redo(group)">重做本章</button>
              <button
                class="btn btn-danger btn-sm"
                type="button"
                :disabled="removing === item.question.id"
                @click="remove(item.question.id)"
              >
                {{ removing === item.question.id ? "移除中" : "移出错题本" }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.summary {
  margin-bottom: 12px;
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.group {
  margin-bottom: 10px;
  padding: 0;
  overflow: hidden;
}

.group-head {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 14px 16px;
  border: none;
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.group-name {
  flex: 1;
  font-weight: 600;
}

.group-count {
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.group-arrow {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  transition: transform 0.2s ease;
}

.group-arrow.open {
  transform: rotate(180deg);
}

.group-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 16px 16px;
}

.wrong-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
}

.stem {
  color: var(--text);
  line-height: 1.65;
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.actions {
  display: flex;
  gap: 8px;
}
</style>
