# Handoff

> 每个窗口结束前更新这份。**下一个 Agent 只读 AGENTS.md + 这份就能接上。**
> 最后更新：2026-11-18 · 第 1 个窗口（已完成首轮交付）

---

## 一句话现状

**首轮调研已交付：五章分线稿 + report.md 长文 + index.html 可视化页全部完成；下一步是补各章「待交叉验证点」的 20+ 个洞。**

---

## 已经确定不用再动的

- ✅ 项目骨架 + AGENTS.md（核心主张已定）
- ✅ `调研/00-overview.md` — 五层栈、演进时间线、四档可信度标准、术语表
- ✅ `调研/01-locomotion-control.md` — 运控三派、RMA→DAWN 演进、sim2real 清单（12 表）
- ✅ `调研/02-perception-nav.md` — 状态估计四路线、高程图、Nav2 三处腿式适配（5 表）
- ✅ `调研/03-vla-and-frameworks.md` — VLA 落地存量 6 个、框架 star 实测、分层架构（4 表）
- ✅ `调研/04-industry-and-learning-path.md` — 9 家产品、算法栈公开度、四阶段学习路径（8 表）
- ✅ `report.md` — 9 章长文，已合并四章内容
- ✅ `index.html` — 单文件可视化页，35KB，标签平衡校验通过

## 正在做

- 🔄 无。等待用户反馈后再定下一轮。

## 还没动 / 该补的

- ✅ `复现/` 已补并**真跑了一项**：WSL2 + MuJoCo 的 12 DOF 力控，站立成功（高 0.265 m，滚转 4.5°）/ 小跑失败（净速度 -0.12 m/s）。失败原因：缺 WBC 分层与滚动时域。详见 `复现/mpc/README.md`
- ✅ `related_work/README.md` 已补：30 篇文献索引 + 抓取命令 + 阅读顺序（**PDF 未下载**）
- ⬜ **20+ 条「待交叉验证点」**（各章末尾）：PD 增益、`dt/decimation`、摩擦区间、WBIC 频率、HIMLoco 硬件口径、Pronto/TSIF 实际频率、cupy 在 Orin 的帧率、MPPI 可用频率、TARE/FAR 的 ROS2 状态、DAWN/StairMaster/LocoWM 的提升幅度等。
- ⬜ **真要复现**：先装 Python 3.10+（别用 Store 版）→ 配清华镜像测速 → 跑 mujoco_playground 的 Go1 验证链路 → 再决定是否租云卡跑 legged_gym。门禁条件写在 `复现/README.md`。
- ⬜ **DataSet/**：本轮未涉及数据集。
- ⬜ **浏览器截图验证**：本机 Electron 不可用，index.html 只做了标签/编码校验，没做视觉验证。

---

## 已发布

- 仓库：https://github.com/AllenRSI/quadruped-stack-survey （public，main）
- Pages：https://allenrsi.github.io/quadruped-stack-survey/ （main 分支根目录，构建状态已验证 `built`）
- 报告页：https://allenrsi.github.io/quadruped-stack-survey/report.html
- 站点 = `index.html`（可视化首页）+ `report.html`（报告静态页）+ `.nojekyll`
- `report.html` 由 `tools/md2html.ps1` 从 `report.md` 生成。改完 report.md 后重跑：

```powershell
$src=[System.IO.File]::ReadAllText("$PWD\tools\md2html.ps1",[System.Text.Encoding]::UTF8)
& ([scriptblock]::Create($src)) -In "$PWD\report.md" -Out "$PWD\report.html"
```

（本机执行策略禁止直接跑 .ps1，要用 scriptblock 绕过；**且必须用 pwsh 7，不能用 `powershell`——5.1 解析器会报错**。）

---

## 踩过的坑，别再踩

1. **init-project.ps1 执行策略被禁** —— 用 `powershell -ExecutionPolicy Bypass -File`。
2. **本机没有 python / node 在 PATH** —— 不要依赖脚本生成 HTML，手写。
3. **PowerShell 读 UTF-8 文件会误判标签** —— `Get-Content -Raw` 默认可能按 ANSI 解，导致中文尾字符吃掉 `<`，把 166/166 的 div 数成 166/138。**必须加 `-Encoding UTF8` 或 `[System.IO.File]::ReadAllText(..., Encoding::UTF8)`。**
4. **调研员会把知识停在 2024** —— 本轮已要求查 2025-2026，实际抓到 DAWN / StairMaster / LocoWM / From Tabletop to Walking Bot 等。
5. **任务书里我写错了三个工作名**（Quadruped-Frontier、VBC、LeggedLoco；AnyBody 实为人形）—— 已被 researcher-vla 揪出并清理，后续派活别再引用。
6. **`powershell`(5.1) 与 `pwsh`(7) 解析器行为不同** —— 同一脚本 pwsh 零错误、5.1 报 unexpected token。跑 .ps1 一律用 pwsh。
7. **本机无 gh CLI** —— GitHub 操作走 REST API + `curl.exe`。注意 PS 传 JSON 时引号会被吃掉，**必须写成无 BOM 文件再用 `--data-binary @file`**，否则报 400 Problems parsing JSON。
8. **CDN 直连会被 reset**（jsdelivr 等）—— 所以没有引入任何外部 JS/CSS，站点完全离线可用。

---

## 给下一个窗口的第一句话

> 读 AGENTS.md 和这份。交付物在 `report.md`（长文）和 `index.html`（可视化页），分章材料在 `调研/`。若要继续深化，优先补各章末尾的「待交叉验证点」——尤其是 01 章的 PD/dt 默认值和 02 章的 MPPI/Nav2 实测频率，这两块目前是「量级估计」而非实测值。
