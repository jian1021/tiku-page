<script setup>
import TopBar from "@/components/TopBar.vue";

const updatedAt = "2026-10-28";

const sections = [
  {
    title: "一、我们收集的信息",
    items: [
      "账号信息：手机号、密码（仅保存加密后的哈希值，不保存明文）、昵称。",
      "学习信息：答题记录、错题本、收藏内容、模拟考试成绩与用时、省份设置。",
      "设备与日志信息：请求时间、接口路径、IP 地址，仅用于安全防护与故障排查。",
    ],
  },
  {
    title: "二、信息的使用目的",
    items: [
      "提供练习、判分、错题归集、成绩统计等核心功能。",
      "校验会员有效期，判断你可访问的题库范围。",
      "接口限流与异常访问识别，保障服务稳定。",
    ],
  },
  {
    title: "三、信息的存储与保护",
    items: [
      "数据存储于服务端数据库，密码使用 bcrypt 哈希算法单向加密存储。",
      "登录凭证采用签名令牌（JWT），有效期到期后需重新登录。",
      "我们不会以明文形式向任何第三方提供你的手机号与学习记录。",
    ],
  },
  {
    title: "四、本地存储的使用",
    items: [
      "浏览器本地保存登录令牌、主题与字号偏好、所选省份，用于免重复登录与界面还原。",
      "练习答题卡的临时进度保存在浏览器会话存储中，关闭标签页后自动清除。",
      "你可以通过浏览器设置清除本地数据，清除后需重新登录。",
    ],
  },
  {
    title: "五、信息共享",
    items: [
      "除法律法规要求、司法机关或行政机关依法调取外，我们不对外共享你的个人信息。",
      "本服务不接入第三方广告或用户画像 SDK。",
    ],
  },
  {
    title: "六、你的权利",
    items: [
      "你可以随时在「我的」页面修改昵称与省份偏好。",
      "如需注销账号或删除学习记录，可通过服务页联系方式提出，我们将在核实身份后处理。",
    ],
  },
  {
    title: "七、未成年人保护",
    items: [
      "本服务面向参加评审专家入库考试的成年考生。若你为未成年人，请在监护人指导下使用。",
    ],
  },
];
</script>

<template>
  <div class="page">
    <TopBar title="隐私政策" />

    <section class="card intro">
      <h1 class="doc-title">隐私政策</h1>
      <p class="doc-meta">更新日期：{{ updatedAt }}　生效日期：{{ updatedAt }}</p>
      <p class="doc-lead">
        我们重视你的个人信息保护。本政策说明「专家库入库考试助手」收集哪些信息、如何使用与保护这些信息，以及你可以行使的权利。
      </p>
    </section>

    <section v-for="section in sections" :key="section.title" class="card section">
      <h2 class="section-title">{{ section.title }}</h2>
      <ul class="list">
        <li v-for="(item, index) in section.items" :key="index" class="list-item">{{ item }}</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.intro,
.section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.doc-title {
  font-size: 1.3rem;
  font-weight: 700;
}

.doc-meta {
  color: var(--text-3);
  font-size: var(--fs-xs);
}

.doc-lead {
  color: var(--text-2);
  line-height: 1.8;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-item {
  position: relative;
  padding-left: 16px;
  color: var(--text);
  line-height: 1.8;
}

.list-item::before {
  content: "";
  position: absolute;
  top: 0.7em;
  left: 4px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--primary);
}
</style>
