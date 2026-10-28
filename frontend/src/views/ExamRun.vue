<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getExam, saveExamAnswer, submitExam } from "../api/exams";
import Modal from "../components/Modal.vue";
import { showToast } from "../composables/useToast";
import { ICONS } from "../components/icons";

const route = useRoute();
const router = useRouter();

const examId = computed(() => route.query.id);
const loading = ref(true);
const exam = ref(null);
const questions = ref([]);
const currentIndex = ref(0);
const answers = ref({}); // questionId -> [selected]
const marked = ref(new Set());
const timeLeft = ref(0);
const timer = ref(null);
const showCardModal = ref(false);
const showSubmitModal = ref(false);

// Touch swipe
let touchStartX = 0;
let touchEndX = 0;

const currentQuestion = computed(() => questions.value[currentIndex.value] || null);
const total = computed(() => questions.value.length);
const isMulti = computed(() => {
  const type = currentQuestion.value?.type;
  return type === "multi" || type === "multiple";
});

const timeText = computed(() => {
  const m = Math.floor(timeLeft.value / 60);
  const s = timeLeft.value % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
});

const timeWarning = computed(() => timeLeft.value < 60);

async function load() {
  loading.value = true;
  try {
    const data = await getExam(examId.value);
    exam.value = data;
    questions.value = Array.isArray(data?.questions) ? data.questions : [];
    // Restore answers
    if (data?.answers) {
      answers.value = data.answers;
    }

    // 已交卷（如超时自动交卷）直接跳转结果页
    if (data?.submitted_at) {
      router.replace(`/exam/result/${examId.value}`);
      return;
    }

    // 剩余时间以服务端计算为准，避免客户端时间漂移
    if (typeof data?.remaining_seconds === "number") {
      timeLeft.value = Math.max(0, data.remaining_seconds);
      startTimer();
    } else if (data?.started_at && data?.duration_limit_sec) {
      const started = new Date(data.started_at).getTime();
      const serverTime = data?.server_time ? new Date(data.server_time).getTime() : Date.now();
      const elapsed = Math.floor((serverTime - started) / 1000);
      timeLeft.value = Math.max(0, data.duration_limit_sec - elapsed);
      startTimer();
    }
  } catch (e) {
    showToast(e?.message || "加载失败", "error");
  } finally {
    loading.value = false;
  }
}

function startTimer() {
  if (timer.value) clearInterval(timer.value);
  timer.value = setInterval(() => {
    timeLeft.value--;
    if (timeLeft.value <= 0) {
      timeLeft.value = 0;
      clearInterval(timer.value);
      autoSubmit();
    }
  }, 1000);
}

async function autoSubmit() {
  showToast("时间到，自动交卷", "warning");
  await doSubmit();
}

function toggleOption(optKey) {
  if (!currentQuestion.value) return;
  if (!answers.value[currentQuestion.value.id]) {
    answers.value[currentQuestion.value.id] = [];
  }
  const arr = answers.value[currentQuestion.value.id];
  if (isMulti.value) {
    const idx = arr.indexOf(optKey);
    if (idx >= 0) {
      arr.splice(idx, 1);
    } else {
      arr.push(optKey);
    }
    answers.value[currentQuestion.value.id] = [...arr];
  } else {
    answers.value[currentQuestion.value.id] = [optKey];
  }
  // Auto save
  saveAnswer(currentQuestion.value.id, answers.value[currentQuestion.value.id]);
}

async function saveAnswer(qid, selected) {
  try {
    const res = await saveExamAnswer(examId.value, qid, selected);
    // 服务端判定已超时并自动交卷
    if (res?.auto_submitted) {
      if (timer.value) clearInterval(timer.value);
      showToast("考试时间已到，已自动交卷", "warning");
      router.replace(`/exam/result/${examId.value}`);
    }
  } catch (e) {
    // 保存失败不阻塞答题，交卷时会以最终答案为准
  }
}

function toggleMark() {
  if (!currentQuestion.value) return;
  const id = currentQuestion.value.id;
  if (marked.value.has(id)) {
    marked.value.delete(id);
  } else {
    marked.value.add(id);
  }
  marked.value = new Set(marked.value);
}

function openCard() {
  showCardModal.value = true;
}

function goToQuestion(idx) {
  currentIndex.value = idx;
  showCardModal.value = false;
}

function prevQuestion() {
  if (currentIndex.value > 0) currentIndex.value--;
}

function nextQuestion() {
  if (currentIndex.value < total.value - 1) currentIndex.value++;
}

function confirmSubmit() {
  showSubmitModal.value = true;
}

async function doSubmit() {
  showSubmitModal.value = false;
  try {
    const res = await submitExam(examId.value, answers.value);
    const resultId = res.id || examId.value;
    router.replace(`/exam/result/${resultId}`);
  } catch (e) {
    showToast(e?.message || "交卷失败", "error");
  }
}

function onTouchStart(e) {
  touchStartX = e.changedTouches[0].screenX;
}

function onTouchEnd(e) {
  touchEndX = e.changedTouches[0].screenX;
  const diff = touchEndX - touchStartX;
  if (Math.abs(diff) > 50) {
    if (diff > 0) prevQuestion();
    else nextQuestion();
  }
}

function isOptionSelected(optKey) {
  const sel = answers.value[currentQuestion.value?.id] || [];
  return sel.includes(optKey);
}

onMounted(() => {
  load();
  // beforeunload warning
  window.addEventListener('beforeunload', (e) => {
    if (timeLeft.value > 0) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
});

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value);
});
</script>

<template>
  <div class="page exam-run-page">
    <header class="exam-run-header">
      <div class="header-left">
        <div class="timer" :class="{ warning: timeWarning }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in ICONS.clock" :key="d" :d="d" />
          </svg>
          <span>{{ timeText }}</span>
        </div>
      </div>
      <div class="header-center">{{ currentIndex + 1 }} / {{ total }}</div>
      <button class="header-btn" type="button" @click="openCard">答题卡</button>
    </header>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!currentQuestion" class="empty">暂无题目</div>
    <div v-else class="exam-content" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <section class="question-card card">
        <div class="question-meta">
          <span class="tag">{{ isMulti ? '多选题' : currentQuestion.type === 'judge' ? '判断题' : '单选题' }}</span>
          <button class="mark-btn" :class="{ marked: marked.has(currentQuestion.id) }" type="button" @click="toggleMark">
            {{ marked.has(currentQuestion.id) ? '已标记' : '标记待检查' }}
          </button>
        </div>
        <div class="question-stem">{{ currentQuestion.stem }}</div>
        <div class="options-list">
          <button
            v-for="(opt, idx) in currentQuestion.options || []"
            :key="opt.key || idx"
            class="option-item"
            :class="{ selected: isOptionSelected(opt.key || String.fromCharCode(65 + idx)) }"
            type="button"
            @click="toggleOption(opt.key || String.fromCharCode(65 + idx))"
          >
            <span class="option-key">{{ opt.key || String.fromCharCode(65 + idx) }}</span>
            <span class="option-text">{{ opt.text }}</span>
          </button>
        </div>
      </section>
    </div>

    <footer class="exam-footer safe-bottom">
      <button class="footer-btn" type="button" :disabled="currentIndex === 0" @click="prevQuestion">上一题</button>
      <button class="footer-btn footer-btn-submit" type="button" @click="confirmSubmit">交卷</button>
      <button class="footer-btn" type="button" :disabled="currentIndex >= total - 1" @click="nextQuestion">下一题</button>
    </footer>

    <!-- 答题卡 Modal -->
    <Modal v-model="showCardModal" title="答题卡">
      <div class="card-grid">
        <button
          v-for="(q, idx) in questions"
          :key="q.id"
          class="card-btn"
          :class="{
            answered: (answers[q.id] && answers[q.id].length > 0),
            marked: marked.has(q.id),
            current: idx === currentIndex
          }"
          type="button"
          @click="goToQuestion(idx)"
        >
          {{ idx + 1 }}
        </button>
      </div>
    </Modal>

    <!-- 交卷确认 Modal -->
    <Modal v-model="showSubmitModal" title="确认交卷">
      <div class="submit-confirm">
        <p>确定要交卷吗？交卷后将无法修改答案。</p>
        <p class="submit-stats">已答：{{ Object.values(answers).filter(a => a && a.length > 0).length }} / {{ total }}</p>
      </div>
      <template #footer>
        <button class="btn" type="button" @click="showSubmitModal = false">取消</button>
        <button class="btn btn-primary" type="button" @click="doSubmit">确认交卷</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.exam-run-page {
  display: flex;
  flex-direction: column;
  padding-bottom: calc(90px + env(safe-area-inset-bottom, 0px));
}

.exam-run-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: -16px -16px 16px;
  padding: 4px 12px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.header-left {
  flex: 1;
}

.timer {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text);
  font-weight: 600;
}

.timer svg {
  width: 18px;
  height: 18px;
}

.timer.warning {
  color: var(--danger);
}

.header-center {
  color: var(--text-2);
}

.header-btn {
  flex: 1;
  text-align: right;
  min-height: 44px;
  border: none;
  background: transparent;
  color: var(--primary);
  font-weight: 600;
  cursor: pointer;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-2);
}

.exam-content {
  flex: 1;
}

.question-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mark-btn {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.mark-btn.marked {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
}

.question-stem {
  font-size: 1.05rem;
  line-height: 1.7;
  color: var(--text);
  white-space: pre-wrap;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  text-align: left;
  cursor: pointer;
  color: var(--text);
}

.option-key {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg);
  border: 1px solid var(--border);
  flex: none;
  font-weight: 600;
}

.option-text {
  flex: 1;
  line-height: 1.6;
}

.option-item.selected {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.option-item.selected .option-key {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast);
}

.exam-footer {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--page-max);
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  background: var(--card);
  border-top: 1px solid var(--border);
}

.footer-btn {
  flex: 1;
  min-height: 44px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
}

.footer-btn:disabled {
  opacity: 0.4;
}

.footer-btn-submit {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}

.card-btn {
  height: 42px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
}

.card-btn.answered {
  background: var(--primary-soft);
  border-color: var(--primary-border);
  color: var(--primary);
}

.card-btn.marked {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
}

.card-btn.current {
  border-width: 2px;
  border-color: var(--primary);
}

.submit-confirm {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--text);
}

.submit-stats {
  color: var(--text-2);
}
</style>
