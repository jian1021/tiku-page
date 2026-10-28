<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { getQuestions } from "@/api/questions";
import TopBar from "@/components/TopBar.vue";
import Skeleton from "@/components/Skeleton.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import { showToast } from "@/composables/useToast";

const STORAGE_PREFIX = "sx_practice_progress:";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const questions = ref([]);
const progress = ref({});

const queryKey = computed(() => {
  const { mode = "practice", chapter_id = "", year_only = "" } = route.query;
  return `${mode}|${chapter_id}|${year_only}`;
});

const answeredCount = computed(
  () => questions.value.filter((q) => progress.value[String(q.id)]?.answered).length
);
const correctCount = computed(
  () => questions.value.filter((q) => progress.value[String(q.id)]?.isCorrect).length
);
const wrongCount = computed(() => answeredCount.value - correctCount.value);
const rate = computed(() =>
  questions.value.length ? Math.round((answeredCount.value / questions.value.length) * 100) : 0
);

function readProgress() {
  try {
    return JSON.parse(sessionStorage.getItem(`${STORAGE_PREFIX}${queryKey.value}`) || "{}");
  } catch {
    return {};
  }
}

async function load() {
  loading.value = true;
  try {
    const params = {
      province_code: (auth.isLoggedIn && auth.user?.province_code) || ui.provinceCode || "SC",
      mode: route.query.mode === "random" ? "random" : "practice",
      year_only: route.query.year_only === "true",
    };
    if (route.query.chapter_id) params.chapter_id = Number(route.query.chapter_id);

    const data = await getQuestions(params);
    questions.value = Array.isArray(data) ? data : data?.items || [];
    progress.value = readProgress();
  } catch (error) {
    showToast(error?.message || "加载题目失败", "error");
  } finally {
    loading.value = false;
  }
}

function itemClass(question) {
  const state = progress.value[String(question.id)];
  if (!state?.answered) return "pending";
  return state.isCorrect ? "correct" : "wrong";
}

function goQuestion(index) {
  router.replace({ path: "/quiz", query: { ...route.query, index } });
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="答题卡" />

    <Skeleton v-if="loading" :rows="2" />

    <template v-else>
      <section class="summary card">
        <div class="summary-head">
          <span class="summary-title">已答 {{ answeredCount }} / {{ questions.length }}</span>
          <span class="summary-rate">{{ rate }}%</span>
        </div>
        <ProgressBar :value="rate" />
        <div class="summary-stats">
          <span class="stat ok">正确 {{ correctCount }}</span>
          <span class="stat bad">错误 {{ wrongCount }}</span>
          <span class="stat pending">未答 {{ questions.length - answeredCount }}</span>
        </div>
      </section>

      <section class="grid card">
        <button
          v-for="(question, index) in questions"
          :key="question.id"
          class="cell"
          :class="itemClass(question)"
          type="button"
          @click="goQuestion(index)"
        >
          {{ index + 1 }}
        </button>
      </section>

      <p class="hint">点击题号可跳回对应题目继续作答；本场练习进度仅保存在当前设备。</p>
    </template>
  </div>
</template>

<style scoped>
.summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.summary-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.summary-title {
  font-weight: 600;
}

.summary-rate {
  color: var(--primary);
  font-weight: 700;
}

.summary-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: var(--fs-sm);
}

.stat.ok {
  color: var(--success);
}

.stat.bad {
  color: var(--danger);
}

.stat.pending {
  color: var(--text-2);
}

.grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}

.cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
}

.cell.correct {
  border-color: var(--success);
  background: var(--success-soft);
  color: var(--success);
}

.cell.wrong {
  border-color: var(--danger);
  background: var(--danger-soft);
  color: var(--danger);
}

.hint {
  margin-top: 12px;
  color: var(--text-3);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

@media (max-width: 400px) {
  .grid {
    grid-template-columns: repeat(5, 1fr);
  }
}
</style>
