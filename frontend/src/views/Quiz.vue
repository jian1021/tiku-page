<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { getQuestions, submitAnswer as apiSubmitAnswer } from "@/api/questions";
import { addFavorite, removeFavorite } from "@/api/favorites";
import Empty from "@/components/Empty.vue";
import Skeleton from "@/components/Skeleton.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const STORAGE_PREFIX = "sx_practice_progress:";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const questions = ref([]);
const currentIndex = ref(0);
const selected = ref([]);
const result = ref(null); // 当前题的判分结果
const submitting = ref(false);
const favoriteIds = ref(new Set());
const favoritesBusy = ref(false);

const queryKey = computed(() => {
  const { mode = "practice", chapter_id = "", year_only = "" } = route.query;
  return `${mode}|${chapter_id}|${year_only}`;
});

const currentQuestion = computed(() => questions.value[currentIndex.value] || null);
const total = computed(() => questions.value.length);
const type = computed(() => currentQuestion.value?.type || "single");
const typeText = computed(
  () => ({ single: "单选题", multi: "多选题", judge: "判断题" }[type.value] || "单选题")
);
const progress = computed(() =>
  total.value ? Math.round(((currentIndex.value + 1) / total.value) * 100) : 0
);
const isFavorited = computed(() =>
  currentQuestion.value ? favoriteIds.value.has(String(currentQuestion.value.id)) : false
);

const options = computed(() => currentQuestion.value?.options || []);
const correctKeys = computed(() => (result.value?.correct_answer || []).map(String));

function optionState(key) {
  if (!result.value) return selected.value.includes(key) ? "selected" : "";
  if (correctKeys.value.includes(key)) return "correct";
  if (selected.value.includes(key)) return "wrong";
  return "";
}

function sessionKey() {
  return `${STORAGE_PREFIX}${queryKey.value}`;
}

/** 读取本场练习的答题进度（用于答题卡与返回后恢复状态）。 */
function readProgress() {
  try {
    return JSON.parse(sessionStorage.getItem(sessionKey()) || "{}");
  } catch {
    return {};
  }
}

function writeProgress(patch) {
  try {
    const data = { ...readProgress(), ...patch };
    sessionStorage.setItem(sessionKey(), JSON.stringify(data));
  } catch {
    // 忽略存储异常
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

    // 收藏状态以服务端返回为准
    const favSet = new Set();
    for (const item of questions.value) {
      if (item.is_favorited) favSet.add(String(item.id));
    }
    favoriteIds.value = favSet;

    // 指定收藏题目跳转
    if (route.query.favorite_id) {
      const idx = questions.value.findIndex(
        (item) => String(item.id) === String(route.query.favorite_id)
      );
      if (idx >= 0) currentIndex.value = idx;
    } else if (route.query.index) {
      const idx = Number(route.query.index);
      if (Number.isInteger(idx) && idx >= 0 && idx < total.value) currentIndex.value = idx;
    }
  } catch (error) {
    const detail = String(error?.detail || error?.message || "");
    if (detail.includes("会员")) {
      showToast("该题目为会员专享，请先激活会员", "warning");
      router.replace("/me");
      return;
    }
    showToast(error?.message || "加载题目失败", "error");
  } finally {
    loading.value = false;
  }
}

function choose(key) {
  if (result.value) return;
  if (type.value === "multi") {
    const set = new Set(selected.value);
    set.has(key) ? set.delete(key) : set.add(key);
    selected.value = [...set];
  } else {
    selected.value = [key];
  }
}

async function submit() {
  if (!currentQuestion.value || submitting.value) return;
  if (selected.value.length === 0) {
    showToast("请先选择答案", "info");
    return;
  }

  submitting.value = true;
  try {
    const res = await apiSubmitAnswer(currentQuestion.value.id, selected.value);
    result.value = res;
    writeProgress({
      [currentQuestion.value.id]: { answered: true, isCorrect: Boolean(res.is_correct) },
    });
  } catch (error) {
    showToast(error?.message || "提交失败", "error");
  } finally {
    submitting.value = false;
  }
}

async function toggleFavorite() {
  if (!currentQuestion.value) return;
  if (!auth.isLoggedIn) {
    showToast("登录后可收藏题目", "info");
    router.push({ name: "Login", query: { redirect: route.fullPath } });
    return;
  }
  if (favoritesBusy.value) return;

  const id = currentQuestion.value.id;
  favoritesBusy.value = true;
  try {
    if (isFavorited.value) {
      await removeFavorite("question", id);
      favoriteIds.value.delete(String(id));
      showToast("已取消收藏", "success");
    } else {
      await addFavorite("question", id);
      favoriteIds.value.add(String(id));
      showToast("已加入收藏", "success");
    }
    favoriteIds.value = new Set(favoriteIds.value);
  } catch (error) {
    showToast(error?.message || "操作失败", "error");
  } finally {
    favoritesBusy.value = false;
  }
}

function resetState() {
  selected.value = [];
  result.value = null;
}

function goPrev() {
  if (currentIndex.value === 0) return;
  currentIndex.value -= 1;
  resetState();
}

function goNext() {
  if (currentIndex.value >= total.value - 1) {
    showToast("已经是最后一题", "info");
    return;
  }
  currentIndex.value += 1;
  resetState();
}

function goCard() {
  router.push({ path: "/quiz/card", query: { ...route.query, index: currentIndex.value } });
}

// 同路径不同 query（换章节、从收藏跳转）时组件会被复用，需要按地址重新加载
let lastKey = "";
let lastIndex = "";
watch(
  () => route.fullPath,
  () => {
    const key = queryKey.value;
    if (key !== lastKey) {
      lastKey = key;
      load();
      return;
    }
    // 仅题号变化时直接跳转，不重新请求
    const index = String(route.query.index ?? "");
    if (index !== lastIndex) {
      lastIndex = index;
      const idx = Number(index);
      if (Number.isInteger(idx) && idx >= 0 && idx < total.value) {
        currentIndex.value = idx;
        resetState();
      }
    }
  }
);

onMounted(() => {
  lastKey = queryKey.value;
  lastIndex = String(route.query.index ?? "");
  load();
});
</script>

<template>
  <div class="page quiz-page">
    <header class="quiz-header">
      <button class="icon-btn" type="button" aria-label="返回" @click="router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.back" :key="d" :d="d" />
        </svg>
      </button>
      <div class="header-center">
        <span class="header-title">{{ currentQuestion?.chapter_name || "章节练习" }}</span>
        <span class="header-count">{{ total ? currentIndex + 1 : 0 }} / {{ total }}</span>
      </div>
      <button class="icon-btn" type="button" aria-label="答题卡" @click="goCard">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in ICONS.list" :key="d" :d="d" />
        </svg>
      </button>
    </header>

    <ProgressBar :value="progress" class="quiz-progress" />

    <Skeleton v-if="loading" :rows="3" />
    <Empty v-else-if="!currentQuestion" text="暂无题目" sub="换个章节或稍后再来">
      <button class="btn btn-primary" type="button" @click="router.push('/')">返回首页</button>
    </Empty>

    <template v-else>
      <section class="question-card card">
        <div class="question-tags">
          <span v-if="currentQuestion.year" class="tag tag-year">真题 · {{ currentQuestion.year }}</span>
          <span class="tag">{{ typeText }}</span>
          <span v-if="currentQuestion.is_free" class="tag tag-free">免费</span>
        </div>

        <p class="question-stem">{{ currentQuestion.stem }}</p>

        <div class="options">
          <button
            v-for="option in options"
            :key="option.key"
            class="option"
            :class="optionState(option.key)"
            type="button"
            @click="choose(option.key)"
          >
            <span class="option-key">{{ option.key }}</span>
            <span class="option-text">{{ option.text }}</span>
          </button>
        </div>

        <div v-if="result" class="answer-panel" :class="result.is_correct ? 'ok' : 'bad'">
          <div class="answer-head">
            <strong>{{ result.is_correct ? "回答正确" : "回答错误" }}</strong>
            <span>正确答案：{{ correctKeys.join("、") || "—" }}</span>
          </div>
          <p v-if="result.explanation" class="answer-explain">{{ result.explanation }}</p>
          <p v-else class="answer-explain muted">本题暂无解析</p>
        </div>
      </section>

      <footer class="quiz-footer">
        <button class="icon-btn favorite" :class="{ active: isFavorited }" type="button" aria-label="收藏" @click="toggleFavorite">
          <svg viewBox="0 0 24 24" :fill="isFavorited ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in ICONS.star" :key="d" :d="d" />
          </svg>
        </button>

        <button class="btn nav-btn" type="button" :disabled="currentIndex === 0" @click="goPrev">上一题</button>

        <button v-if="!result" class="btn btn-primary nav-btn" type="button" :disabled="submitting || !selected.length" @click="submit">
          {{ submitting ? "提交中" : "提交答案" }}
        </button>
        <button v-else class="btn btn-primary nav-btn" type="button" @click="goNext">下一题</button>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.quiz-page {
  padding-bottom: calc(84px + env(safe-area-inset-bottom, 0px));
}

.quiz-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -16px -16px 10px;
  padding: 4px 8px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: var(--radius);
  background: transparent;
  color: var(--text);
  cursor: pointer;
}

.icon-btn svg {
  width: 22px;
  height: 22px;
}

.header-center {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.header-title {
  max-width: 100%;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-count {
  font-size: var(--fs-xs);
  color: var(--text-2);
}

.quiz-progress {
  margin-bottom: 12px;
}

.question-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 16px;
}

.question-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.question-stem {
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text);
  white-space: pre-wrap;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.option-key {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--bg);
  font-weight: 600;
  flex: none;
}

.option-text {
  flex: 1;
  line-height: 1.6;
}

.option.selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.option.selected .option-key {
  border-color: var(--primary);
  background: var(--primary);
  color: var(--primary-contrast);
}

.option.correct {
  border-color: var(--success);
  background: var(--success-soft);
}

.option.correct .option-key {
  border-color: var(--success);
  background: var(--success);
  color: var(--primary-contrast);
}

.option.wrong {
  border-color: var(--danger);
  background: var(--danger-soft);
}

.option.wrong .option-key {
  border-color: var(--danger);
  background: var(--danger);
  color: var(--card);
}

.answer-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  border-radius: var(--radius);
  background: var(--bg);
}

.answer-panel.ok .answer-head strong {
  color: var(--success);
}

.answer-panel.bad .answer-head strong {
  color: var(--danger);
}

.answer-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  font-size: var(--fs-sm);
  color: var(--text-2);
}

.answer-explain {
  color: var(--text);
  line-height: 1.7;
  white-space: pre-wrap;
}

.answer-explain.muted {
  color: var(--text-3);
}

.quiz-footer {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: var(--page-max);
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom, 0px));
  background: var(--card);
  border-top: 1px solid var(--border);
}

.favorite {
  border: 1px solid var(--border);
  color: var(--text-3);
  flex: none;
}

.favorite.active {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-soft);
}

.nav-btn {
  flex: 1;
}
</style>
