import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

// 页面按需加载，首屏只加载首页
const HomePage = () => import("@/views/Home.vue");
const ChapterPage = () => import("@/views/Chapter.vue");
const QuizPage = () => import("@/views/Quiz.vue");
const QuizCardPage = () => import("@/views/QuizCard.vue");
const WrongPage = () => import("@/views/Wrong.vue");
const FavoritesPage = () => import("@/views/Favorites.vue");
const LawListPage = () => import("@/views/LawList.vue");
const LawSearchPage = () => import("@/views/LawSearch.vue");
const LawDetailPage = () => import("@/views/LawDetail.vue");
const ExamHomePage = () => import("@/views/ExamHome.vue");
const ExamRunPage = () => import("@/views/ExamRun.vue");
const ExamResultPage = () => import("@/views/ExamResult.vue");
const ServicePage = () => import("@/views/Service.vue");
const ProfilePage = () => import("@/views/Me.vue");
const AgreementPage = () => import("@/views/Agreement.vue");
const PrivacyPage = () => import("@/views/Privacy.vue");
const LoginPage = () => import("@/auth/LoginPage.vue");
const RegisterPage = () => import("@/auth/RegisterPage.vue");

const routes = [
  { path: "/", name: "Practice", component: HomePage, meta: { title: "练习", tab: true } },
  { path: "/chapter/:id", name: "ChapterDetail", component: ChapterPage, meta: { title: "章节练习" } },
  { path: "/quiz", name: "Quiz", component: QuizPage, meta: { title: "答题" } },
  { path: "/quiz/card", name: "QuizCard", component: QuizCardPage, meta: { title: "答题卡" } },
  { path: "/wrong", name: "WrongBook", component: WrongPage, meta: { title: "错题本", requiresAuth: true } },
  { path: "/favorites", name: "Favorites", component: FavoritesPage, meta: { title: "我的收藏", requiresAuth: true } },
  { path: "/law", name: "LawList", component: LawListPage, meta: { title: "法规库" } },
  // 搜索页必须早于 /law/:id，否则会被详情路由吞掉
  { path: "/law/search", name: "LawSearch", component: LawSearchPage, meta: { title: "法规搜索" } },
  { path: "/law/:id", name: "LawDetail", component: LawDetailPage, meta: { title: "法规详情" } },
  { path: "/exam", name: "ExamHome", component: ExamHomePage, meta: { title: "模拟考试", tab: true } },
  { path: "/exam/run", name: "ExamRun", component: ExamRunPage, meta: { title: "考试中", requiresAuth: true } },
  { path: "/exam/result/:id", name: "ExamResult", component: ExamResultPage, meta: { title: "考试结果", requiresAuth: true } },
  { path: "/service", name: "Service", component: ServicePage, meta: { title: "服务", tab: true } },
  { path: "/me", name: "Profile", component: ProfilePage, meta: { title: "我的", tab: true } },
  { path: "/agreement", name: "Agreement", component: AgreementPage, meta: { title: "用户协议" } },
  { path: "/privacy", name: "Privacy", component: PrivacyPage, meta: { title: "隐私政策" } },
  { path: "/login", name: "Login", component: LoginPage, meta: { title: "登录", guestOnly: true } },
  { path: "/register", name: "Register", component: RegisterPage, meta: { title: "注册", guestOnly: true } },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  const auth = useAuthStore();

  // 已登录用户不再回到登录/注册页
  if (to.meta?.guestOnly && auth.isLoggedIn) {
    const redirect = typeof to.query.redirect === "string" ? to.query.redirect : "/";
    return { path: redirect };
  }

  // 需要登录的页面统一跳转登录，并记录来源地址
  if (to.meta?.requiresAuth && !auth.isLoggedIn) {
    return { name: "Login", query: { redirect: to.fullPath } };
  }

  return true;
});

router.afterEach((to) => {
  const base = "专家库入库考试助手";
  document.title = to.meta?.title ? `${to.meta.title} · ${base}` : base;
});

export default router;
