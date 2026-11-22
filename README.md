# 具身四足机器狗 · 全栈算法方案调研

调研 2023–2026 年主流四足机器狗从「本体传感器 → 状态估计 → 地形感知 → 导航 → 运动控制 → 高层智能」的完整算法栈。

**核心主张：四足全栈的主干已经从 MPC/WBC 手工建模转为 GPU 万级并行 RL + teacher-student 蒸馏 + sim2real；2025–2026 的新前沿不是替换运动层，而是把运动层当作 skill primitive，在上面叠 VLM/VLA 做长程任务——而这一层目前真机跑通的极少。**

## 在线浏览

- **[可视化调研页](https://allenrsi.github.io/quadruped-stack-survey/)** — 五层栈图、范式时间线、宣传 vs 真机矩阵、产业对比
- **[完整报告（HTML）](https://allenrsi.github.io/quadruped-stack-survey/report.html)** — 1.4 万字长文，16 张对比表
- [Markdown 原文](report.md)

## 结论速览

| # | 结论 |
|---|---|
| 1 | 运动控制已从瓶颈变成配置项：legged_gym 论文口径下单卡训练平地策略 **<4 分钟**、崎岖地形 **20 分钟** |
| 2 | 但 RL 没有取代 MPC——工业界是混合的，模型派退化为 baseline 与安全兜底 |
| 3 | 最容易被低估的是状态估计：含 flight phase 时 base height 不可观（Cerberus, arXiv:2210.02127） |
| 4 | 真机四足闭环跑通的公开 VLA 工作只有个位数，其余是机械臂验证或 demo 视频 |
| 5 | 世界模型在腿式上唯一的硬证据仍是 2022 年的 DayDreamer，四年无同量级后续 |
| 6 | 开源框架只有 IsaacLab 值得押注（8.7k star，2026-11-18 当天仍有提交） |

## 仓库结构

```
index.html                     可视化调研页（GitHub Pages 首页）
report.html                    完整报告静态页
report.md                      完整报告 Markdown（可在此直接阅读）
调研/
  00-overview.md               五层结构、范式演进、四档可信度标准、术语表
  01-locomotion-control.md     运动控制：MPC / RL / 混合，sim2real 工程清单
  02-perception-nav.md         状态估计、高程图、Nav2 三处腿式适配
  03-vla-and-frameworks.md     四足 VLA 落地存量、世界模型、开源框架对比
  04-industry-and-learning-path.md  九家产品、算法栈公开度、四阶段学习路径
复现/
  README.md                    复现状态说明 + 本机环境实测
  00-复现可行性评估.md         逐个 baseline 的可达性判断与排序
  01-legged_gym-复现方案.md    经典路线（受 Isaac Gym 门槛限制）
  02-mujoco_playground-实机可行的轻量路线.md  本机唯一可能跑通的路线
  03-isaaclab-复现方案.md      现代路线（8 GB 显存是硬伤）
related_work/
  README.md                    30 篇核心文献索引 + 一键抓取命令 + 阅读顺序
tools/md2html.ps1              report.md → report.html 的转换脚本
```

> **关于 `复现/`**：本轮**没有执行任何复现**。本机实测无 Python、pypi 约 15 KB/s、GPU 仅 8 GB，跑不动主流 baseline。目录里是可行性评估与可执行方案，不是实验结果——报告中的指标全部标注为「引自论文」。

## 方法

每一章都按**四档可信度**标注：A 真机常态化 / B 真机实验 / C 仿真验证 / D demo 视频。

论文名、年份、arXiv 号逐条核对过摘要页；查不到的写「未核实」，不拿记忆当事实。各章末尾列有「待交叉验证点」，共 20+ 条，是下一步该补的洞。

## 本地预览

直接双击 `index.html` 即可，无需任何依赖或构建步骤。

## 声明

调研时间 2026-11。数据以正文标注来源为准；预印本内容未经同行评审。产业数据（出货量、融资）变动快，均标注查证时间。
