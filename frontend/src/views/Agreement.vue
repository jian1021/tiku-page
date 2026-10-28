<script setup>
import TopBar from "@/components/TopBar.vue";

const updatedAt = "2026-10-28";

const sections = [
  {
    title: "一、服务说明",
    paragraphs: [
      "「专家库入库考试助手」为政府采购评审专家入库考试提供在线练习、模拟考试与法规查询等备考工具，题库内容仅供学习参考，不代表任何官方考试范围或命题口径。",
      "本服务为民办备考工具，与各级政府主管部门、公共资源交易机构无隶属或授权关系。",
    ],
  },
  {
    title: "二、账号与安全",
    paragraphs: [
      "你需使用有效手机号注册账号，并妥善保管密码。因个人保管不善导致的账号被他人使用，由账号持有人承担相应后果。",
      "同一账号仅限本人使用，不得出租、出借、转让或用于代考等违规行为。",
    ],
  },
  {
    title: "三、会员与激活码",
    paragraphs: [
      "部分功能（全部题目练习、模拟考试等）需激活会员后使用。激活码一次使用即失效，激活后有效期按激活码标注天数计算。",
      "会员到期后，账号内的答题记录、错题本与收藏仍会保留，但会员专属功能将暂停使用。",
      "激活码属于虚拟商品，一经使用不支持退换；如遇激活异常，请通过服务页联系方式反馈。",
    ],
  },
  {
    title: "四、内容与知识产权",
    paragraphs: [
      "题库解析、页面设计、程序代码等由本平台整理或开发，未经许可不得批量抓取、复制、转载或用于商业用途。",
      "法规条文依据公开发布的官方文本整理，如与官方文本不一致，以官方发布文本为准。",
    ],
  },
  {
    title: "五、使用规范",
    paragraphs: [
      "禁止利用本服务从事任何违法违规活动，包括但不限于攻击服务、绕过权限、批量注册、恶意刷题影响系统稳定等。",
      "如发现题目或解析存在错误，欢迎通过意见反馈告知，我们将核实后修正。",
    ],
  },
  {
    title: "六、免责声明",
    paragraphs: [
      "考试结果受个人基础、复习程度与当年命题等多重因素影响，本平台不对考试通过作出任何承诺。",
      "因网络故障、设备异常、不可抗力等导致的服务中断，我们将尽力恢复，但不承担由此产生的间接损失。",
    ],
  },
  {
    title: "七、协议变更",
    paragraphs: [
      "本协议可能随功能调整而更新，更新后将在本页面公布。继续使用本服务即视为接受更新后的协议内容。",
    ],
  },
];
</script>

<template>
  <div class="page">
    <TopBar title="用户协议" />

    <section class="card intro">
      <h1 class="doc-title">用户协议</h1>
      <p class="doc-meta">更新日期：{{ updatedAt }}　生效日期：{{ updatedAt }}</p>
      <p class="doc-lead">
        欢迎使用「专家库入库考试助手」。在使用本服务前，请认真阅读并理解以下条款；你开始使用本服务，即表示已同意本协议全部内容。
      </p>
    </section>

    <section v-for="section in sections" :key="section.title" class="card section">
      <h2 class="section-title">{{ section.title }}</h2>
      <p v-for="(text, index) in section.paragraphs" :key="index" class="paragraph">{{ text }}</p>
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

.paragraph {
  color: var(--text);
  line-height: 1.85;
}
</style>
