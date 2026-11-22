# related_work · 文献索引

> 本轮调研以联网核证为主，**没有批量下载 PDF**。这里是核心文献索引，按主题分组，带 arXiv 号与一键抓取命令。
> 抓取：`powershell -ExecutionPolicy Bypass -File <skill>\scripts\fetch-paper.ps1 <arxiv-id> <目录名>`

---

## A · 运动控制主线（必读前 4 篇）

| # | 文献 | arXiv | 为什么读 |
|---|---|---|---|
| 1 | Di Carlo et al., *Dynamic Locomotion in the MIT Cheetah 3 Through Convex MPC*, RA-L 2018 | 无 | 模型派的 QP 形式化，必读 |
| 2 | Rudin et al., *Learning to Walk in Minutes*, CoRL 2021 | 2109.11978 | 万级并行 RL 的起点，必精读 |
| 3 | Kumar et al., *RMA: Rapid Motor Adaptation*, RSS 2021 | 2107.04034 | teacher-student 蒸馏模板 |
| 4 | Margolis & Agrawal, *Walk These Ways*, CoRL 2022 | 2212.03238 | 步态条件化，工程极实用 |

## B · 感知式运动与越障

| # | 文献 | arXiv | 要点 |
|---|---|---|---|
| 5 | Miki et al., *Learning Robust Perceptive Locomotion in the Wild* | 2201.08117 | 地形感知进策略的分水岭 |
| 6 | Nahrendra et al., *DreamWaQ* | 2301.10602 | 隐式地形估计 |
| 7 | Cheng et al., *Extreme Parkour with Legged Robots* | 2309.14341 | 高动态跑酷 |
| 8 | Zhuang et al., *Robot Parkour Learning*, CoRL 2023 | 2309.05665 | 技能蒸馏到单一视觉策略 |
| 9 | Long et al., *HIMLoco*（2023-12 首发） | 2312.11460 | 显式+隐式混合内部模型 |

## C · 鲁棒性与规划时域

| # | 文献 | arXiv | 要点 |
|---|---|---|---|
| 10 | Long et al., *Learning H-Infinity Locomotion* | 2404.14405 | H∞ 做成 RL 目标 |
| 11 | Shirwatkar et al., *PIP-Loco*, ICRA 2025 | 2409.09441 | 无限时域规划 |
| 12 | *DAWN: Deep Denoising World Model*, IROS 2026 | 2609.29092 | 用世界模型替代手工深度滤波 |
| 13 | *StairMaster* | 2606.25765 | Go2 零样本爬 55° 镂空楼梯 |

## D · 状态估计与感知

| # | 文献 | arXiv | 要点 |
|---|---|---|---|
| 14 | *Cerberus / VILENS* | 2210.02127 · 2107.07243 | flight phase 下 base height 不可观 |
| 15 | *Contact-aided Invariant EKF* | 1805.10410 · 1904.09251 | 腿式本体感受主线 |
| 16 | MEM: *Multi-modal Elevation Mapping*, IROS 2023 | 2309.16818 | 语义高程图 |
| 17 | *Deep IMU Bias* | 2211.04517 | 学习式 IMU 零偏 |
| 18 | *足端打滑下的接触估计* | 2606.05501 | GRF 对「接触但打滑」不敏感 |

## E · 导航与 VLN

| # | 文献 | arXiv | 要点 |
|---|---|---|---|
| 19 | *NaVid* | 2402.15852 | VLM 直出导航动作，无需地图 |
| 20 | *Uni-NaVid*, RSS 2025 | 2412.06224 | 统一多任务导航 VLA |
| 21 | *NavFoM* | 2509.12129 | 导航基础模型 |
| 22 | *ConceptGraphs* | 2309.16650 | 开放词汇 3D 场景图 + LLM 分解 |
| 23 | *FAR Planner*, IROS 2022 | 2110.09460 | 可尝试重规划 |

## F · 四足 VLA 与高层智能

| # | 文献 | arXiv | 落地等级 |
|---|---|---|---|
| 24 | *From Tabletop to Walking Bot*, 2026-10 | 2610.32271 | **A/B** 唯一完整闭环 |
| 25 | *DR-VLA*, 2026-10 | 2610.18373 | B 户外配送 |
| 26 | *TrackVLA++* | 2510.07134 | B |
| 27 | *MoRE*, 2025-03 | 2503.08007 | B 多 LoRA 专家 + RL 微调 |
| 28 | *ODYSSEY*, 2025-08 | 2508.08240 | B 四足+机械臂长程 |
| 29 | *SayTap*（非 VLA，常被误归） | 2306.07580 | LLM → 足端接触模式 |
| 30 | *DayDreamer* | 2206.14244 | 腿式上唯一硬的世界模型证据 |

---

## 抓取示例

```powershell
$skill = "C:\Users\Allen\.dsh\skills\research-workflow"
powershell -ExecutionPolicy Bypass -File "$skill\scripts\fetch-paper.ps1" 2109.11978 legged_gym
powershell -ExecutionPolicy Bypass -File "$skill\scripts\fetch-paper.ps1" 2107.04034 RMA
powershell -ExecutionPolicy Bypass -File "$skill\scripts\fetch-paper.ps1" 2201.08117 perceptive_locomotion
```

抓下来后每篇是 `paper.pdf` + `source/`（已清洗的 LaTeX）。详见项目根目录 `AGENTS.md` 的「读论文的规矩」。

---

## 阅读顺序建议

**要快速建立全局观**：1 → 2 → 3 → 5（四篇，约 3 天）

**要动手做**：2 → 4 → 6 → 9（这四篇对应能跑起来的代码）

**要做研究找空白**：5 → 11 → 24 → 30（感知、规划时域、VLA、世界模型各一篇）
