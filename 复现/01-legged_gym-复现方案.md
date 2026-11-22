# 01 · legged_gym 复现方案（经典路线）

> **状态：未执行。** 本文是可执行方案，不是实验结果。
> 论文：Rudin et al., *Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning*, arXiv:2109.11978
> 仓库：https://github.com/leggedrobotics/legged_gym

---

## 1. 为什么选它

它是 2021 年之后整个四足 RL 生态的母体：RMA、DreamWaQ、HIMLoco、Extreme Parkour 的代码几乎都从它 fork 出来。**跑通它 = 打通了理解后续 80% 工作的路。**

代价是它锁死在**已停止维护的 Isaac Gym Preview 4** 上——这也是它 2025-05 之后停更的原因。

---

## 2. 硬依赖

| 项 | 要求 | 备注 |
|---|---|---|
| GPU | NVIDIA，≥8 GB 可用 | 默认 4096 环境是给 24 GB 卡写的，8 GB 要降环境数 |
| 驱动 | 支持 CUDA 11.7 即可 | 本机 610.88 满足 |
| Python | **3.8** | 3.10+ 会踩依赖兼容问题 |
| PyTorch | 1.13 + cu117 | Isaac Gym Preview 4 的官方配套 |
| Isaac Gym | Preview 4 | **需 NVIDIA 开发者账号登录下载**，无公开直链 |
| 系统 | Linux 原生最佳 | Windows 需 WSL2；本机没有 WSL |

---

## 3. 步骤（Linux / WSL2 下执行）

```bash
# 1) 环境
conda create -n legged python=3.8 -y
conda activate legged
pip install torch==1.13.1+cu117 torchvision==0.14.1+cu117 \
  --extra-index-url https://download.pytorch.org/whl/cu117

# 2) Isaac Gym（先从 developer.nvidia.com/isaac-gym/download 手动下载 Preview 4）
tar -xzf IsaacGym_Preview_4_Package.tar.gz
cd isaacgym/python && pip install -e .
python -c "import isaacgym"        # 必须无报错再往下

# 3) legged_gym
cd ../..
git clone https://github.com/leggedrobotics/legged_gym.git
cd legged_gym && pip install -e .
cd ..

# 4) rsl_rl
git clone https://github.com/leggedrobotics/rsl_rl.git
cd rsl_rl
git checkout v1.0.2                 # 版本与 legged_gym 对齐，勿用 main
pip install -e .
cd ..

# 5) 训练（先用小环境数验证链路，再放大）
cd legged_gym
python legged_gym/scripts/train.py --task=anymal_c_flat --headless --num_envs=1024
```

> 任务名以仓库里 `legged_gym/envs/__init__.py` 的注册表为准（`anymal_b_flat` / `anymal_c_flat` / `anymal_c_rough` 等）。**这一条我未在本机核实，属记忆**——落地前先 `grep` 注册表。

---

## 4. 预期结果与判据

| 阶段 | 判据 | 论文口径 |
|---|---|---|
| 链路通 | `train.py` 跑满 50 iteration 无 OOM、无 NaN | — |
| 会走 | 平地任务，reward 曲线在 300–500 iteration 后趋稳 | 论文称平地 <4 分钟（单卡） |
| 能玩 | `play.py` 加载 checkpoint，狗不摔、能跟速度指令 | — |

**本机预期（3060 Ti 8 GB，1024 环境）**：平地约 30–90 分钟；崎岖地形 3–6 小时。**这是估算，不是实测。**

---

## 5. 已知会踩的坑

1. **Isaac Gym 安装报 `libpython` 或 GLIBC 错误** —— Preview 4 对 Ubuntu 22.04+ 不友好，常见解法是退回 20.04 或打补丁。
2. **`numpy` 版本冲突** —— Isaac Gym 要求 `numpy<1.24`，新版 pip 会装到 2.x，需手动钉版本。
3. **OOM** —— 4096 环境在 8 GB 卡上必炸。从 512 起，逐次翻倍找上限。
4. **CUDA 版本错配** —— Isaac Gym 用自己编译的 CUDA 运行时，torch 版本必须匹配 11.7。
5. **Windows 原生跑不了** —— 必须 WSL2 或 Linux。

---

## 6. 跑通之后该记什么

一份 `复现/legged_gym/复现报告.md`，至少包含：

- `pip freeze` 全文 + `nvidia-smi` 输出
- 实际用的 `num_envs` 与显存峰值
- reward 曲线截图与收敛 iteration
- 与论文「<4 分钟 / 20 分钟」的对比：差多少、为什么（环境数？GPU？）
- 失败记录：哪一步卡了多久、怎么解决的
