<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getFavorites, removeFavorite } from "@/api/favorites";
import TopBar from "@/components/TopBar.vue";
import Empty from "@/components/Empty.vue";
import Skeleton from "@/components/Skeleton.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();

const tab = ref("question");
const loading = ref(true);
const questionItems = ref([]);
const lawItems = ref([]);
const busy = ref(null);

async function load() {
  loading.value = true;
  try {
    const [questionData, lawData] = await Promise.all([
      getFavorites("question").catch(() => ({ items: [] })),
      getFavorites("law_article").catch(() => ({ items: [] })),
    ]);
    questionItems.value = (questionData?.items || []).filter((item) => item.question);
    lawItems.value = (lawData?.items || []).filter((item) => item.law_article);
  } catch (error) {
    showToast(error?.message || "加载收藏失败", "error");
  } finally {
    loading.value = false;
  }
}

async function remove(type, item) {
  if (busy.value) return;
  busy.value = item.id;
  try {
    await removeFavorite(type, item.target_id);
    if (type === "question") {
      questionItems.value = questionItems.value.filter((row) => row.id !== item.id);
    } else {
      lawItems.value = lawItems.value.filter((row) => row.id !== item.id);
    }
    showToast("已取消收藏", "success");
  } catch (error) {
    showToast(error?.message || "操作失败", "error");
  } finally {
    busy.value = null;
  }
}

function practiceQuestion(item) {
  const question = item.question;
  if (question.chapter_id) {
    router.push({
      path: "/quiz",
      query: { chapter_id: question.chapter_id, mode: "practice", favorite_id: question.id },
    });
  } else {
    showToast("该题目所属章节已删除", "warning");
  }
}

function openArticle(item) {
  const documentId = item.law_document?.id;
  if (!documentId) {
    showToast("法规原文不存在", "warning");
    return;
  }
  router.push({ path: `/law/${documentId}`, query: { article_id: item.law_article.id } });
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("zh-CN");
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="我的收藏" right-text="错题本" @right="router.push('/wrong')" />

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'question' }" type="button" @click="tab = 'question'">
        题目 {{ questionItems.length }}
      </button>
      <button class="tab" :class="{ active: tab === 'law' }" type="button" @click="tab = 'law'">
        法规条文 {{ lawItems.length }}
      </button>
    </div>

    <Skeleton v-if="loading" :rows="3" />

    <template v-else>
      <div v-if="tab === 'question'">
        <Empty v-if="questionItems.length === 0" text="暂无题目收藏" sub="练习时点击收藏按钮即可加入" />
        <div v-else class="list">
          <article v-for="item in questionItems" :key="item.id" class="row card">
            <button class="row-main" type="button" @click="practiceQuestion(item)">
              <div class="row-tags">
                <span v-if="item.question.year" class="tag tag-year">{{ item.question.year }}</span>
                <span class="tag">{{ item.question.chapter_name || "未分类" }}</span>
              </div>
              <p class="row-text">{{ item.question.stem }}</p>
            </button>
            <button class="row-remove" type="button" aria-label="取消收藏" :disabled="busy === item.id" @click="remove('question', item)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path v-for="d in ICONS.star" :key="d" :d="d" />
              </svg>
            </button>
          </article>
        </div>
      </div>

      <div v-else>
        <Empty v-if="lawItems.length === 0" text="暂无法规条文收藏" sub="在法规详情页点击星标即可收藏条文" />
        <div v-else class="list">
          <article v-for="item in lawItems" :key="item.id" class="row card">
            <button class="row-main" type="button" @click="openArticle(item)">
              <div class="row-tags">
                <span class="tag">{{ item.law_article.article_no || "条文" }}</span>
                <span class="tag tag-status-ok">{{ item.law_document?.title }}</span>
              </div>
              <p class="row-text">{{ item.law_article.content }}</p>
              <span v-if="formatDate(item.law_document?.publish_date)" class="row-meta">
                发布日期：{{ formatDate(item.law_document.publish_date) }}
              </span>
            </button>
            <button class="row-remove" type="button" aria-label="取消收藏" :disabled="busy === item.id" @click="remove('law_article', item)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path v-for="d in ICONS.star" :key="d" :d="d" />
              </svg>
            </button>
          </article>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 6px;
  padding: 4px;
  margin-bottom: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
}

.tab {
  flex: 1;
  min-height: 40px;
  border: none;
  border-radius: calc(var(--radius) - 2px);
  background: transparent;
  color: var(--text-2);
  font-weight: 600;
  cursor: pointer;
}

.tab.active {
  background: var(--card);
  color: var(--primary);
  box-shadow: var(--shadow);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 8px 12px 14px;
}

.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: none;
  background: transparent;
  text-align: left;
  color: var(--text);
  cursor: pointer;
}

.row-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.row-text {
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-meta {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.row-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  flex: none;
}

.row-remove svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}
</style>
