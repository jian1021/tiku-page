<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getLaw } from "../api/laws";
import { addFavorite, removeFavorite, getFavorites } from "../api/favorites";
import { useAuthStore } from "../stores/auth";
import TopBar from "../components/TopBar.vue";
import Skeleton from "../components/Skeleton.vue";
import { showToast } from "../composables/useToast";
import { ICONS } from "../components/icons";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const loading = ref(true);
const law = ref(null);
const articles = ref([]);
const activeArticleId = ref(null);
const favoriteArticleIds = ref(new Set());

const lawTitle = computed(() => law.value?.title || "");

async function load() {
  loading.value = true;
  try {
    const data = await getLaw(route.params.id);
    law.value = data?.document || data || null;
    articles.value = Array.isArray(data?.articles) ? data.articles : [];
    // Sort by sort_order
    articles.value.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    // 收藏状态仅在登录后拉取（未登录调用会触发 401 从而清空令牌）
    if (auth.isLoggedIn) {
      try {
        const favs = await getFavorites("law_article");
        const items = Array.isArray(favs) ? favs : favs?.items || [];
        favoriteArticleIds.value = new Set(items.map((f) => String(f.target_id || f.id)));
      } catch (e) {
        // 收藏状态获取失败不影响正文阅读
      }
    }
    // Handle article_id from query
    if (route.query.article_id) {
      nextTick(() => {
        scrollToArticle(route.query.article_id);
      });
    }
  } catch (e) {
    showToast(e?.message || "加载失败", "error");
  } finally {
    loading.value = false;
  }
}

function scrollToArticle(articleId) {
  const el = document.getElementById(`article-${articleId}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    activeArticleId.value = String(articleId);
  }
}

async function toggleFavoriteArticle(article) {
  if (!auth.isLoggedIn) {
    showToast("登录后可收藏法规条文", "info");
    router.push({ name: "Login", query: { redirect: route.fullPath } });
    return;
  }

  const id = article.id;
  const fav = favoriteArticleIds.value.has(String(id));
  try {
    if (fav) {
      await removeFavorite("law_article", id);
      favoriteArticleIds.value.delete(String(id));
    } else {
      await addFavorite("law_article", id);
      favoriteArticleIds.value.add(String(id));
    }
    favoriteArticleIds.value = new Set(favoriteArticleIds.value);
  } catch (e) {
    showToast(e?.message || "操作失败", "error");
  }
}

function getStatusText(s) {
  if (s === "repealed") return "已废止";
  if (s === "revised") return "已修订";
  if (s === "effective") return "现行有效";
  return s || "";
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar :title="lawTitle" />
    <Skeleton v-if="loading" :rows="5" />
    <div v-else>
      <section class="law-info card">
        <div class="law-title">{{ law?.title }}</div>
        <div class="law-meta">
          <div class="meta-row">
            <span class="meta-label">效力状态：</span>
            <span class="tag" :class="law?.status === 'repealed' ? 'tag-status-danger' : law?.status === 'revised' ? 'tag-status-warn' : 'tag-status-ok'">
              {{ getStatusText(law?.status) }}
            </span>
          </div>
          <div v-if="law?.issuer" class="meta-row">
            <span class="meta-label">发文单位：</span>
            <span>{{ law.issuer }}</span>
          </div>
          <div v-if="law?.publish_date" class="meta-row">
            <span class="meta-label">发布日期：</span>
            <span>{{ law.publish_date }}</span>
          </div>
          <div v-if="law?.revise_date" class="meta-row">
            <span class="meta-label">修订日期：</span>
            <span>{{ law.revise_date }}</span>
          </div>
        </div>
      </section>

      <section class="catalog card">
        <div class="catalog-title">目录</div>
        <div class="catalog-list">
          <button
            v-for="article in articles"
            :key="article.id"
            class="catalog-item"
            :class="{ active: activeArticleId === String(article.id) }"
            type="button"
            @click="scrollToArticle(article.id)"
          >
            {{ article.article_no || article.title || `第${article.sort_order}条` }}
          </button>
        </div>
      </section>

      <section class="articles">
        <div
          v-for="article in articles"
          :key="article.id"
          :id="`article-${article.id}`"
          class="article-card card"
        >
          <div class="article-header">
            <div class="article-no">{{ article.article_no || `第${article.sort_order}条` }}</div>
            <button
              class="favorite-btn"
              :class="{ active: favoriteArticleIds.has(String(article.id)) }"
              type="button"
              @click="toggleFavoriteArticle(article)"
              aria-label="收藏"
            >
              <svg viewBox="0 0 24 24" :fill="favoriteArticleIds.has(String(article.id)) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path v-for="d in ICONS.star" :key="d" :d="d" />
              </svg>
            </button>
          </div>
          <div v-if="article.chapter_title" class="article-chapter">{{ article.chapter_title }}</div>
          <div class="article-content">{{ article.content }}</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.law-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.law-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  line-height: 1.6;
}

.law-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 0.95rem;
}

.meta-label {
  color: var(--text-2);
}

.catalog {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.catalog-title {
  font-weight: 600;
  color: var(--text);
}

.catalog-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.catalog-item {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}

.catalog-item.active {
  background: var(--primary-soft);
  border-color: var(--primary-border);
  color: var(--primary);
}

.articles {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.article-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.article-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.article-no {
  font-weight: 600;
  color: var(--primary);
}

.favorite-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
}

.favorite-btn svg {
  width: 20px;
  height: 20px;
}

.favorite-btn.active {
  color: var(--accent);
}

.article-chapter {
  font-weight: 600;
  color: var(--text);
}

.article-content {
  color: var(--text);
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
