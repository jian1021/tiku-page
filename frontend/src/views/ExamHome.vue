<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { getExamConfig, getExamHistory, startExam } from "@/api/exams";
import TopBar from "@/components/TopBar.vue";
import Skeleton from "@/components/Skeleton.vue";
import Empty from "@/components/Empty.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();

const loading = ref(true);
const starting = ref(false);
const config = ref(null);
const history = ref([]);
const questionCount = ref(100);
const durationMinutes = ref(120);

const provinceCode = computed(() => {
  if (auth.isLoggedIn && auth.user?.province_code) return auth.user.province_code;
  return ui.provinceCode || "SC";
});

const configured = computed(() => Boolean(config.value?.configured));
const passLine = computed(() => config.value?.pass_score ?? "待配置");
const totalScore = computed(() => config.value?.total_score ?? "待配置");

async function load() {
  loading.value = true;
  try {
    const [cfg, hist] = await Promise.all([
      getExamConfig(provinceCode.value).catch(() => null),
      auth.isLoggedIn ? getExamHistory().catch(() => ({ items: [] })) : Promise.resolve({ items: [] }),
    ]);
    config.value = cfg;
    history.value = Array.isArray(hist) ? hist : hist?.items || [];

    if (cfg?.question_count) questionCount.value = cfg.question_count;
    if (cfg?.duration_minutes) durationMinutes.value = cfg.duration_minutes;
    // 用户上次的自定义设置优先
    const savedCount = cfg?.user_settings?.exam_question_count;
    const savedDuration = cfg?.user_settings?.exam_duration_minutes;
    if (savedCount) questionCount.value = savedCount;
    if (savedDuration) durationMinutes.value = savedDuration;
  } catch (error) {
    showToast(error?.message || "加载考试配置失败", "error");
  } finally {
    loading.value = false;
  }
}

async function start() {
  if (!auth.isLoggedIn) {
    router.push({ name: "Login", query: { redirect: "/exam" } });
    return;
  }
  if (!auth.isMember) {
    showToast("模拟考试仅会员可参加，请先激活", "warning");
    router.push("/me");
    return;
  }
  if (!configured.value) {
    showToast("管理员尚未配置本省考试参数", "warning");
    return;
  }

  starting.value = true;
  try {
    const res = await startExam({
      question_count: Number(questionCount.value),
      duration_minutes: Number(durationMinutes.value),
    });
    const examId = res?.id || res?.exam_id;
    if (!examId) throw new Error("考试创建失败");

    // 记住本次自定义题量/时长，下次进入自动带出
    try {
      await auth.updateSettings({
        settings: {
          exam_question_count: Number(questionCount.value),
          exam_duration_minutes: Number(durationMinutes.value),
        },
      });
    } catch {
      // 保存失败不影响考试
    }

    router.push({ path: "/exam/run", query: { id: examId } });
  } catch (error) {
    const detail = String(error?.detail || error?.message || "");
    if (error?.response?.status === 403 || detail.includes("会员")) {
      showToast("模拟考试仅会员可参加", "warning");
      router.push("/me");
    } else if (error?.response?.status === 400 && detail.includes("配置")) {
      showToast("管理员尚未配置本省考试参数", "warning");
    } else {
      showToast(error?.message || "开始考试失败", "error");
    }
  } finally {
    starting.value = false;
  }
}

function openResult(id) {
  router.push(`/exam/result/${id}`);
}

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("zh-CN", { hour12: false });
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="模拟考试" :back="false" />

    <Skeleton v-if="loading" :rows="4" />

    <template v-else>
      <section class="intro card">
        <div class="intro-head">
          <span class="intro-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.exam" :key="d" :d="d" />
            </svg>
          </span>
          <div class="intro-text">
            <h2>全真模拟考试</h2>
            <p>按考试规则随机抽题，交卷后给出章节正确率与错题解析。</p>
          </div>
        </div>

        <dl class="meta">
          <div class="meta-item">
            <dt>题量</dt>
            <dd>{{ config?.question_count ?? "待配置" }}</dd>
          </div>
          <div class="meta-item">
            <dt>时长</dt>
            <dd>{{ config?.duration_minutes ?? "待配置" }} 分钟</dd>
          </div>
          <div class="meta-item">
            <dt>及格线</dt>
            <dd>{{ passLine }}</dd>
          </div>
          <div class="meta-item">
            <dt>总分</dt>
            <dd>{{ totalScore }}</dd>
          </div>
        </dl>

        <p v-if="!configured" class="warn">
          本省考试参数尚未配置，暂时无法开始考试，请联系管理员。
        </p>
        <p v-else-if="!auth.isMember" class="warn">
          模拟考试为会员功能，激活后即可参加。
        </p>
      </section>

      <section v-if="configured" class="settings card">
        <h3 class="settings-title">本次设置</h3>
        <label class="row">
          <span>题量</span>
          <input v-model.number="questionCount" type="number" min="10" :max="config?.available_questions || 200" />
        </label>
        <label class="row">
          <span>时长（分钟）</span>
          <input v-model.number="durationMinutes" type="number" min="10" max="300" />
        </label>
        <p class="hint">可选题量上限 {{ config?.available_questions ?? 0 }} 题</p>
      </section>

      <button class="btn btn-primary btn-block start-btn" type="button" :disabled="starting" @click="start">
        {{ starting ? "正在生成试卷" : auth.isMember ? "开始考试" : "激活会员后参加" }}
      </button>

      <section class="history">
        <div class="history-head">
          <h3>历史成绩</h3>
          <span v-if="history.length" class="history-total">{{ history.length }} 次</span>
        </div>

        <Empty
          v-if="history.length === 0"
          :text="auth.isLoggedIn ? '暂无考试记录' : '登录后可查看考试记录'"
          :sub="auth.isLoggedIn ? '完成一次模拟考试后会显示在这里' : ''"
        />

        <button
          v-for="item in history"
          :key="item.id"
          class="history-item card"
          type="button"
          @click="openResult(item.id)"
        >
          <div class="history-main">
            <span class="history-date">{{ formatTime(item.started_at) }}</span>
            <span class="history-score">得分 {{ item.score ?? 0 }} · 用时 {{ Math.round((item.used_seconds || 0) / 60) }} 分钟</span>
          </div>
          <span class="tag" :class="item.passed ? 'tag-status-ok' : 'tag-status-danger'">
            {{ item.passed ? "及格" : "未及格" }}
          </span>
          <svg class="history-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in ICONS.chevronRight" :key="d" :d="d" />
          </svg>
        </button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 12px;
}

.intro-head {
  display: flex;
  gap: 12px;
  align-items: center;
}

.intro-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--primary-soft);
  color: var(--primary);
  flex: none;
}

.intro-icon svg {
  width: 24px;
  height: 24px;
}

.intro-text h2 {
  font-size: 1.1rem;
  font-weight: 600;
}

.intro-text p {
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--radius);
  background: var(--bg);
}

.meta-item dt {
  color: var(--text-2);
  font-size: var(--fs-xs);
}

.meta-item dd {
  margin: 0;
  font-weight: 600;
}

.warn {
  padding: 10px 12px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  font-size: var(--fs-sm);
}

.settings {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.settings-title {
  font-size: 1rem;
  font-weight: 600;
}

.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.row input {
  width: 110px;
  min-height: 40px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  text-align: center;
}

.hint {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.start-btn {
  margin-bottom: 22px;
}

.history {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.history-head h3 {
  font-size: 1.05rem;
  font-weight: 600;
}

.history-total {
  color: var(--text-2);
  font-size: var(--fs-xs);
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
}

.history-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-date {
  color: var(--text);
  font-size: var(--fs-sm);
}

.history-score {
  color: var(--text-2);
  font-size: var(--fs-xs);
}

.history-arrow {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  flex: none;
}
</style>
