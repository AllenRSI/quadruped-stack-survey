# 03 · IsaacLab 复现方案（现代路线）

> **状态：未执行。** 本机显存 8 GB 低于 Isaac Sim 官方建议，不推荐硬试。
> 仓库：https://github.com/isaac-sim/IsaacLab

---

## 1. 定位

IsaacLab 是 Isaac Gym 的官方继任者（原 Orbit → IsaacLab），2026 年的事实上标准。**新项目应该用它，而不是 legged_gym。**

它的任务注册表里直接有 `Isaac-Velocity-Flat-Anymal-C-v0`、`Isaac-Velocity-Rough-Anymal-D-v0` 等，跑通一条就等于拿到了后续所有 task 的模板。

---

## 2. 硬件门槛（这是本机的问题所在）

| 项 | 官方建议 | 本机 |
|---|---|---|
| GPU 显存 | **16 GB 以上** | 8 GB ❌ |
| 磁盘 | 30 GB+ | 80 GB ✅ |
| 驱动 | 较新 | 610.88 ✅ |

8 GB 不是绝对不能启动，而是常见结果是：能加载场景，训练几步后 OOM，或渲染时崩。**时间会全花在 debug 显存上，而不是理解方法。**

---

## 3. 步骤（在满足显存的机器上）

```bash
# 1) Python 3.10
conda create -n isaaclab python=3.10 -y && conda activate isaaclab

# 2) Isaac Sim（pip 方式，约 10–15 GB）
pip install --upgrade pip
pip install "isaacsim[all]==4.5.0" --extra-index-url https://pypi.nvidia.com

# 3) Isaac Lab
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
./isaaclab.sh --install          # Linux/macOS
# Windows: isaaclab.bat --install

# 4) 训练
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-Flat-Anymal-C-v0 --headless --num_envs=2048
```

> 版本号（4.5.0 / 任务名 / 脚本路径）会随 IsaacLab 版本变，**落地前以仓库 README 和 `source/isaaclab_tasks` 的注册表为准**。这几条我未在本机核实。

---

## 4. 判据

| 阶段 | 判据 |
|---|---|
| 环境通 | `./isaaclab.sh --check` 通过，能无头启动 |
| 渲染通 | 开 viewer 看到 Anymal 站立 |
| 训练通 | 500 iteration 内 reward 上升、无 OOM |
| 会走 | play 模式跟速度指令走 |

---

## 5. 已知坑

1. **Windows 支持弱**——官方主推 Linux，Windows 上很多脚本要手动改
2. **Isaac Sim 首次启动会编译 shader**，10–30 分钟，看起来像卡死
3. **`omni` 模块导入失败**——通常是 `isaacsim` 装到了错误的 Python 环境
4. **8 GB 卡的实际表现**：能跑 `num_envs=256` 左右的极简配置，但没有复现意义

---

## 6. 如果一定要在本机跑

两个现实选项：

- **租云 GPU**：A10 / 4090 / A100，按小时计费。跑一次平地任务 1–2 小时，成本可控。
- **降级到 mujoco_playground**：见 [02](02-mujoco_playground-实机可行的轻量路线.md)，先建立直觉，不追数字。

**不建议**为了在本机跑 IsaacLab 去折腾 WSL + 虚拟显存，投入产出比很差。
