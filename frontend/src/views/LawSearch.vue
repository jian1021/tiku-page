<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { searchLaws } from "@/api/laws";
import { useUiStore } from "@/stores/ui";
import { useAuthStore } from "@/stores/auth";
import TopBar from "@/components/TopBar.vue";
import Empty from "@/components/Empty.vue";
import Skeleton from "@/components/Skeleton.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const auth = useAuthStore();

const keyword = ref(typeof route.query.q === "string" ? route.query.q : "");
const loading = ref(false);
const searched = ref(false);
const hits = ref([]);

const provinceCode = computed(() => {
  if (auth.isLoggedIn && auth.user?.province_code) return auth.user.province_code;
  return ui.provinceCode || "SC";
});

/** 按法规文档聚合命中条目，便于分组展示。 */
const groups = computed(() => {
  const map = new Map();
  for (const hit of hits.value) {
    const id = hit.document?.id;
    if (!map.has(id)) {
      map.set(id, { document: hit.document, items: [] });
    }
    map.get(id).items.push(hit);
  }
  return [...map.values()];
});

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** 高亮关键词；未匹配时原样返回。 */
function highlight(text) {
  if (!keyword.value || !text) return text;
  const regex = new RegExp(escapeRegExp(keyword.value), "gi");
  return text.replace(regex, (match) => `<mark class="hl">${match}</mark>`);
}

/** 截取命中位置附近的片段，避免整条法条过长。 */
function snippet(hit) {
  const content = hit.article?.content || "";
  const pos = Array.isArray(hit.positions) && hit.positions.length ? hit.positions[0] : -1;
  if (pos < 0 || content.length <= 120) return highlight(content);
  const start = Math.max(0, pos - 30);
  const end = Math.min(content.length, pos + 90);
  const prefix = start > 0 ? "…" : "";
  const suffix = end < content.length ? "…" : "";
  return prefix + highlight(content.slice(start, end)) + suffix;
}

async function search() {
  const text = keyword.value.trim();
  if (!text) {
    showToast("请输入搜索关键词", "info");
    return;
  }
  loading.value = true;
  searched.value = true;
  try {
    const data = await searchLaws(text, provinceCode.value);
    hits.value = Array.isArray(data?.hits) ? data.hits : [];
  } catch (error) {
    hits.value = [];
    showToast(error?.message || "搜索失败", "error");
  } finally {
    loading.value = false;
  }
}

function openArticle(hit) {
  const documentId = hit.document?.id;
  if (!documentId) return;
  router.push({
    path: `/law/${documentId}`,
    query: { article_id: hit.article?.id, q: keyword.value },
  });
}

onMounted(() => {
  if (keyword.value) search();
});
</script>

<template>
  <div class="page">
    <TopBar title="法规搜索" />

    <div class="search-box">
      <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path v-for="d in ICONS.search" :key="d" :d="d" />
      </svg>
      <input
        v-model="keyword"
        class="search-input"
        type="search"
        placeholder="输入法规名称或条文关键词"
        @keyup.enter="search"
      />
      <button class="search-btn" type="button" @click="search">搜索</button>
    </div>

    <Skeleton v-if="loading" :rows="3" />

    <template v-else>
      <p v-if="searched && hits.length" class="result-info">
        共匹配 {{ hits.length }} 条，涉及 {{ groups.length }} 部法规
      </p>

      <Empty v-if="!searched" text="输入关键词开始搜索" sub="支持法规标题与条文全文检索" />
      <Empty v-else-if="hits.length === 0" text="未找到相关法规" sub="换个关键词试试" />

      <div v-else class="groups">
        <section v-for="group in groups" :key="group.document.id" class="group">
          <button class="group-title" type="button" @click="router.push(`/law/${group.document.id}`)">
            {{ group.document.title }}
            <span class="group-tag">{{ group.items.length }} 条命中</span>
          </button>

          <button
            v-for="hit in group.items"
            :key="hit.article.id"
            class="hit-card card"
            type="button"
            @click="openArticle(hit)"
          >
            <div class="hit-head">
              <span class="hit-no">{{ hit.article.article_no || "条文" }}</span>
              <span v-if="hit.article.chapter_title" class="hit-chapter">{{ hit.article.chapter_title }}</span>
            </div>
            <p class="hit-content" v-html="snippet(hit)"></p>
          </button>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--card);
}

.search-icon {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  flex: none;
}

.search-input {
  flex: 1;
  min-height: 44px;
  border: none;
  background: transparent;
  color: var(--text);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-3);
}

.search-btn {
  min-height: 36px;
  padding: 0 14px;
  border: none;
  border-radius: 6px;
  background: var(--primary);
  color: var(--primary-contrast);
  cursor: pointer;
}

.result-info {
  margin-bottom: 12px;
  color: var(--text-2);
  font-size: var(--fs-sm);
}

.groups {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--primary);
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.group-tag {
  color: var(--text-3);
  font-size: var(--fs-xs);
  font-weight: 400;
}

.hit-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
}

.hit-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.hit-no {
  color: var(--text);
  font-weight: 600;
}

.hit-chapter {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.hit-content {
  color: var(--text-2);
  line-height: 1.7;
}

.hit-content :deep(.hl) {
  padding: 0 2px;
  border-radius: 3px;
  background: var(--highlight);
  color: var(--highlight-text);
}
</style>
