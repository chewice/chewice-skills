export const defaultTask = `从 Phase 1 开始导师匹配。

Phase 1 启动前只检查：
1. 已填写目标学校或目标范围
2. 已上传可读取的真实 CV

目标学位和申请季可以稍后补充，但进入客观申请条件筛选前必须齐全。
研究兴趣和权重是可选补充；没有权重时按等权处理。
严格保留每条关键结论的来源。`;

export function buildPhaseOneTaskPrompt({ project, filePath = "" }) {
  if (project?.domainProfile === "medical") return `使用 Boss Hunting 的生物医学 ${project.searchMode || "discovery"} 模式。
复用已保存研究画像 ${JSON.stringify(project.medicalProfile || {})}；只补缺失信息，按 领域 → 疾病/机制/科学问题 → 目标地区 三步推进，研究对象/尺度/范式/方法偏好为可选。
地区：${project.target || "尚未询问"}；目标数量：${project.shortlistTarget || 10}。
流程：科学问题 → Map/Research Seeds → PI 识别与验证（Level A–D）→ 近五年回查 → 合作网络扩展（≤2 轮，collaboration edge 与 research-neighbor edge 分开）→ 饱和 → shortlist（展示顺序）。
探索不读取 CV、成绩或申请者能力；申请筛选才使用真实背景，未知资格保持待确认。
以五维证据画像（研究问题契合 / 主线连续性 / PI 角色置信 / 证据充分度 / 当前活跃度）比较，不计算综合分、引用量排名或 reach 配额；不评估训练匹配、资源、博士资助或培养环境。未映射真实项目的导师保存在 advisor_records 中；深查仍需精确目标和五模块维度确认。凭据只报告状态词，不得输出 key 值。`;
  const interests = project?.interests?.length
    ? project.interests
        .map((interest) => `${interest.name} ${interest.weight}%`)
        .join("，")
    : "未提供；请以 CV 为主要匹配信号";
  const strategy = {
    balanced: "均衡：保留少量冲刺，并以主申和相对稳妥选择为主体",
    conservative: "稳妥优先：压低冲刺比例，优先当前履历更有现实机会的项目",
    ambitious: "冲刺优先：允许更多高门槛项目，但仍保留可申请的主申选择",
  }[project?.portfolioStrategy || "balanced"];
  const hardConstraints = String(project?.hardConstraints || "").trim() || "未提供；不得自行添加隐含门槛";

  return `${defaultTask}

当前已保存的 Phase 1 输入：
- CV：${project?.cv?.path || filePath || "未上传"}
- 申请目标：${project?.target || "未填写"}
- 目标学位与申请季：${project?.degree || "未填写"} · ${project?.season || "未填写"}
- 必须满足的硬条件：${hardConstraints}
- 研究兴趣权重：${interests}
- shortlist：Top ${project?.shortlistTarget || 10}
- 申请组合策略：${strategy}

仅调查目标范围内的导师。先识别申请路径，再核验硬条件，然后分别判断研究相似度、履历匹配和机会证据；除非用户明确要求全冲刺，不要让 reach 候选占据 shortlist 多数。Phase 1 不检索社区风评或其他 Phase 2 信息；优先复用同一官方页面中的项目与申请条件，避免重复搜索。`;
}

export function buildInvestigationTaskPrompt() {
  return "开始 Phase 2：按当前项目已确认的精确导师—项目组合、调查维度与社区资料授权执行背调。";
}

export function buildRankingTaskPrompt(project) {
  if (project?.domainProfile === "medical") return "使用已有真实候选与已确认的五模块调查生成生物医学五维证据画像比较、HTML 报告及 Excel；展示顺序不是质量排名，不生成综合分、引用量排名或录取概率。";
  return "使用当前项目已有的真实候选导师、客观条件与已确认背调证据生成最终排名。";
}

export function buildApplicationMaterialTaskPrompt(mode) {
  if (mode === "research_proposal") {
    return "为当前项目已确认的精确导师—项目目标生成 Research Proposal 与可核验文献包。";
  }
  if (mode === "outreach_email") {
    return "为当前项目已确认的精确导师—项目目标生成一封可复制的陶瓷信与引用审计。";
  }
  throw new Error(`未知申请材料模式：${mode}`);
}
