# 02 · mujoco_playground：本机唯一可能跑通的路

> **状态：未执行。** 本机网络下 pypi 不可用（≈15 KB/s），装不了依赖。
> 仓库：https://github.com/google-deepmind/mujoco_playground

---

## 1. 为什么是它

| 对比项 | legged_gym | IsaacLab | **mujoco_playground** |
|---|---|---|---|
| 是否需 NVIDIA 账号 | 是 | 否 | **否** |
| 安装体积 | 中 | 15 GB+ | **小（~1 GB）** |
| 8 GB 显存能否跑 | 勉强 | 很难 | **能** |
| 是否活跃 | 停更 18 个月 | 最活跃 | 活跃（2026-11 仍有提交） |
| 依赖闭源组件 | Isaac Gym | Isaac Sim | **无，纯开源** |

它用 MuJoCo 的 MJX（JAX 重写版）做 GPU 并行，内置 Go1 / Go2 / Barkour 等四足环境和 PPO 训练脚本。

---

## 2. 步骤

```bash
# 1) Python 3.10+（本机没有，先装）
winget install Python.Python.3.11
# 或从 python.org 下安装包，注意别用 Microsoft Store 版本

# 2) 配国内镜像，否则装不动
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
# 先测速：pip download numpy --no-deps -d /tmp/x

# 3) 拉仓库
git clone https://github.com/google-deepmind/mujoco_playground.git
cd mujoco_playground

# 4) 装依赖（推荐 uv，失败则退回 pip）
pip install -e .
# 若需要 GPU 版 jax：
pip install -U "jax[cuda12]"

# 5) 验证 GPU 可见
python -c "import jax; print(jax.devices())"   # 应打印 gpu
```

训练与可视化的具体脚本名，**以仓库 README 为准**——我没有在本机核实到命令级，不写猜测的命令。典型形态是 `learning/train_jax_ppo.py --env_name=<任务名>`。

---

## 3. 判据

| 阶段 | 判据 |
|---|---|
| 环境通 | `jax.devices()` 返回 GPU |
| 能渲染 | MuJoCo 打开 Go1 场景不崩 |
| 能训练 | 100 iteration 内 reward 上升、无 NaN |
| 会走 | 策略能跟随机速度指令，摔倒率明显下降 |

---

## 4. 风险

1. **CUDA 版 jax 体积大**（数百 MB），弱网下仍是主要障碍
2. **MJX 与原生 MuJoCo 的物理差异**：sim2sim 时会有行为漂移，这是正常的，不要当 bug
3. **它不是论文级 benchmark**：跑通它证明「链路可用」，不能用来反驳 legged_gym 的数字

---

## 5. 建议用法

把它当作**学习与验证工具**，而不是复现目标：

- 用来理解 PPO + 域随机化在四足上的最小闭环
- 用来快速试 reward 设计，不用等 Isaac Gym 那种重装备
- 想认真复现论文数字时，还是得上 legged_gym / IsaacLab（或租云卡）
