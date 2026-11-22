# 02 · 状态估计 / 地形感知 / 导航层

> 一句话结论：四足全栈里**最容易低估的是状态估计，最容易过度设计的是导航**——90% 的实机翻车发生在"腿式里程计漂了 5 分钟之后高程图错了 20 cm"，而不是规划器不够聪明。

本文只写能落地的部分：选型、频率、算力、失效模式。所有带 URL 的结论都查过原文/官方文档；拿不准的地方明确标「未核实」，不写没来源的数字。

---

## 1. 为什么四足的状态估计比轮式/人形都难

一句话：**腿既是传感器又是执行器，接触状态每一毫秒都在变，而所有"零速假设"类观测都在高动态下失效。**

四个具体难点：

| 难点 | 机理 | 后果 |
|---|---|---|
| 飞行相 / 腾空 | 小跑/跳跃时无足端接触，腿部里程计**没有观测** | 基座高度不可观。Cerberus 团队明确：含 flight phase 时 SOTA 方法无法可靠估计姿态，**尤其 base height**（[arXiv:2210.02127](https://arxiv.org/abs/2210.02127)） |
| 足端打滑 | leg odometry 假设"支撑足相对世界速度为零" | 冰面、碎石、泥地直接崩；而足端 GRF 传感器**对"接触但打滑"不敏感**（[arXiv:2606.05501](https://arxiv.org/abs/2606.05501)，2026） |
| IMU 饱和 / 零偏漂移 | 落足冲击短时高 g 打满量程；bias 随温度与冲击历史漂移 | 姿态数秒内线性发散——Deep IMU Bias 这类工作的动机（[arXiv:2211.04517](https://arxiv.org/abs/2211.04517)） |
| 视觉退化 | 运动模糊、rolling shutter、低纹理地面、逆光；冲击破坏 camera-IMU 同步/外参 | VIO 在纯旋转、匀速段尺度退化，模糊帧直接丢跟踪 |

工程含义：不要指望单一估计器，必须做**退化检测 + 模态切换**（Pronto 把 IMU、腿部运动学与可选视觉/LiDAR 放进同一滤波器，正是这个思路，[Frontiers 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7805780/)）。

---

## 2. 状态估计三条路线与失效模式

一句话：**proprioceptive（contact-aided EKF）负责鲁棒与高频，VIO/LIO 负责消除长期漂移，learned 负责补上"打滑与冲击"这段模型空白。**

### 2.1 Contact-aided invariant EKF（腿式 proprioceptive 主线）

- 代表：MIT 的 contact-aided InEKF（[arXiv:1805.10410](https://arxiv.org/abs/1805.10410)，RSS 2018，在 Cassie 双足上首次给出接触辅助的不变观测器；扩展版 [arXiv:1904.09251](https://arxiv.org/abs/1904.09251) 成为 MIT Cheetah 系列机载估计器的基线）。
- 优点：只用 IMU + 关节编码器 + 接触检测，**不依赖光照与纹理**；不变误差（invariant error）线性化误差更小，收敛域更大。
- 最容易翻车的细节：接触概率是**软约束**，协方差要按接触置信度缩放；足端位置噪声与编码器噪声强相关，当成独立白噪声会让滤波器过度自信。
- 工程实现：Pronto（[论文](http://robots.ox.ac.uk/~mfallon/publications/2020FRONTIERS_camurri.pdf)）、ANYmal 的 kinematic-inertial 滤波器 TSIF（版本与参数**未核实**）。

### 2.2 VIO（视觉惯性）

- 代表：VINS-Fusion（[HKUST-Aerial-Robotics/VINS-Fusion](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion)）、OpenVINS（[rpng/open_vins](https://github.com/rpng/open_vins)）。
- 在四足上的真实表现：**平地慢走可用，剧烈运动不可用**。四足的角速度/线加速度是冲击型而非平滑型，IMU 预积分在冲击瞬间误差大；而俯仰/滚转本来就由接触可观测，VIO 增量有限。
- 正确姿势是紧耦合而非替代：VILENS 把视觉、LiDAR、IMU、腿部运动学放进因子图，并在线估计**线速度 bias** 压 leg odometry 漂移（[arXiv:2107.07243](https://arxiv.org/abs/2107.07243)）；Cerberus 是开源 VILO（stereo + IMU + 编码器 + 接触），带在线运动学标定与接触外点剔除（[arXiv:2209.07654](https://arxiv.org/abs/2209.07654)），两者均有真机实验。
- 传感器成本：双目 + IMU 几百到几千元级；算力 1–2 核或一路 GPU。

### 2.3 LIO（LiDAR 惯性）

- 代表：FAST-LIO2（[hku-mars/FAST_LIO](https://github.com/hku-mars/FAST_LIO)）、Point-LIO（[hku-mars/Point-LIO](https://github.com/hku-mars/Point-LIO)）。Point-LIO 卖点是"高带宽"：作者报告输出可达 **4–8 kHz** 量级（[Adv. Intell. Syst. 论文](https://advanced.onlinelibrary.wiley.com/doi/10.1002/aisy.202200459)），比 10 Hz 常规 LO 更扛落地冲击与快速转身。
- 代价：LiDAR 重量/功耗/价格，以及**楼梯、草丛、玻璃、粉尘下的退化**；点云配准假设场景静止，动态物体会留鬼影。
- 2025 年的正确融合姿势：LiDAR-IMU-**Leg** 紧耦合 + 足端触觉在线学习腿部运动学（[IEEE 2025](https://ieeexplore.ieee.org/document/11037541)）。

### 2.4 Learned 状态估计（2024–2026）

三条线：①**学习式 leg odometry / 接触表示**——网络从本体感受历史回归接触概率与足端速度，替掉阈值法接触检测，正面解决"GRF 对打滑不敏感"（[arXiv:2606.05501](https://arxiv.org/abs/2606.05501)，2026）；②学习式 leg odometry 直接喂策略做 terrain-aware locomotion（[IEEE 2025](https://ieeexplore.ieee.org/document/11247127)）；③**Deep IMU bias**——用网络推断 bias 当因子图先验（[arXiv:2211.04517](https://arxiv.org/abs/2211.04517)）。三者以真机实验为主，跨地形泛化边界**未核实**。

### 2.5 对比表（这是选型时真正要看的一页）

| 方案 | 典型输出频率 | 绝对精度（量级） | 传感器成本 | 算力 | **主要失效场景** |
|---|---|---|---|---|---|
| Contact-aided InEKF / Pronto | 200–1000 Hz（跟随 IMU） | 短时好，长时漂（分钟级米级） | 极低（IMU+编码器+足端开关） | <1 CPU 核 | 打滑、飞行相、接触误判、足端碰撞变形 |
| VIO（VINS-Fusion / OpenVINS） | 20–60 Hz | 中，尺度易退化 | 中（双目+IMU+同步） | 1–2 核 | 运动模糊、低纹理、光照突变、时间同步 |
| VILO 紧耦合（VILENS / Cerberus） | 10–50 Hz | 好（相对纯 leg odometry 显著降漂） | 中高 | 2–4 核 | 视觉与 LiDAR 同时退化（黑暗+空旷）、标定漂移 |
| LIO（FAST-LIO2 / Point-LIO） | 10–50 Hz（Point-LIO 可到 kHz 级） | 好（结构丰富场景） | 高（LiDAR） | 2–4 核 | 长廊/隧道几何退化、动态物体、雨雾粉尘 |
| Learned leg odometry | 50–200 Hz（网络推理） | 未核实（依赖训练分布） | 低 | GPU/边缘 NPU | 分布外地形、训练集未覆盖的接触模式 |

> 频率列是工程常用区间，不是某一篇论文的统一口径；只有 Point-LIO 的 4–8 kHz 是原文报告值。落地时以你实际 IMU 频率与滤波器实现为准。

---

## 3. 地形感知：高程图是四足的"中间语言"

一句话：**高程图（elevation map）是四足感知的事实标准，因为它同时喂得动运控（落脚点）和导航（代价地图）；难点不在建图，在"什么算可通行"。**

### 3.1 三个主流实现

| 方案 | 表示 | 更新频率（典型） | 算力 | 适用 | 备注 |
|---|---|---|---|---|---|
| [elevation_mapping_cupy](https://github.com/leggedrobotics/elevation_mapping_cupy) | 2.5D 高度图 + 多语义层 | 10–30 Hz（GPU） | Jetson 级 GPU | ANYmal 系 / 腿式运控 | ROS2 Jazzy 维护中；**默认 resolution 0.1 m、map_length 20 m**（[官方参数文档](https://leggedrobotics.github.io/elevation_mapping_cupy/usage/parameters.html)）；自带 traversability 层 + erosion 插件 |
| [grid_map](https://github.com/ANYbotics/grid_map) | 多层 2.5D 栅格（elevation/variance/normal…） | 10–30 Hz（CPU） | 1–2 CPU 核 | 与 ROS 生态结合最紧 | 有官方 costmap 桥（grid_map_costmap_2d），"高程图→Nav2"最短路径 |
| [nvblox](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox)（Isaac ROS） | TSDF / ESDF 体素 | 10–30 Hz（GPU） | NVIDIA GPU | 3D 避障、移动底盘+机械臂 | 3D 连续表示比 2.5D 更适合楼梯/悬空障碍；延迟指标**未核实** |

补充：多模态高程图 MEM（[arXiv:2309.16818](https://arxiv.org/abs/2309.16818)，IROS 2023）把颜色/语义层并进高程图，是"可通行性学习"的标准输入载体。

### 3.2 可通行性（traversability）：别用几何阈值糊弄

高程图本身只是几何。工程上真正决定成败的是 traversability 的算法：

- **几何法（必做基线）**：坡度（surface normal 与重力夹角）、台阶（相邻格高差）、粗糙度（局部方差）+ unknown 保守处理。阈值需实测标定（**未核实**）：坡 > 25–30° 算高代价，单步高差 > 0.10–0.15 m 算 lethal。
- **学习法（2024–2026 主流）**：高程图 patch + 本体感受历史回归"这一步踩下去会不会滑/卡"，输出连续代价；ANYmal 的 perceptive locomotion 直接把高程图喂策略（[arXiv:2201.08117](https://arxiv.org/abs/2201.08117)）。
- **反面教材（论文点名）**：雪、植被、水面在视觉上"像不可踩障碍"，或者干脆**没有回波**——这是野外感知型运动控制的主要失败源（同上摘要）。

### 3.3 盲走 vs 视觉感知：真实差距在哪

- 盲走（仅本体感受 + 接触记忆）在**平地、缓坡、已知台阶**上并不差，没有感知延迟与误检风险；很多商用狗的默认档就是盲走。差距只在**负障碍、高台、稀疏障碍物、乱石地**——必须靠 exteroception 提前看到。
- 工程结论：**双模并存 + 按地形置信度切换**，而不是"上了视觉就删掉盲走"。

---

## 4. 导航层：Nav2 能用到什么程度

一句话：**Nav2 能承担 2.5D 的全局/局部导航，但"腿式"的三个适配（3D 层、footprint、控制频率）必须自己做，否则就是一台跑得很快的轮式机器人。**

### 4.1 controller 选型

| 局部控制器 | 原理 | 典型频率 | 优点 | 四足上的坑 |
|---|---|---|---|---|
| **MPPI**（`nav2_mppi_controller`） | 采样 + 推演，批量轨迹加权 | 20–50 Hz（受 batch×steps 限制） | 处理非线性和动态障碍最好；参数直观（batch_size / time_steps / model_dt / critics） | 算力随 batch_size×time_steps 线性涨；默认 critics 组合偏向"贴路径"，需要给腿式加障碍/摆动余量约束 |
| **DWB** | 离散速度采样 + 评分 | 20–50 Hz | 轻、稳定、好调 | 只做局部避障，容易在窄缝/高代价区卡死；对地形起伏无感知 |
| **TEB** | 时间弹性带优化 | 10–20 Hz | 轨迹平滑、支持多拓扑 | Nav2 官方不含 TEB；ROS2 端口为社区维护，版本兼容性差；优化在动态场景易不可行 |

MPPI 官方参数与 critic 列表见 [Nav2 Jazzy 文档](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/)。**具体默认值随 Nav2 版本变动，落地前用 `ros2 param get` 核实**，不要照抄博客。

### 4.2 costmap 层配置（腿式适配的核心）

标准 `nav2_costmap_2d` 层：`static_layer` → `obstacle_layer`/`voxel_layer` → `inflation_layer`。腿式必须做的替换与加法：

1. **3D 感知 → 2.5D 代价**：用 [STVL（spatio-temporal voxel layer）](https://docs.nav2.org/jazzy/tutorials/general_tutorials/navigation2_with_stvl/) 替代 2D obstacle layer，才能吃下 3D LiDAR/深度点云并做体素衰减。
2. **高程图 → costmap 转换**（自写 layer plugin 或 grid_map 桥）：输入 `elevation`/`traversability`/`variance`；算坡度、台阶、粗糙度后归一化到 cost 0–252；`lethal (254)` 只留给确定不可通过（坡/台阶超阈值、unknown 且贴近机器人）。**分辨率必须对齐**：0.1 m 高程图喂 0.05 m costmap 时，双线性插值会在台阶边缘造出"假缓坡"，要用最近邻 + 形态学膨胀。
3. **footprint 与 inflation**：footprint 用**支撑多边形**（站立四点凸包）而非整机包络，否则窄缝全过不去；`inflation_radius` 按"机身半宽 + 一个步长"取——四足能跨过 10 cm 级障碍，按 LiDAR 安全距离取等于自我阉割。

### 4.3 全局规划与探索

| 规划器 | 类型 | 场景 | 状态 |
|---|---|---|---|
| NavFn / Smac Planner (2D/Analytic/Hybrid-A*) | 栅格/混合 A* | 室内、结构化地形 | Nav2 内置，够用 |
| [FAR Planner](https://github.com/MichaelFYang/far_planner) | 动态可见图 + "attemptable" 重规划 | 未知/部分已知环境，允许"先试再退" | [arXiv:2110.09460](https://arxiv.org/abs/2110.09460)，IROS 2022，ROS1 为主 |
| [TARE](https://github.com/caochao39/tare_planner) | 分层探索（局部细化 + 全局拓扑） | 大范围未知空间自主探索 | RSS 2021；ROS1（melodic-noetic 分支），ROS2 需自行移植 |
| ANYmal 式 3D 导航 | 高程图上的 MPC / 采样 | 野外 3D 地形，含台阶与陡坡 | 学术方案，未产品化，**代码可用性未核实** |

### 4.4 语义 / 语言导航（VLN）在四足上的落地程度

- **NaVid**（[arXiv:2402.15852](https://arxiv.org/abs/2402.15852)）：视频级 VLM 直接出下一步动作，训练用 **51 万条导航样本 + 76.3 万条网络数据**，卖点是绕开里程计噪声与地图/深度输入的 sim2real gap。
- **Uni-NaVid**（[arXiv:2412.06224](https://arxiv.org/abs/2412.06224)，RSS 2025）：把多种导航任务统一成一个 video-based VLA。
- **NavFoM**（[arXiv:2509.12129](https://arxiv.org/abs/2509.12129)）：导航基础模型，论文称约 **1270 万**训练样本（统计口径**未核实**）。
- **OpenNav**（[arXiv:2507.18033](https://arxiv.org/abs/2507.18033)）与 **ConceptGraphs**（[arXiv:2309.16650](https://arxiv.org/abs/2309.16650)）：前者 MLLM + 开放词汇做目标导航，后者是开放词汇 3D 场景图 + LLM 任务分解，构成"语义地图 → 长程任务"中间件。

**冷静判断**：这些系统的验证以**仿真基准为主、真机 demo 为辅**，且 demo 几乎都在低速室内短程；接到四足 50 Hz 运控上，瓶颈是**推理延迟（几百 ms 到秒级）与失败恢复**，不是模型能力。正确位置：VLN 只出"去哪个区域"的高层子目标，底层交给 Nav2/MPC。

---

## 5. 一套能跑的分层栈：频率与算力

| 层 | 典型频率 | 典型算力占用 | 关键接口 |
|---|---|---|---|
| IMU / 编码器 / 足端传感器 | 200–1000 Hz | — | 硬同步，时间戳统一到同一时钟 |
| 状态估计（腿式 EKF） | 200–1000 Hz | <1 CPU 核 | `odom → base` TF，协方差要真实 |
| VIO / LIO（可选，紧耦合） | 10–60 Hz | 1–4 CPU 核 / 一路 GPU | 提供漂移校正，不直接给运控 |
| 高程图（GPU） | 10–30 Hz | Jetson Orin 上 GPU 10–20%（**未核实**具体值） | `grid_map` 或点云 + 位姿 |
| 可通行性 / 代价层 | 10–30 Hz | 1 CPU 核 | costmap 0–255 |
| 全局规划 | 1–5 Hz | <1 核 | 路径 + 目标 |
| 局部控制（MPPI/DWB） | 20–50 Hz | 1–2 核（MPPI 更高） | `cmd_vel`（vx, vy, wz） |
| 运控策略 / WBC | 50–200 Hz（RL 策略常见 50 Hz；MPC/WBC 可到 200–500 Hz） | 1 核 / GPU | 关节目标 |

**整合时最常踩的四个坑**：
1. **时间同步**：高程图用了几十毫秒前的位姿 → 地图"拖影"，越走越歪；必须把位姿插值到点云时间戳。
2. **协方差造假**：`odom→base` 发 100 Hz 但协方差全写 1e-6，下游会把漂移当真理。
3. **分辨率不一致**：0.1 m 高程图直接喂 0.05 m costmap，台阶被插值抹平。
4. **Nav2 的平面假设**：坡度只能压进 cost，真 3D 落脚必须由运控层解决——两套系统要明确"谁负责台阶"。

---

## 6. 待交叉验证点

1. **Pronto / TSIF 的真实频率与延迟**：200–1000 Hz 是工程区间；ANYmal 机载 TSIF 的实际输出频率、相对高程图的延迟无官方数字，需查 Anybotics 文档或 VILENS 实验章节。
2. **elevation_mapping_cupy 在 Orin 上的帧率与 GPU 占用**：官方只给参数不给 benchmark，需自己跑 deterministic fusion 基准。
3. **Nav2 MPPI 在四足上的可用频率**：受 batch_size × time_steps、critic 数量与 CPU/GPU 影响，需本机实测（x86 与 Orin 差数倍）。
4. **learned leg odometry 的泛化边界**：跨狗/跨鞋/跨地面的公开对比未核实。
5. **TARE / FAR 的 ROS2 可用性**：主力分支仍是 ROS1，移植版维护状态需逐仓库确认。
