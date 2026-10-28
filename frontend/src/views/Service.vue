<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getSiteConfig, sendFeedback } from "@/api/questions";
import { useAuthStore } from "@/stores/auth";
import TopBar from "@/components/TopBar.vue";
import Skeleton from "@/components/Skeleton.vue";
import Empty from "@/components/Empty.vue";
import { showToast } from "@/composables/useToast";
import { ICONS } from "@/components/icons";

const router = useRouter();
const auth = useAuthStore();

const loading = ref(true);
const site = ref({});
const content = ref("");
const submitting = ref(false);
const openFaq = ref(0);

const faqs = [
  {
    q: "激活码怎么获取？",
    a: "激活码由平台运营方统一发放，可通过服务页的联系方式咨询。一个激活码仅可激活一次，激活后有效期从当前时间开始计算，未到期续费会顺延。",
  },
  {
    q: "非会员能做什么？",
    a: "非会员可以浏览法规库、查看章节结构和练习免费题目。激活会员后可练习全部题目、收藏题目与法规条文、参加模拟考试。",
  },
  {
    q: "换设备后学习记录还在吗？",
    a: "答题记录、错题本、收藏与考试成绩都保存在服务端，使用同一手机号登录即可恢复。练习中未提交的答题卡进度只保存在当前设备。",
  },
  {
    q: "题目或答案有误怎么办？",
    a: "请在下方意见反馈中说明章节与题干要点，我们会核对题库来源后更新。法规条文以官方发布文本为准。",
  },
];

const phone = computed(() => site.value.service_phone || "");
const wechat = computed(() => site.value.service_wechat || "");
const intro = computed(() => site.value.service_intro || "政府采购评审专家入库考试备考服务平台");

async function load() {
  loading.value = true;
  try {
    site.value = (await getSiteConfig()) || {};
  } catch (error) {
    showToast(error?.message || "加载服务信息失败", "error");
  } finally {
    loading.value = false;
  }
}

async function copy(text, label) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label}已复制`, "success");
  } catch {
    showToast("复制失败，请手动选择文本", "error");
  }
}

async function submit() {
  const text = content.value.trim();
  if (text.length < 5) {
    showToast("请至少填写 5 个字的反馈内容", "info");
    return;
  }
  if (text.length > 1024) {
    showToast("反馈内容不能超过 1024 字", "info");
    return;
  }

  submitting.value = true;
  try {
    await sendFeedback(text);
    content.value = "";
    showToast("反馈已提交，感谢你的建议", "success");
  } catch (error) {
    showToast(error?.message || "提交失败", "error");
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <TopBar title="服务" :back="false" />

    <Skeleton v-if="loading" :rows="2" />

    <template v-else>
      <section class="hero card">
        <h2 class="hero-title">备考服务</h2>
        <p class="hero-desc">{{ intro }}</p>
        <div class="hero-actions">
          <button class="btn btn-primary" type="button" @click="router.push('/exam')">模拟考试</button>
          <button class="btn" type="button" @click="router.push('/law')">法规库</button>
        </div>
      </section>

      <!-- 联系方式 -->
      <section class="contact card">
        <h3 class="block-title">联系我们</h3>

        <div v-if="!phone && !wechat" class="empty-contact">
          客服联系方式尚未配置，可在下方留言反馈。
        </div>

        <button v-if="phone" class="contact-row" type="button" @click="copy(phone, '客服电话')">
          <span class="contact-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.phone" :key="d" :d="d" />
            </svg>
          </span>
          <span class="contact-text">
            <span class="contact-label">客服电话</span>
            <span class="contact-value">{{ phone }}</span>
          </span>
          <span class="contact-copy">复制</span>
        </button>

        <button v-if="wechat" class="contact-row" type="button" @click="copy(wechat, '客服微信')">
          <span class="contact-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.wechat" :key="d" :d="d" />
            </svg>
          </span>
          <span class="contact-text">
            <span class="contact-label">客服微信</span>
            <span class="contact-value">{{ wechat }}</span>
          </span>
          <span class="contact-copy">复制</span>
        </button>
      </section>

      <!-- 意见反馈 -->
      <section class="feedback card">
        <h3 class="block-title">意见反馈</h3>
        <p class="block-desc">
          题目纠错、功能建议、激活问题都可以在这里留言{{ auth.isLoggedIn ? "" : "（未登录也可提交）" }}。
        </p>
        <textarea
          v-model="content"
          class="textarea"
          rows="4"
          maxlength="1024"
          placeholder="请描述你遇到的问题或建议，例如：第一章第 3 题答案有误……"
        ></textarea>
        <div class="feedback-foot">
          <span class="counter">{{ content.length }}/1024</span>
          <button class="btn btn-primary" type="button" :disabled="submitting" @click="submit">
            {{ submitting ? "提交中" : "提交反馈" }}
          </button>
        </div>
      </section>

      <!-- 常见问题 -->
      <section class="faq card">
        <h3 class="block-title">常见问题</h3>
        <div v-for="(item, index) in faqs" :key="item.q" class="faq-item">
          <button class="faq-q" type="button" @click="openFaq = openFaq === index ? -1 : index">
            <span>{{ item.q }}</span>
            <svg class="faq-arrow" :class="{ open: openFaq === index }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in ICONS.chevronDown" :key="d" :d="d" />
            </svg>
          </button>
          <p v-if="openFaq === index" class="faq-a">{{ item.a }}</p>
        </div>
      </section>

      <section class="links card">
        <button class="link" type="button" @click="router.push('/agreement')">用户协议</button>
        <button class="link" type="button" @click="router.push('/privacy')">隐私政策</button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.hero-title {
  font-size: 1.2rem;
  font-weight: 700;
}

.hero-desc {
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.hero-actions .btn {
  flex: 1;
}

.contact,
.feedback,
.faq,
.links {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.block-title {
  font-size: 1rem;
  font-weight: 600;
}

.block-desc {
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.6;
}

.empty-contact {
  padding: 12px;
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text-3);
  font-size: var(--fs-sm);
}

.contact-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.contact-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary-soft);
  color: var(--primary);
  flex: none;
}

.contact-icon svg {
  width: 18px;
  height: 18px;
}

.contact-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.contact-label {
  color: var(--text-2);
  font-size: var(--fs-xs);
}

.contact-value {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contact-copy {
  color: var(--primary);
  font-size: var(--fs-sm);
  font-weight: 600;
}

.textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  resize: vertical;
}

.feedback-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.counter {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.faq-item {
  border-top: 1px solid var(--border);
  padding-top: 10px;
}

.faq-item:first-of-type {
  border-top: none;
  padding-top: 0;
}

.faq-q {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text);
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.faq-q span {
  flex: 1;
}

.faq-arrow {
  width: 18px;
  height: 18px;
  color: var(--text-3);
  transition: transform 0.2s ease;
}

.faq-arrow.open {
  transform: rotate(180deg);
}

.faq-a {
  margin-top: 8px;
  color: var(--text-2);
  font-size: var(--fs-sm);
  line-height: 1.75;
}

.link {
  min-height: 44px;
  border: none;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.link:last-child {
  border-bottom: none;
}
</style>
