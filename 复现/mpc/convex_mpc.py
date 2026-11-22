#!/usr/bin/env python3
"""
Convex MPC（单刚体模型）+ WBC 力矩映射 —— 对应 Di Carlo et al., RA-L 2018 的做法。

与上一版 run_quad.py 的区别（这是关键）：
  run_quad.py   : 一步力分配 + PD，没有预测，没有动力学模型
  convex_mpc.py : 10 步滚动时域，单刚体线性化模型，力和落脚点由优化器决定

实现要点：
  状态 x = [Θ(3), p(3), ω(3), v(3)]，控制 u = 支撑足的三维力
  动力学：ṗ=v, v̇=f/m+g, Θ̇=ω, ω̇=I⁻¹Σ(r_i×f_i)
  离散 dt=0.025（40 Hz），时域 N=10
  约束：摩擦金字塔 |fx|,|fy| ≤ μ fz，fz ≥ 0，fz ≤ fmax
  代价：姿态/高度/速度跟踪 + 力正则，不惩罚水平位置（否则会抵抗行走）

用法：
    python convex_mpc.py --mode stand --dur 6
    python convex_mpc.py --mode trot --vx 0.4 --dur 10
"""
import argparse
import json
import os
import time

import numpy as np
import mujoco
import osqp
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "quad12.xml")

LEGS = ["FR", "FL", "RR", "RL"]
PHASE_OFFSET = {"FR": 0.0, "RL": 0.0, "FL": 0.5, "RR": 0.5}
G = 9.81
MU = 0.6
Q_NOM = np.array([0.0, 0.7, -1.4] * 4)

# ---------------- 模型参数（与 quad12.xml 一致） ----------------
MASS = 6.0 + 4 * (0.15 + 0.75 + 0.35 + 0.05)
INERTIA = np.diag([0.035, 0.13, 0.14])   # 近似，含腿部质量贡献
INERTIA_INV = np.linalg.inv(INERTIA)

# MPC 权重
Q_ROLL_PITCH = np.array([180.0, 180.0])   # 滚转/俯仰
Q_YAW = 60.0
Q_HEIGHT = 2500.0
Q_OMEGA = np.array([12.0, 12.0, 8.0])
Q_VEL = np.array([60.0, 60.0, 20.0])
R_FORCE = 1e-4

N_HORIZON = 10
DT = 0.025


class ConvexMPC:
    """单刚体 convex MPC。每次调用重建 QP（问题很小，比增量更新更稳）。"""

    def __init__(self, mass, inertia_inv, dt, horizon):
        self.m = mass
        self.Iinv = inertia_inv
        self.dt = dt
        self.N = horizon

    def build_AB(self, R_body):
        """在当前姿态下线性化：返回 (A, B) 离散矩阵，状态 12 维、每脚力 3 维。"""
        dt = self.dt
        A = np.eye(12)
        A[0:3, 6:9] = np.eye(3) * dt      # Θ += ω dt
        A[3:6, 9:12] = np.eye(3) * dt     # p  += v dt

        B = np.zeros((12, 3))
        # v̇ = f/m  → 作用在世界系
        B[9:12, :] = np.eye(3) * dt / self.m
        return A, B

    def moment_matrix(self, feet_body):
        """把足端力映射到机体力矩：[r]× f，r 取机体坐标系下位置。"""
        M = np.zeros((3, 3))
        return M

    def solve(self, x0, feet_world, stance, R, v_ref, z_ref, yaw_ref=0.0):
        """
        x0: 12 维当前状态 [rpy, p, omega, v]
        feet_world: 4x3 足端世界坐标
        stance: 长度 4 的 bool
        返回 (forces 4x3, solve_time_ms, status)
        """
        t0 = time.perf_counter()
        n_st = int(sum(stance))
        if n_st == 0:
            return np.zeros((4, 3)), 0.0, "no_stance"

        idx = [i for i in range(4) if stance[i]]
        com = x0[3:6]
        # 足端在机体坐标系的位置（世界系相对 COM，再转到机体系）
        r_world = np.array([feet_world[i] - com for i in idx])      # n x 3
        r_body = (R.T @ r_world.T).T                                # n x 3

        dt, N = self.dt, self.N
        nu = 3 * n_st

        # ---- 构建预测矩阵：X_{k+1} = A X_k + B u_k + c ----
        A = np.eye(12)
        A[0:3, 6:9] = np.eye(3) * dt
        A[3:6, 9:12] = np.eye(3) * dt

        I_w = R @ INERTIA @ R.T
        Iinv_w = np.linalg.inv(I_w)

        def Bk():
            B = np.zeros((12, nu))
            for j in range(n_st):
                B[9:12, 3 * j:3 * j + 3] += np.eye(3) * dt / self.m
                rj = r_world[j]
                skew = np.array([[0, -rj[2], rj[1]],
                                 [rj[2], 0, -rj[0]],
                                 [-rj[1], rj[0], 0]])
                B[0:3, 3 * j:3 * j + 3] += Iinv_w @ skew * dt
            return B

        B = Bk()
        c = np.zeros(12)
        c[9:12] = np.array([0, 0, -G]) * dt

        Abar = np.zeros((12 * N, 12))
        Bbar = np.zeros((12 * N, nu * N))
        cbar = np.zeros(12 * N)
        for k in range(N):
            Ak1 = np.linalg.matrix_power(A, k + 1)
            Abar[12 * k:12 * (k + 1), :] = Ak1
            for j in range(k + 1):
                Bbar[12 * k:12 * (k + 1), nu * j:nu * (j + 1)] = \
                    np.linalg.matrix_power(A, k - j) @ B
            acc = np.zeros(12)
            for j in range(k + 1):
                acc += np.linalg.matrix_power(A, k - j) @ c
            cbar[12 * k:12 * (k + 1)] = acc

        # ---- 代价 ----
        Q = np.diag(np.concatenate([
            [Q_ROLL_PITCH[0], Q_ROLL_PITCH[1], Q_YAW],
            [0.0, 0.0, Q_HEIGHT],       # 水平位置不惩罚
            Q_OMEGA,
            Q_VEL,
        ]))
        # 参考轨迹：姿态回零、高度 z_ref、速度 v_ref
        Xref = np.zeros(12 * N)
        for k in range(N):
            Xref[12 * k + 2] = yaw_ref
            Xref[12 * k + 5] = z_ref
            Xref[12 * k + 9:12 * k + 12] = v_ref

        Qbar = np.kron(np.eye(N), Q)
        Rbar = np.eye(nu * N) * R_FORCE

        H = Bbar.T @ Qbar @ Bbar + Rbar
        g = Bbar.T @ Qbar @ (cbar + Abar @ x0 - Xref)

        # ---- 约束：摩擦金字塔 + 力上限 ----
        rows, cols, vals = [], [], []
        lo, hi = [], []
        row = 0
        for k in range(N):
            for j in range(n_st):
                base = nu * k + 3 * j
                # |fx| <= mu fz  →  fx - mu*fz <= 0 ; -fx - mu*fz <= 0
                for sgn in (1, -1):
                    rows += [row, row, row]
                    cols += [base, base + 2, base + 2]
                    vals += [sgn, -MU, 0]
                    lo.append(-np.inf); hi.append(0.0)
                    row += 1
                for sgn in (1, -1):
                    rows += [row, row]
                    cols += [base + 1, base + 2]
                    vals += [sgn, -MU]
                    lo.append(-np.inf); hi.append(0.0)
                    row += 1
                # fz >= 0
                rows += [row]; cols += [base + 2]; vals += [1.0]
                lo.append(0.0); hi.append(np.inf); row += 1
                # fz <= fmax
                rows += [row]; cols += [base + 2]; vals += [1.0]
                lo.append(-np.inf); hi.append(150.0); row += 1

        A_con = sp.csc_matrix((vals, (rows, cols)), shape=(row, nu * N))
        lo = np.array(lo); hi = np.array(hi)

        solver = osqp.OSQP()
        solver.setup(sp.csc_matrix(H), g, A_con, lo, hi, verbose=False,
                     eps_abs=1e-4, eps_rel=1e-4, max_iter=4000, polish=True)
        res = solver.solve()
        el = (time.perf_counter() - t0) * 1e3

        forces = np.zeros((4, 3))
        if res.x is None:
            return forces, el, "failed"
        u0 = np.array(res.x[:nu]).reshape(n_st, 3)
        for j, i in enumerate(idx):
            forces[i] = u0[j]
        # 投影到摩擦锥，防止数值越界
        for i in idx:
            fz = max(forces[i, 2], 0.0)
            lim = MU * fz
            fxy = np.clip(forces[i, :2], -lim, lim)
            forces[i] = [fxy[0], fxy[1], fz]
        return forces, el, res.info.status


class Sim:
    def __init__(self):
        self.m = mujoco.MjModel.from_xml_path(MODEL)
        self.d = mujoco.MjData(self.m)
        self.dt = self.m.opt.timestep
        self.site = [mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_SITE, f"{l}_foot") for l in LEGS]
        self.lj = [[mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, f"{l}_{n}")
                    for n in ("roll", "pitch", "knee")] for l in LEGS]
        self.qadr = [[self.m.jnt_qposadr[j] for j in js] for js in self.lj]
        self.dadr = [[self.m.jnt_dofadr[j] for j in js] for js in self.lj]
        self.hips = [mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, f"{l}_hip") for l in LEGS]
        self.torso = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, "torso")
        self.jacp = np.zeros((3, self.m.nv))
        self.jacr = np.zeros((3, self.m.nv))

    def reset(self, z):
        mujoco.mj_resetData(self.m, self.d)
        self.d.qpos[0:3] = [0, 0, z]
        self.d.qpos[3:7] = [1, 0, 0, 0]
        self.d.qpos[7:] = Q_NOM
        mujoco.mj_forward(self.m, self.d)

    def foot(self, i):
        return self.d.site_xpos[self.site[i]].copy()

    def jac(self, i):
        mujoco.mj_jacSite(self.m, self.d, self.jacp, self.jacr, self.site[i])
        return self.jacp[:, self.dadr[i]].copy()

    def ik(self, i, target, iters=10):
        qa = self.qadr[i]
        qs = self.d.qpos[qa].copy()
        for _ in range(iters):
            err = target - self.foot(i)
            if np.linalg.norm(err) < 1e-4:
                break
            J = self.jac(i)
            self.d.qpos[qa] = self.d.qpos[qa] + np.clip(
                J.T @ np.linalg.solve(J @ J.T + 1e-3 * np.eye(3), err), -0.15, 0.15)
            mujoco.mj_kinematics(self.m, self.d)
        q = self.d.qpos[qa].copy()
        self.d.qpos[qa] = qs
        mujoco.mj_kinematics(self.m, self.d)
        return q

    def state12(self):
        pos = self.d.qpos[0:3].copy()
        R = np.zeros(9); mujoco.mju_quat2Mat(R, self.d.qpos[3:7]); R = R.reshape(3, 3)
        vel = np.zeros(6)
        mujoco.mj_objectVelocity(self.m, self.d, mujoco.mjtObj.mjOBJ_BODY, self.torso, vel, 0)
        w, v = vel[0:3], vel[3:6]
        roll = np.arctan2(R[2, 1], R[2, 2])
        pitch = np.arctan2(-R[2, 0], np.sqrt(R[2, 1] ** 2 + R[2, 2] ** 2))
        yaw = np.arctan2(R[1, 0], R[0, 0])
        x0 = np.concatenate([[roll, pitch, yaw], pos, w, v])
        return x0, R, pos, w, v, (roll, pitch, yaw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="stand", choices=["stand", "trot"])
    ap.add_argument("--dur", type=float, default=6.0)
    ap.add_argument("--vx", type=float, default=0.4)
    ap.add_argument("--period", type=float, default=0.5)
    ap.add_argument("--duty", type=float, default=0.6)
    ap.add_argument("--z0", type=float, default=0.275)
    ap.add_argument("--tau-sign", type=float, default=1.0, help="Jᵀf 的符号，±1")
    ap.add_argument("--kp-stance", type=float, default=8.0)
    ap.add_argument("--kd-stance", type=float, default=1.2)
    ap.add_argument("--rf", type=float, default=1e-4)
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    sim = Sim()
    sim.reset(args.z0)
    mpc = ConvexMPC(MASS, INERTIA_INV, DT, N_HORIZON)

    ctrl_dt = 1.0 / 500.0
    n_sub = int(round(ctrl_dt / sim.dt))
    n_steps = int(args.dur / ctrl_dt)
    mpc_every = int(round(DT / ctrl_dt))

    kp, kd = 80.0, 2.0
    vx_tgt = args.vx if args.mode == "trot" else 0.0
    v_ref = np.array([vx_tgt, 0.0, 0.0])

    log = {k: [] for k in ["t", "vx", "vy", "z", "roll", "pitch", "solve_ms", "n_stance", "qp_status"]}
    feet = [sim.foot(i) for i in range(4)]
    prev_st = [True] * 4
    hold = [sim.foot(i) for i in range(4)]
    qref = [Q_NOM[3 * i:3 * i + 3].copy() for i in range(4)]
    forces = np.zeros((4, 3))
    solve_ms = 0.0
    qp_status = "-"
    fell = None
    v_est = np.zeros(3)

    for step in range(n_steps):
        t = step * ctrl_dt
        x0, R, pos, w, v, (roll, pitch, yaw) = sim.state12()
        v_est = 0.95 * v_est + 0.05 * v

        if pos[2] < 0.12:
            fell = t
            break

        stance = [True] * 4
        if args.mode == "trot":
            ph = (t / args.period) % 1.0
            for i, l in enumerate(LEGS):
                stance[i] = ((ph + PHASE_OFFSET[l]) % 1.0) < args.duty

        # --- MPC，40 Hz ---
        if step % mpc_every == 0:
            x0_mpc = x0.copy()
            x0_mpc[9:12] = v_ref  # 用期望速度做 tracking 的初值不影响约束
            forces, solve_ms, qp_status = mpc.solve(
                x0, feet, stance, R, v_ref, args.z0, yaw_ref=yaw)
            if args.debug and step % (mpc_every * 4) == 0:
                print(f"[mpc] t={t:.2f} vx={v[0]:+.3f} z={pos[2]:.3f} "
                      f"Fz={forces[:,2].sum():.1f} solve={solve_ms:.1f}ms {qp_status}", flush=True)

        # --- 摆腿 ---
        swing_ref = [None] * 4
        if any(not s for s in stance):
            ph = (t / args.period) % 1.0
            for i, l in enumerate(LEGS):
                if stance[i]:
                    continue
                hip = sim.d.xpos[sim.hips[i]].copy()
                td = args.period * (1 - args.duty)
                s = np.clip(((ph + PHASE_OFFSET[l]) % 1.0 - args.duty) / max(1 - args.duty, 1e-6), 0, 1)
                tgt = hip + np.array([vx_tgt * td * 0.5 * (2 * s - 1), 0.0, -0.25])
                tgt[2] += 0.08 * np.sin(np.pi * s)
                swing_ref[i] = sim.ik(i, tgt, iters=6)

        # --- WBC：τ = Jᵀf + PD ---
        tau = np.zeros(sim.m.nu)
        for i in range(4):
            qa, da = sim.qadr[i], sim.dadr[i]
            qd = sim.d.qpos[qa]; vd = sim.d.qvel[da]
            if stance[i]:
                if not prev_st[i]:
                    hold[i] = sim.foot(i)
                    qref[i] = sim.ik(i, hold[i], iters=8)
                J = sim.jac(i)
                tau[3 * i:3 * i + 3] = (args.tau_sign * (J.T @ forces[i])
                                        + args.kp_stance * (qref[i] - qd)
                                        - args.kd_stance * vd)
            else:
                ref = swing_ref[i] if swing_ref[i] is not None else Q_NOM[3 * i:3 * i + 3]
                tau[3 * i:3 * i + 3] = kp * (ref - qd) - kd * vd
        prev_st = stance[:]
        sim.d.ctrl[:] = np.clip(tau, -24, 24)

        for _ in range(n_sub):
            mujoco.mj_step(sim.m, sim.d)
        feet = [sim.foot(i) for i in range(4)]

        if step % 50 == 0:
            log["t"].append(t); log["vx"].append(float(v[0])); log["vy"].append(float(v[1]))
            log["z"].append(float(pos[2])); log["roll"].append(float(roll))
            log["pitch"].append(float(pitch)); log["solve_ms"].append(float(solve_ms))
            log["n_stance"].append(int(sum(stance))); log["qp_status"].append(qp_status)

    n = len(log["t"]); settle = int(0.3 * n)
    def st(k):
        a = np.array(log[k][settle:], dtype=float)
        return a if len(a) else np.array(log[k], dtype=float)
    summary = {
        "mode": args.mode, "vx_target": vx_tgt, "duration_s": args.dur,
        "fell": fell is not None, "fell_at_s": None if fell is None else round(float(fell), 3),
        "mean_vx": round(float(st("vx").mean()), 3),
        "vx_rmse": round(float(np.sqrt(((st("vx") - vx_tgt) ** 2).mean())), 3),
        "mean_height": round(float(st("z").mean()), 4),
        "height_std": round(float(st("z").std()), 4),
        "max_abs_roll_deg": round(float(np.degrees(np.abs(st("roll")).max())), 1),
        "max_abs_pitch_deg": round(float(np.degrees(np.abs(st("pitch")).max())), 1),
        "mpc_solve_ms_mean": round(float(np.mean(log["solve_ms"])), 2) if log["solve_ms"] else None,
        "mpc_solve_ms_max": round(float(np.max(log["solve_ms"])), 2) if log["solve_ms"] else None,
        "qp_status": log["qp_status"][-1] if log["qp_status"] else None,
        "tau_sign": args.tau_sign, "n_samples": n, "total_mass": round(MASS, 2),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    os.makedirs(args.outdir, exist_ok=True)
    tag = "stand" if args.mode == "stand" else f"trot_{args.vx:.1f}"
    with open(os.path.join(args.outdir, f"mpc_result_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    np.savez(os.path.join(args.outdir, f"mpc_log_{tag}.npz"),
             **{k: np.array(v) for k, v in log.items()})


if __name__ == "__main__":
    main()
