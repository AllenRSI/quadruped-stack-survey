# 03 · 高层智能（VLM/VLA/世界模型）与开源全栈框架

> **本章结论一句话**：四足与 VLA 的真实关系是「用 VLA 做语义导航和高层任务，用 RL 做一切和平衡、地形、速度有关的事」——把 VLA 直接接到四足关节上、在真机上闭环跑通的公开工作，我逐个核过之后只有个位数，且几乎全部只完成单一任务；开源框架这边则相反，运动层的栈已经高度收敛且活跃（IsaacLab 系），VLA 侧的栈（LeRobot/openpi/Isaac-GR00T）活跃但**与四足基本没有开箱即用的接口**。

**关于本章的验证等级标记**（这是本章最重要的东西，也是整份调研最容易被宣传带偏的地方）：

| 标记 | 含义 |
|---|---|
| **L3 真机四足** | 论文/官方自述在真实四足上闭环运行；本文给出本体型号或明确说明型号未核实 |
| **L2 仿真四足** | 只在 Habitat/IsaacLab/MuJoCo 等仿真中的四足本体上验证 |
| **L1 机械臂/桌面** | 真机验证，但本体是固定底座机械臂或移动底盘，**不是四足** |
| **L0 仅 demo** | 只有官方博客/演示视频/研究预览，无可复现产物或第三方复现 |

「官方自述」不等于「第三方复现过」。本领域 2025-2026 的通行做法是：论文里 1 个真机 demo + 大量仿真数字，且真机 demo 往往是糖纸包装好的单场景。**没有任何一个工作公布过跨场景、跨本体、可复现的四足 VLA 真机基准。**

---

## 1. 四足上真正跑通的 VLA，数量比想象中少得多

把「真机四足 + 语言/视觉高层输入 + 闭环控制」三条同时满足的公开工作筛出来，只有下面这些，而且它们各自只覆盖一件事：

- **NaVid**（arXiv:2402.15852，2024-02）：视频驱动的 VLM 直接输出下一步动作做 VLN，**不需要地图、里程计、深度**，只用单目 RGB 视频流。论文明确做了 sim-to-real 的真实部署（真机四足，具体型号本文未核实）。它的意义是第一次证明「VLM 不做 3D 重建也能导航」，局限是只走室内短指令、速度极慢。
- **Uni-NaVid**（arXiv:2412.06224，2024-12）：把指令跟随、找物体、问答、跟人统一进一个视频 VLA，宣称首个统一多任务的视频 VLA 导航模型，真机在未见过的真实环境跑长程混合任务。**这是四足上最接近「通用导航策略」的公开工作。**
- **TrackVLA++**（arXiv:2510.07134，2025-10）：具身视觉跟踪（EVT），加了 Polar-CoT 空间推理和 Target Identification Memory，解决遮挡和相似干扰物。前代 TrackVLA 出自银河通用，公开演示是真机四足；**++ 版本的真机部署范围未核实**。
- **DR-VLA**（arXiv:2610.18373，2026-10）：户外配送四足导航。用 10,000 小时自采第一视角网络视频（EgoLynx-Web）+ 2,000 段真实配送遥操作数据（EgoLynx-Robot）预训练，Mixture-of-Transformers + 流匹配动作专家 + 隐空间世界模型。**这是我看到的最诚实的「数据不够就用人视频补」的路线，也是唯一公开四足户外配送规模数据的。**
- **From Tabletop to Walking Bot**（arXiv:2610.32271，2026-10）：把桌面机械臂上训好的 VLA 迁到 **Unitree Go2 + AgileX Piper** 上做闭环 loco-manipulation。**这篇是本章最该读的一篇**，因为它不谈模型创新，只谈落地时要做的取舍：模型变体、action horizon、示教约定、以及「底座会动」之后策略必须同时协调导航、机身姿态和末端——这正是四足与机械臂的分界线。
- **SayTap**（arXiv:2306.07580，2023）：严格说不算 VLA，是 **LLM → 足端接触模式 → 运动控制器**，真机四足（Go1）验证。但它给出了四足高层智能最务实的分层范式：语言不要碰关节，只碰「接触模式」这种中间表征。

**反面清单（必须点名的三个名字）**：任务书里提到的 `Quadruped-Frontier`、`AnyBody`、`VBC`，我用 arXiv 标题检索逐个查过——**都没有命中对应的「四足 VLA」工作**。其中 AnyBody 实为**人形**全身关键点控制（用任意关键点自由控制人形身体），与四足无关；`LeggedLoco(lib)` 也未找到对应的公开库。这三个名字建议从项目文档里删掉或降级为「来源未核实」，否则会污染后面的选型判断。

### 表 1 · VLA / 世界模型代表作与「在四足上的真实落地程度」

| 工作 | 时间 | 本体 | 高层输入 → 输出 | 验证等级 | 开源 | 关键事实 |
|---|---|---|---|---|---|---|
| **From Tabletop to Walking Bot** | 2026-10 | **Unitree Go2 + AgileX Piper** | 视觉+语言 → 底盘+臂联合动作 | **L3 真机四足** | 未核实 | 本章最完整的一篇落地报告：模型变体、action horizon、示教约定都写了 |
| **DR-VLA** | 2026-10 | 户外配送四足 | 视觉+语言 → 导航动作 | **L3（真机数据）**，闭环部署程度未核实 | 未核实 | 10,000h 人第一视角视频 + 2,000 段真机遥操作，MoT + 流匹配 |
| **TrackVLA++** | 2025-10 | 四足（型号未核实） | 语言指定目标 → 跟踪动作 | **L3 真机四足** | 未核实 | Polar-CoT 空间推理 + 目标记忆，专治遮挡与相似干扰 |
| **Uni-NaVid** | 2024-12 | 四足 | 视频+语言 → 导航动作 | **L3 真机四足** | 未核实 | 首个统一指令跟随/找物/问答/跟人的视频 VLA |
| **NaVid** | 2024-02 | 四足（型号未核实） | 单目视频+语言 → 下一步动作 | **L3 真机四足** | 未核实 | 不用地图/里程计/深度；首个 VLM 直出导航动作 |
| **SayTap** | 2023 | Unitree Go1 | 自然语言 → 足端接触模式 | **L3 真机四足**（非 VLA） | 未核实 | 语言不碰关节、只碰接触模式——最务实的分层范式 |
| **π0** | 2024-10 | 机械臂/移动底盘共 8 种配置 | 视觉+语言 → 50 步动作块 | **L1** | 开源（openpi，Apache-2.0） | 3B 级 flow matching 动作专家，跨本体微调范式奠定者 |
| **π0.5** | 2025-04 | 移动机械臂（真实家庭） | 视觉+语言 → 动作块 | **L1**（非四足） | **未开源**（仅 π0 权重公开） | 异构数据联合训练做开放世界泛化，至今是机械臂侧最强公开结果 |
| **GR00T N1** | 2025-03 | 人形 | 视觉+语言 → 全身动作 | **L1/L2**（人形，非四足） | 开源（Isaac-GR00T，Apache-2.0，8.4k star） | 双系统（快慢）架构；官方无四足 recipe |
| **Gemini Robotics 1.5 / ER 1.5** | 2025-09 | 机械臂为主；已与 Spot 合作 | 视觉+语言 → 动作 / 空间推理 | **L1 + L0**（Spot 为官方演示） | 闭源 | 强调「先思考再动作」与跨本体迁移；四足侧只有官方博客 |
| **V-JEPA 2 / 2-AC** | 2025-06 | 实验室机械臂 | 视频表征 → 零样本拾取放置 | **L1** | 部分开源 | 自监督视频预训练可规划，但缺动作条件化层 |
| **DayDreamer** | 2022 | **Unitree A1（真机）** | 本体感觉+视觉 → 关节 | **L3 真机四足** | 未核实 | 世界模型在真机四足上约 1 小时学会走路，此后四年无同量级后续 |
| **DreamerV3** | 2023 / Nature 2025 | 多域（含仿真） | 观测 → 动作 | **L2** | 未核实 | 单一超参跨域通用的里程碑，但不是四足工程方案 |
| **Cosmos WFM** | 2025-01 | 无本体 | 文本/视频 → 合成视频 | **L0**（工具链） | 部分开源 | 定位是数据工厂，给 GR00T 一类模型造训练数据，不是控制器 |
| **Genie 3** | 2025-08 | 无本体 | 文本/图像 → 可交互 3D 世界 | **L0**（研究预览） | 闭源、无公开 API | 720p/24fps、分钟级一致性；与四足控制无任何公开结合 |

读这张表的正确方式：**L3 那一栏（6 行）就是「四足上真正跑通」的全部公开存量**，其中 2 行还是「真机数据但闭环程度未核实」，1 行（SayTap）根本不是 VLA。剩下的 L1/L0 全是机械臂、人形、或无本体的工具——它们构成了这个领域 90% 以上的宣传素材。

---

## 2. 为什么四足上的 VLA 比机械臂难一个量级

### 2.1 动作频率与分层是硬约束

机械臂 VLA 可以 5-10Hz 直接输出末端增量，因为底座不动、动力学慢。四足不行：机身是欠驱动的，任何 1Hz 级别的动作指令都必须由 50Hz 的运动策略去「实现」，再由 500Hz-1kHz 的关节 PD 去跟踪。所以四足上 VLA 的输出**必然是抽象的**——航点、速度指令、skill 选择、接触模式，而不是关节角。**谁声称 VLA 直出四足 12 维关节且效果好，基本可以直接怀疑。**

由此推出工程上唯一可行的架构（本章后面复现路径也按这个走）：

```
VLM/VLA（0.5-5Hz）：看画面 → 出语义目标 / skill 名 / 航点
        ↓
skill primitive 层（10-50Hz）：航点跟踪、视觉伺服、抓取位姿
        ↓
运动策略（50Hz，RL 训出来的 policy）：速度指令 → 关节目标
        ↓
关节 PD（500Hz-1kHz，SDK 层）：力矩/位置闭环 + 安全裁剪
```

### 2.2 数据缺口是结构性的

Open X-Embodiment 这类聚合数据集里，腿式平台占比极低，四足+臂的遥操作数据几乎为零。DR-VLA 用 10,000 小时人类第一视角视频去补，本质是在承认「机器人数据采不起」。反过来，机械臂有 ALOHA、DROID 这种万级 episode 的开源数据集，π0/π0.5 才能做出泛化。**四足 VLA 的数据问题在 2026 年没有解决，只是被绕开了。**

### 2.3 没有可比的 benchmark

导航侧有 SR/SPL（成功率/路径长度加权成功率），操作侧有成功率，两套指标不可比；四足还多一个「摔不摔」的安全指标，几乎没人报。所以任何「我们的四足 VLA 比 baseline 强 X%」的说法，先问三件事：什么本体、多少场景、失败怎么算。

---

## 3. 世界模型：在腿式上唯一像样的证据来自 2022 年

**结论：世界模型目前在四足上的现实用途是「造数据」和「做价值函数」，不是替代策略。**

- **DreamerV3 / DayDreamer**：DreamerV3 的期刊版是 *Mastering Diverse Domains through World Models*（arXiv:2301.04104，Nature 2025 刊出）；真正在**真机四足**上跑通的是它的前作 **DayDreamer**（arXiv:2206.14176，2022）：在 A1 四足上**约 1 小时**学会走路。这是「世界模型 + 真机四足」最强的一条证据，但它是 2022 年的单任务结果，四年过去没有出现同等量级的后续。
- **V-JEPA 2**（arXiv:2506.09985，2025-06）：自监督视频模型 + V-JEPA 2-AC 做零样本拾取放置，验证平台是**实验室机械臂（Franka 类）**，不是四足。它的价值在于「用视频预训练得到可规划的表示」，但要接到四足上还缺一层动作条件化。
- **Cosmos**（arXiv:2501.03575，2025-01）：World Foundation Model 平台，定位是**合成数据与仿真**，给 GR00T 这类模型生成训练视频。它不是控制器，评估它「能不能控制机器人」是问错了问题。真实用途：补长尾场景、做域随机化的视频版。
- **Genie 3**（Google DeepMind，2025-08 公布）：交互式世界模型，720p/24fps 实时生成可探索环境，一致性能维持数分钟。**无公开 API、研究预览、与四足控制无任何公开结合**，标 L0。它对四足的价值是未来的「无限仿真器」，现在不能进任何工程方案。
- **V-JEPA/Genie 系的共同问题**：生成的未来帧再漂亮，也不能保证「在真实四足上闭环不摔」。世界模型的误差在长程会累积，而四足一旦摔就是硬件损失。

---

## 4. 开源全栈框架盘点

**结论：运动层只有 IsaacLab 一个值得押注的选择；legged_gym 已经事实上停更 18 个月，新项目不要再用。**

star 数与最近提交时间均为 **2026-11-18 通过 GitHub API 查证**；License 一栏若 GitHub 标为 NOASSERTION，说明仓库用的是自定义/多协议文件，**落地前必须自己读 LICENSE**。

| 框架 | 仓库 | star（2026-11-18） | 最近提交 | License | 仿真依赖 | 上手难度 | 适用 |
|---|---|---|---|---|---|---|---|
| **IsaacLab** | `isaac-sim/IsaacLab` | 8.7k | 2026-11-18（当天） | GitHub 标 NOASSERTION（实际 BSD-3 系，需核对） | Isaac Sim 4.x/5.x，**不再依赖旧 Isaac Gym** | 中高（Isaac Sim 安装本身是门槛） | **首选**：四足/人形 RL 训练，当前 tag 已到 v3.0.0，v2.3.x 稳定可用 |
| **legged_gym** | `leggedrobotics/legged_gym` | 3.2k | **2025-05-29（停更约 18 个月）** | NOASSERTION | **必须 Isaac Gym Preview 4（NVIDIA 已弃更）** | 低（但装 Isaac Gym 会卡住新人） | 只用于读经典实现（ANYmal 那套 reward/课程设计），不要用于新项目 |
| **rsl_rl** | `leggedrobotics/rsl_rl` | 3.1k | 2026-11-17 | NOASSERTION | 无（纯 PPO 实现，可配任意 sim） | 低 | **必装**：PPO + teacher-student 蒸馏的事实标准，IsaacLab 官方后端之一 |
| **robot_lab** | `fan-ziqi/robot_lab` | 2.0k | 2026-10-20 | Apache-2.0 | IsaacLab（跟随其版本） | 中 | 国产本体适配最全：`assets/` 下已含 unitree、deeprobotics、booster、robotera 等厂商模块 |
| **unitree_rl_gym** | `unitreerobotics/unitree_rl_gym` | 3.7k | **2025-07-25（停更约 16 个月）** | BSD-3-Clause | **Isaac Gym** | 中 | Go2 官方入门：`legged_gym/envs/` 下确有 `go2`、`g1`、`h1`、`h1_2`；能用但已落后 |
| **mujoco_playground** | `google-deepmind/mujoco_playground` | 2.3k | 2026-11-17 | Apache-2.0 | MuJoCo/MJX（GPU 加速，无需 Isaac） | 中 | **无 NVIDIA 依赖的替代路线**；包内含 `rl/`、`real/`，后者用于真机对照 |
| **unitree_sdk2**（C++） | `unitreerobotics/unitree_sdk2` | 1.5k | 2026-11-18 | BSD-3-Clause | 无 | 中 | 真机通信底座（DDS），低层控制必用 |
| **unitree_sdk2_python** | `unitreerobotics/unitree_sdk2_python` | 0.85k | 2026-09-21 | BSD-3-Clause | 无 | 低 | 快速验证；**issue 数 142，坑不少**，上生产前要有心理准备 |
| **unitree_ros2** | `unitreerobotics/unitree_ros2` | 0.90k | 2026-07-02 | BSD-3-Clause | 无 | 中 | ROS2 桥，接 Nav2/自研感知时用 |
| **OCS2** | `leggedrobotics/ocs2` | 1.5k | 2026-09-29 | BSD-3-Clause | 无 | 高（C++/优化功底） | 最优控制路线（MPC），与 RL 二选一或做 baseline |
| **Nav2** | `ros-navigation/navigation2` | 5.1k | 2026-11-18 | NOASSERTION（Apache-2.0 系） | 无 | 中 | 导航层骨架；四足上需替换/调优 costmap 与足迹模型 |
| **Isaac ROS** | `NVIDIA-ISAAC-ROS/isaac_ros_common` | 0.32k（仅 common 子仓） | 2026-11-18 | NOASSERTION | 需 Isaac Sim/ROS2 | 高（容器化，绑定 Jetson 版本） | 机载感知加速；四足上主要用于 VSLAM/深度 |
| **LeRobot** | `huggingface/lerobot` | **29.0k** | 2026-11-18 | Apache-2.0 | 无（主推真机数据） | 低-中 | 数据采集/训练/推理的事实标准；**四足支持需自己写 platform 适配** |
| **openpi**（π0/π0.5） | `Physical-Intelligence/openpi` | 14.7k | 2026-08-24 | Apache-2.0 | 无 | 中高（3B 模型 + 自有数据格式） | 机械臂/移动底盘 VLA 微调首选 |
| **Isaac-GR00T** | `NVIDIA/Isaac-GR00T` | 8.4k | 2026-11-17 | Apache-2.0 | 依赖 Isaac 生态 | 高 | 人形 VLA 微调；**四足没有官方 recipe** |
| **OpenVLA** | `openvla/openvla` | 7.3k | **2025-03-23（停更）** | MIT | 无 | 中 | 已被后续工作超越，仅作 baseline/教学 |

补充判断，几条不写在表里但很重要的：

1. **IsaacLab 已到 v3.0.0**（tags 查证），同时 v2.1/2.2/2.3 系列都在；网上大量教程还停在 IsaacLab 1.x，跟着装会踩 API 变更的坑。**选版本比选框架更容易出事。**
2. **legged_gym 与 unitree_rl_gym 都锁死在 Isaac Gym Preview 4**，而 NVIDIA 早已停止更新 Isaac Gym、转向 Isaac Sim/IsaacLab。这两条路 2027 年会越来越难装（依赖旧 CUDA/Python 3.8）。
3. **star 数不能当维护度看**：LeRobot 29k star 但四足支持为零；unitree_rl_gym 3.7k star 却停更 16 个月。**看「最近提交 + 是否跟随 IsaacLab 版本」比看 star 有用得多。**

---

## 5. 从零到实机：一条可执行的复现路径

下面以 **Unitree Go2 + IsaacLab + rsl_rl + unitree_sdk2** 为主干。命令是「步骤感」而非逐字可粘贴（路径随 IsaacLab 版本变化），但顺序和坑是真实的。

**阶段 0：环境（半天到两天，主要耗在 Isaac Sim）**
- Ubuntu 22.04 + NVIDIA 驱动 550+ + RTX 4090（24GB）。Isaac Sim 需要 RTX 显卡，**AMD/核显直接出局**。
- 装 IsaacLab（建议锁 v2.3.x 稳定分支，别一上来追 v3.0.0）+ 按官方文档装 Isaac Sim；再 `pip install -e` 装 rsl_rl。
- 国内网络下 Isaac Sim 的 USD 资产下载是第一个大坑，先备好代理或离线包。

**阶段 1：训练（单卡 4090，Go2 速度跟踪任务）**
```bash
# 4096 个并行环境，headless（无渲染，快 2-3 倍）
python scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-Flat-Unitree-Go2-v0 --headless --num_envs 4096
```
- 时长量级：4096 envs 下单卡 4090 大约 **20-60 分钟**能出可用策略（此为社区通行量级，**未逐项核实**具体迭代数）。任务名随 IsaacLab 版本变化，以 `--help` 列出的为准。
- 想要盲走/抗扰，再加 terrain curriculum + 域随机化（摩擦、质量、电机强度、外部推力）。这一步决定了真机能不能站住。

**阶段 2：导出（10 分钟）**
```bash
python scripts/reinforcement_learning/rsl_rl/play.py --task ... --checkpoint <ckpt> --export
```
- 产出 `policy.pt`（TorchScript）或 ONNX。**真机上只跑推理，不要带训练依赖**。
- 关键：把观测归一化参数（mean/std）一起导出，否则真机输入分布对不上，策略会直接瘫。

**阶段 3：真机部署（最容易出事的一段）**
- 通信：Go2 走 **DDS**。高层用 `sport/state` + `sport/request`（速度指令），低层用 `rt/lowstate`（读，约 500Hz）+ `rt/lowcmd`（写）。Python 用 `unitree_sdk2_python`，C++ 用 `unitree_sdk2`。
- **低层控制必须先退出 sport mode**，且官方明确 low-level 有烧电机/摔机风险。**第一次上真机请把狗吊起来（吊架）跑，不要落地。**
- 安全层必须是独立于策略的一层，至少四条：
  1. 关节角/力矩**硬裁剪**（在 SDK 写入前，不在策略里）；
  2. 姿态保护：roll/pitch 超阈值直接切零力矩阻尼（damping 模式）；
  3. 看门狗：策略推理超时（比如 >100ms 没出下一帧）立刻降级为阻尼；
  4. 物理急停：遥控器接管优先于一切软件。
- 延迟预算（真机实测才是数，下面是设计目标）：VLA/VLM 200ms-2s → skill 20-100ms → 运动策略 20ms（50Hz）→ 关节 PD 1-2ms。**任何一层抖动都会让上层「看起来在发呆」。**

**阶段 4：接 VLA（可选，最后做）**
- 路径 A（推荐，稳）：ROS2 桥 → VLM 只做「看图出航点/出 skill 名」→ Nav2 或自写航点跟踪 → 速度指令进运动策略。VLM 挂了不影响走路。
- 路径 B（激进）：LeRobot 训练一个 3B 级 VLA，在 Go2 上微调导航动作头。现实预期：需要数千条遥操作 episode，且只在采集场景附近有效。
- 无论哪条路，**先把「VLA 掉线时机器人能安全停住」做出来，再谈智能。**

---

## 6. 算力与成本

**结论：训练端不是瓶颈（一张 4090 就够训四足运动），瓶颈在机载端跑 VLA 和采数据的人。

| 环节 | 硬件 | 关键参数（厂商标称） | 现实情况 |
|---|---|---|---|
| 训练（运动层 RL） | RTX 4090 24GB | 4096 并行环境可跑 | 单卡够用；四足运动任务不需要多卡 |
| 训练（VLA 微调） | A100 80GB / H100 / 多卡云 | π0 级模型约 3B 参数 | 全量微调需多卡；LoRA 单卡 24-48GB 可试（**显存数字未核实**） |
| 机载（主流） | Jetson Orin NX 16GB | **100 TOPS**（Super 模式 157 TOPS，NVIDIA 标称） | 跑运动策略轻松；跑 3B VLA 很勉强，频率预计 1-3Hz 级（**未核实**） |
| 机载（高配） | Jetson AGX Orin 64GB | **275 TOPS**（NVIDIA 标称） | 四足上装得下，功耗与散热要重新设计 |
| 机载（新一代） | Jetson Thor | 面向物理 AI，算力显著高于 Orin | **具体 TOPS 与四足适配案例均未核实**，2026 年仍在早期 |
| 数据采集 | 遥操作手柄 + 动捕/VR | — | **这才是真成本**：四足+臂的遥操作效率低，一小时有效数据要多人配合 |

价格一律不写具体数——2026 年的行情波动大，且不同渠道（edu/代理/二手）差异极大，**任何精确报价都会误导选型**。要报价请按「Go2 EDU + Orin + 一张 4090 工作站 + 一个人月」这个组合去询价。

---

## 7. 给技术负责人的三段话

1. **该不该上 VLA**：如果你的需求是「走到某处、找到某个东西、跟着某个人、听懂一句话去执行」，VLA/VLM 值得投入，且**只做语义层**，运动层老老实实用 RL。如果是「复杂地形、高速、抗扰」，VLA 一点用都没有，别浪费预算。
2. **该选哪个框架**：**只推一个——IsaacLab（配 rsl_rl）**。理由不是它最好用，而是它是唯一还在按周迭代、且生态（robot_lab/各家本体资产）都围着它转的。legged_gym 只能用来读代码。
3. **别信 demo**：看到四足 + VLA 的视频，先问三句——什么本体、几个场景、失败率多少。**本章标注为 L0/L1 的东西，占了这个领域宣传量的九成。**

---

## 待交叉验证点

1. **NaVid / Uni-NaVid / TrackVLA++ 的真机四足型号与场景数**：本文只能确认「论文自述做了真机部署」，具体是 Go2 还是自研平台、跑了几个场景、成功率多少，需回原文实验节核对。
2. **DR-VLA 的部署程度**：摘要只能确认「用真实配送遥操作数据训练」，是否在真机四足上闭环部署、闭环时长多少，未核实。
3. **`Quadruped-Frontier` / `AnyBody` / `VBC` / `LeggedLoco(lib)` 四个名字的来源**：arXiv 标题检索均未命中对应的四足 VLA 工作（AnyBody 实为人形全身控制）。需回到任务书出处确认是笔误还是内部代号。
4. **IsaacLab v3.0.0 的发布时间与 v2.3.x 的兼容边界**：本文只查到 tag 存在，未查到发布日期与破坏性变更清单；实际选版本前必须读 release notes。
5. **Jetson Thor 的算力标称与四足实机案例**：厂商标称口径（FP4/FP8/INT8 混杂）不可直接比较，且 2026 年尚无公开的四足 + Thor 部署报告。
6. **训练时长（4096 envs / 单卡 4090 / 20-60 分钟）**：属社区经验量级，未在本文环境下实测。

---

## 参考（均于 2026-11-18 核查可达）

- NaVid — https://arxiv.org/abs/2402.15852
- Uni-NaVid — https://arxiv.org/abs/2412.06224
- TrackVLA++ — https://arxiv.org/abs/2510.07134
- DR-VLA — https://arxiv.org/abs/2610.18373
- From Tabletop to Walking Bot（Go2 + Piper 真机） — https://arxiv.org/abs/2610.32271
- SayTap — https://arxiv.org/abs/2306.07580
- π0 — https://arxiv.org/abs/2410.24164 ；π0.5 — https://arxiv.org/abs/2504.16054
- GR00T N1 — https://arxiv.org/abs/2503.14734
- V-JEPA 2 — https://arxiv.org/abs/2506.09985
- Cosmos WFM — https://arxiv.org/abs/2501.03575
- DreamerV3 — https://arxiv.org/abs/2301.04104 ；DayDreamer — https://arxiv.org/abs/2206.14176
- Gemini Robotics 1.5 — https://deepmind.google/blog/gemini-robotics-15-brings-ai-agents-into-the-physical-world/
- IsaacLab — https://github.com/isaac-sim/IsaacLab ；rsl_rl — https://github.com/leggedrobotics/rsl_rl
- legged_gym — https://github.com/leggedrobotics/legged_gym ；robot_lab — https://github.com/fan-ziqi/robot_lab
- unitree_rl_gym — https://github.com/unitreerobotics/unitree_rl_gym ；unitree_sdk2_python — https://github.com/unitreerobotics/unitree_sdk2_python
- mujoco_playground — https://github.com/google-deepmind/mujoco_playground
- LeRobot — https://github.com/huggingface/lerobot ；openpi — https://github.com/Physical-Intelligence/openpi ；Isaac-GR00T — https://github.com/NVIDIA/Isaac-GR00T
