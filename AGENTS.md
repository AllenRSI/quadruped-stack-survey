# 具身四足机器狗全栈算法方案调研

调研 2023-2026 年主流四足机器狗从「本体传感器 → 状态估计 → 地形感知 → 导航 → 运动控制 → 高层智能」的完整算法栈，产出一份可交付的深度报告 + 可视化网页。

**核心主张：四足全栈的主干已经从「MPC/WBC 手工建模」转为「GPU 万级并行 RL + teacher-student 蒸馏 + sim2real」；2025-2026 的新前沿不是替换运动层，而是把运动层当作 skill primitive，在上面叠 VLM/VLA 做长程任务——而这一层目前真机跑通的极少，宣传与落地之间存在巨大落差。**

目标：内部技术选型 + 新人入门材料（无投稿 deadline）

---

## 你（Agent）每次进来先读什么

1. **本文件** —— 知道我们在做什么、每个目录是干什么的
2. **[handoff.md](handoff.md)** —— 上一个窗口做到哪了、下一步是什么

**不要读完整个仓库再开始。** 上下文很贵，按需读。

---

## 目录

| 路径 | 是什么 | 什么时候看 |
|---|---|---|
| `调研/` | 分章节调研稿，01-04 由分线调研员产出，00 是总览 | 写报告、查细节时 |
| `related_work/` | 相关文献，每篇 `paper.pdf` + `source/` | 要引用、要对比方法时 |
| `复现/` | 重要 baseline 的复现，每个带一份复现报告 | 要确认 baseline 数字时 |
| `brainstorm.md` | 问题和假设是怎么聊出来的 | 想不通为什么这么设计时 |
| `handoff.md` | 进度交接 | **每次都读** |

最终交付：`report.md`（长文） + `index.html`（可视化网页）

---

## 读论文的规矩

`related_work/` 里每篇都是 `paper.pdf` + `source/`（LaTeX 源码），按要问什么选：

- 泛读（讲了什么、什么方法）→ `paper.pdf`
- 细查（表里的数、公式、引用）→ `source/*.tex`
- 看图 → 只能 `paper.pdf`，图不在源码里

用 `fetch-paper.ps1` 抓的源码已清洗过（旧稿在 `source/.stale/`，注释已剥、原文存 `.orig`）。
手动下的记得自己清一遍。宏多的论文先读 `commands.tex` / `macros.tex` 这类文件。


---

## 硬规矩

1. **不要自己发明术语。**用领域已有的词：convex MPC、WBC（whole-body control）、
   teacher-student distillation、domain randomization、sim2real gap、leg odometry、
   elevation mapping、costmap、traversability、skill primitive、VLA、VLN。
2. **每个数字都要有出处。**参数/价格/指标后面标来源与时间；查不到就写「未公开」，禁止估算成事实。
3. **区分「真机跑通」「仿真验证」「demo 视频」。**这是本调研最重要的可信度来源，任何一处不得含糊。
4. **每版调研稿都保留。**不要覆盖别人的章节文件，只写自己 scope 内的文件。
5. **窗口快满了跟我说，我让你更新 handoff。**不要硬撑到被截断。
