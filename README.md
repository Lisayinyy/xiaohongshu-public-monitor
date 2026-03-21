# 小红书舆论监控 Skill v2.0

自动监控小红书帖子 → 深入详情页抓取 → 智能筛选 → 生成高质量评论话术 → 写入飞书多维表格。

适用于任何行业：AI、电商、美妆、餐饮、教育……只需修改 `config.yaml` 即可适配。

## ✨ v2.0 新特性

- 🔍 **详情页深入抓取** — 不只看标题，进入每篇帖子抓取正文、图片、评论
- 🧠 **3 层评论打磨流水线** — 真人风格学习 → 两轮去AI味 → 8 项质量检查
- 🔄 **自进化闭环** — 不合格评论自动分析原因、提取规则，越用越强
- 📊 **相对排名制紧急程度** — 跨行业通用，永远保证 1/3 高、1/3 中、1/3 低
- 📝 **审核员反馈学习** — 从人工调整中提取规则，持续优化判定逻辑

## 🚀 快速开始

### 1. 安装

```bash
# Via ClawHub
clawdhub install xiaohongshu-public-monitor

# 手动安装
git clone https://github.com/Lisayinyy/xiaohongshu-public-monitor.git ~/.openclaw/skills/xiaohongshu-public-monitor
```

### 2. 安装依赖 Skill

本 Skill 依赖以下 Skill 实现评论打磨：

```bash
clawdhub install humanize-zh
clawdhub install elatia-humanizer-zh
clawdhub install writing-style-iterator
```

### 3. 配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入：
- 你的品牌名和产品
- 搜索关键词（3-5 个）
- 飞书多维表格 token
- 3 个评论人设
- 竞品列表

### 4. 运行

告诉 Agent：`执行小红书舆情监控`

## 📋 工作流程

```
Step 1：搜索列表页（内置浏览器 + 滚动翻页）
    ↓
Step 2：去重（对比飞书表格已有链接）
    ↓
Step 3：详情页深入抓取（正文 + 图片 + 评论 + 互动数据）
    ↓
Step 4：内容质量筛选
    ↓
Step 5：评论生成（3 层打磨）
    5a. 学习真人评论风格
    5b. 三人设生成初稿
    5c. 两轮去AI味（humanize-zh + elatia-humanizer-zh）
    5d. 8 项质量检查 → 不通过则自进化重写
    5e. 紧急程度判定（相对排名制）
    ↓
Step 6：写入飞书多维表格
```

## 📊 紧急程度判定

采用**相对排名制**，不依赖绝对阈值，跨行业通用：

- 每条帖子按**威胁度**（60%）和**传播力**（40%）打分
- 传播力用本批次内的相对排名，不用绝对点赞数
- 按综合分排序，前 1/3 → 🔴高，中 1/3 → 🟡中，后 1/3 → 🟢低

## 🧹 评论去AI味

3 层打磨确保评论像真人写的：

| 层级 | Skill | 作用 |
|------|-------|------|
| 第 1 层 | writing-style-iterator | 从真人评论中学习风格，越用越像 |
| 第 2 层 | humanize-zh | 中文口语化（替换 AI 连接词、加入口语元素） |
| 第 3 层 | elatia-humanizer-zh | 深度扫描 10 种 AI 模式 |

## 📁 文件结构

```
xiaohongshu-public-monitor/
├── SKILL.md              # 使用说明
├── README.md             # 本文件
├── config.yaml           # 配置模板（用户填自己的）
├── config.example.yaml   # 示例配置（AI 行业）
├── .gitignore
├── scripts/
│   └── xhs_search.py     # Playwright 脚本（已弃用，保留参考）
├── references/
│   └── workflow.md        # 工作流说明
└── .learnings/
    ├── COMMENT_RULES.md   # 评论质量学习规则
    └── URGENCY_RULES.md   # 紧急程度学习规则
```

## 🤝 贡献

欢迎提 Issue 和 PR！

## 📄 License

MIT
