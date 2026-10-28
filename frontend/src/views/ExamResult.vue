<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getExamResult } from "@/api/exams";
import TopBar from "@/components/TopBar.vue";
import Skeleton from "@/components/Skeleton.vue";
import Empty from "@/components/Empty.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import { showToast } from "@/composables/useToast";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const payload = ref(null);

const exam = computed(() => payload.value?.exam || null);
const chapters = computed(() => payload.value?.chapters || []);
const wrongItems = computed(() => payload.value?.wrong_items || []);

const accuracy = computed(() => {
  if (!exam.value?.total) return 0;
  const wrongCount = wrongItems.value.length;
  return Math.round(((exam.value.total - wrongCount) / exam.value.total) * 100);
});

const usedText = computed(() => {
  const seconds = exam.value?.used_seconds || 0;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m} 分 ${s} 秒` : `${s} 秒`;
});

async function load() {
  loading.value = true;
  try {
    payload.value = await getExamResult(route.params.id);
  } catch (error) {
    showToast(error?.message || "加载考试结果失败", "error");
  } finally {
    loading.value = false;
  }
}

function retry() {
  router.replace("/exam");
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="考试结果" />

    <Skeleton v-if="loading" :rows="4" />

    <Empty v-else-if="!exam" text="暂无考试结果" sub="该场考试可能尚未交卷">
      <button class="btn btn-primary" type="button" @click="router.replace('/exam')">返回考试页</button>
    </Empty>

    <template v-else>
      <section class="score-card card">
        <div class="score-main" :class="exam.passed ? 'pass' : 'fail'">
          <span class="score-value">{{ exam.score ?? 0 }}</span>
          <span class="score-total">/ {{ exam.total_score ?? 100 }} 分</span>
        </div>
        <span class="score-badge" :class="exam.passed ? 'pass' : 'fail'">
          {{ exam.passed ? "已通过" : "未通过" }}
        </span>
        <dl class="score-meta">
          <div><dt>及格线</dt><dd>{{ exam.pass_score ?? "-" }}</dd></div>
          <div><dt>题量</dt><dd>{{ exam.total }}</dd></div>
          <div><dt>正确率</dt><dd>{{ accuracy }}%</dd></div>
          <div><dt>用时</dt><dd>{{ usedText }}</dd></div>
        </dl>
      </section>

      <section class="block card">
        <h2 class="block-title">各章节正确率</h2>
        <Empty v-if="chapters.length === 0" text="暂无章节统计" />
        <div v-else class="chapter-list">
          <div v-for="item in chapters" :key="item.chapter_id ?? 'unknown'" class="chapter-row">
            <div class="chapter-head">
              <span class="chapter-name">{{ item.chapter_name }}</span>
              <span class="chapter-value">{{ item.correct }}/{{ item.total }} · {{ item.accuracy }}%</span>
            </div>
            <ProgressBar :value="item.accuracy" />
          </div>
        </div>
      </section>

      <section class="block">
        <h2 class="block-title">错题解析（{{ wrongItems.length }}）</h2>
        <Empty v-if="wrongItems.length === 0" text="本次全部答对" sub="继续保持" />
        <div v-else class="wrong-list">
          <article v-for="item in wrongItems" :key="item.question.id" class="wrong-item card">
            <div class="wrong-tags">
              <span class="tag tag-status-danger">答错</span>
              <span v-if="item.question.chapter_name" class="tag">{{ item.question.chapter_name }}</span>
            </div>
            <p class="wrong-stem">{{ item.question.stem }}</p>
            <p class="wrong-answer">
              你的答案：<strong>{{ (item.selected || []).join("、") || "未作答" }}</strong>
            </p>
            <p class="wrong-correct">
              正确答案：<strong>{{ (item.question.correct_answer || []).join("、") }}</strong>
            </p>
            <p v-if="item.question.explanation" class="wrong-explain">{{ item.question.explanation }}</p>
          </article>
        </div>
      </section>

      <div class="actions">
        <button class="btn" type="button" @click="router.push('/')">返回练习</button>
        <button class="btn btn-primary" type="button" @click="retry">再考一次</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 24px 16px;
}

.score-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.score-value {
  font-size: 2.8rem;
  font-weight: 700;
  line-height: 1;
}

.score-main.pass .score-value {
  color: var(--success);
}

.score-main.fail .score-value {
  color: var(--danger);
}

.score-total {
  color: var(--text-2);
}

.score-badge {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: var(--fs-sm);
  font-weight: 600;
}

.score-badge.pass {
  background: var(--success-soft);
  color: var(--success);
}

.score-badge.fail {
  background: var(--danger-soft);
  color: var(--danger);
}

.score-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  width: 100%;
  margin: 8px 0 0;
  text-align: center;
}

.score-meta dt {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.score-meta dd {
  margin: 2px 0 0;
  font-weight: 600;
}

.block {
  margin-bottom: 14px;
}

.block-title {
  margin-bottom: 10px;
  font-size: 1.05rem;
  font-weight: 600;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chapter-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.chapter-name {
  color: var(--text);
}

.chapter-value {
  color: var(--text-2);
  font-size: var(--fs-xs);
  white-space: nowrap;
}

.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wrong-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.wrong-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.wrong-stem {
  line-height: 1.65;
}

.wrong-answer,
.wrong-correct {
  font-size: var(--fs-sm);
  color: var(--text-2);
}

.wrong-correct strong {
  color: var(--success);
}

.wrong-explain {
  padding: 10px 12px;
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.7;
  white-space: pre-wrap;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.actions .btn {
  flex: 1;
}
</style>
