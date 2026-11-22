#!/usr/bin/env python3
"""
12 自由度四足：模型派控制器基准（力分配 + 关节 PD + 摆腿 IK）。

控制器结构（250 Hz）：
  1. 机身期望 wrench：高度 PD + 速度 PD + 姿态 PD
  2. 支撑足竖直力均分（含高度反馈），横向力用带摩擦锥裁剪的最小二乘求
  3. 支撑足 τ = -Jᵀf + 关节 PD（保持落脚点）
  4. 摆动足按 Raibert 落脚点做 IK，PD 跟踪

这不是论文级 convex MPC（没有滚动时域与线性化模型），而是它的"一步版"。
用途：量化模型派控制器在 MuJoCo 里能把机身稳住/走动到什么程度。

用法：
    python run_quad.py --mode stand --dur 5
    python run_quad.py --mode trot --dur 12 --vx 0.4
"""
import argparse
import json
import os

import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "quad12.xml")

LEGS = ["FR", "FL", "RR", "RL"]
PHASE_OFFSET = {"FR": 0.0, "RL": 0.0, "FL": 0.5, "RR": 0.5}

MASS_TOTAL = 6.0 + 4 * (0.15 + 0.75 + 0.35 + 0.05)
G = 9.81
MU = 0.6

Q_NOM = np.array([0.0, 0.7, -1.4] * 4)


class Quad:
    def __init__(self):
        self.m = mujoco.MjModel.from_xml_path(MODEL)
        self.d = mujoco.MjData(self.m)
        self.dt = self.m.opt.timestep
        self.nv = self.m.nv

        self.site = [mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_SITE, f"{l}_foot") for l in LEGS]
        self.leg_joints = [[mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, f"{l}_{n}")
                            for n in ("roll", "pitch", "knee")] for l in LEGS]
        self.leg_qadr = [[self.m.jnt_qposadr[j] for j in js] for js in self.leg_joints]
        self.leg_dadr = [[self.m.jnt_dofadr[j] for j in js] for js in self.leg_joints]
        self.hip_bodies = [mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, f"{l}_hip") for l in LEGS]
        self.torso = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, "torso")

        self.jacp = np.zeros((3, self.nv))
        self.jacr = np.zeros((3, self.nv))

    def reset(self, z):
        mujoco.mj_resetData(self.m, self.d)
        self.d.qpos[0:3] = [0, 0, z]
        self.d.qpos[3:7] = [1, 0, 0, 0]
        self.d.qpos[7:] = Q_NOM
        self.d.qvel[:] = 0
        mujoco.mj_forward(self.m, self.d)

    def foot_pos(self, i):
        return self.d.site_xpos[self.site[i]].copy()

    def foot_jac(self, i):
        mujoco.mj_jacSite(self.m, self.d, self.jacp, self.jacr, self.site[i])
        return self.jacp[:, self.leg_dadr[i]].copy()

    def ik(self, i, target_world, iters=12, damping=1e-3):
        """求第 i 条腿到达 target_world 的关节角。返回结果但不改变仿真状态。"""
        qa = self.leg_qadr[i]
        q_save = self.d.qpos[qa].copy()
        for _ in range(iters):
            err = target_world - self.foot_pos(i)
            if np.linalg.norm(err) < 1e-4:
                break
            J = self.foot_jac(i)
            dq = J.T @ np.linalg.solve(J @ J.T + damping * np.eye(3), err)
            self.d.qpos[qa] = self.d.qpos[qa] + np.clip(dq, -0.15, 0.15)
            mujoco.mj_kinematics(self.m, self.d)
        q_out = self.d.qpos[qa].copy()
        self.d.qpos[qa] = q_save
        mujoco.mj_kinematics(self.m, self.d)
        return q_out

    def body_state(self):
        pos = self.d.qpos[0:3].copy()
        quat = self.d.qpos[3:7].copy()
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, quat)
        R = R.reshape(3, 3)
        vel = np.zeros(6)
        mujoco.mj_objectVelocity(self.m, self.d, mujoco.mjtObj.mjOBJ_BODY, self.torso, vel, 0)
        return pos, R, vel[3:6].copy(), vel[0:3].copy()

    def solve_lateral(self, feet_world, Fxy_des, Tau, fz_each):
        """给定每只脚竖直力，求横向力，使合力/合力矩逼近期望。带摩擦锥裁剪。"""
        n = 4
        r_c = self.d.qpos[0:3]
        # 未知量：8 个横向力
        A = np.zeros((3, 2 * n))
        b = np.zeros(3)
        b[0] = Fxy_des[0]
        b[1] = Fxy_des[1]
        b[2] = Tau[2]
        for k in range(n):
            r = feet_world[k] - r_c
            A[0, 2 * k] = 1.0
            A[1, 2 * k + 1] = 1.0
            # Mz = r_x*f_y - r_y*f_x
            A[2, 2 * k] = -r[1]
            A[2, 2 * k + 1] = r[0]
        fxy, *_ = np.linalg.lstsq(A, b, rcond=None)
        f = np.zeros((n, 3))
        for k in range(n):
            fx, fy = fxy[2 * k], fxy[2 * k + 1]
            lim = MU * max(fz_each[k], 1.0)
            norm = np.hypot(fx, fy)
            if norm > lim:
                fx, fy = fx / norm * lim, fy / norm * lim
            f[k] = [fx, fy, fz_each[k]]
        return f


def gait_phase(t, period):
    return (t / period) % 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="stand", choices=["stand", "trot"])
    ap.add_argument("--dur", type=float, default=8.0)
    ap.add_argument("--vx", type=float, default=0.4)
    ap.add_argument("--period", type=float, default=0.5)
    ap.add_argument("--duty", type=float, default=0.6)
    ap.add_argument("--z0", type=float, default=0.275)
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--kz", type=float, default=120.0)
    ap.add_argument("--kv", type=float, default=18.0)
    ap.add_argument("--kp", type=float, default=60.0)
    args = ap.parse_args()

    q = Quad()
    q.reset(z=args.z0)

    ctrl_dt = 1.0 / 250.0
    n_sub = int(round(ctrl_dt / q.dt))
    n_steps = int(args.dur / ctrl_dt)

    kp_q, kd_q = args.kp, 1.5
    vx_tgt = args.vx if args.mode == "trot" else 0.0

    log = {k: [] for k in ["t", "vx", "vy", "vz", "z", "roll", "pitch", "vx_tgt", "n_stance"]}

    feet_now = [q.foot_pos(i) for i in range(4)]
    prev_stance = [True] * 4
    foothold = [q.foot_pos(i) for i in range(4)]
    q_ref = [Q_NOM[3 * i:3 * i + 3].copy() for i in range(4)]
    fell_at = None
    v_est = np.zeros(3)

    for step in range(n_steps):
        t = step * ctrl_dt
        pos, R, v_w, w_w = q.body_state()
        v_est = 0.9 * v_est + 0.1 * v_w

        if pos[2] < 0.12:
            fell_at = t
            break

        roll = np.arctan2(R[2, 1], R[2, 2])
        pitch = np.arctan2(-R[2, 0], np.sqrt(R[2, 1] ** 2 + R[2, 2] ** 2))

        # 步态
        stance = [True] * 4
        if args.mode == "trot":
            ph = gait_phase(t, args.period)
            for i, l in enumerate(LEGS):
                stance[i] = ((ph + PHASE_OFFSET[l]) % 1.0) < args.duty
            if sum(stance) < 2:  # 保护：至少两只脚支撑
                stance = [True, True, False, False]
        n_st = max(sum(stance), 1)

        # 期望机身力/力矩
        Fz_tot = MASS_TOTAL * G + args.kz * (args.z0 - pos[2]) - 15.0 * v_est[2]
        Fxy_des = np.array([args.kv * (vx_tgt - v_est[0]), args.kv * (0.0 - v_est[1])])
        Tau = np.array([-45.0 * roll - 2.5 * w_w[0],
                        -45.0 * pitch - 2.5 * w_w[1],
                        -8.0 * w_w[2]])
        fz_each = np.where(stance, Fz_tot / n_st, 0.0)
        f = q.solve_lateral(feet_now, Fxy_des, Tau, fz_each)

        if getattr(args, "debug", False) and step % 50 == 0:
            print(f"[dbg] t={t:.2f} vx={v_est[0]:+.3f} z={pos[2]:.3f} "
                  f"Fxy_des=({Fxy_des[0]:+.1f},{Fxy_des[1]:+.1f}) "
                  f"f_sum=({f[:,0].sum():+.1f},{f[:,1].sum():+.1f},{f[:,2].sum():+.1f}) "
                  f"n_st={n_st}", flush=True)

        # 摆腿目标
        swing_ref = [None] * 4
        if any(not s for s in stance):
            ph = gait_phase(t, args.period)
            for i, l in enumerate(LEGS):
                if stance[i]:
                    continue
                hip = q.d.xpos[q.hip_bodies[i]].copy()
                td = args.period * (1 - args.duty)
                s_prog = ((ph + PHASE_OFFSET[l]) % 1.0 - args.duty) / max(1 - args.duty, 1e-6)
                s_prog = np.clip(s_prog, 0, 1)
                target = hip + np.array([vx_tgt * td * 0.5 * (2 * s_prog - 1), 0.0, -0.25])
                target[2] += 0.08 * np.sin(np.pi * s_prog)
                swing_ref[i] = q.ik(i, target, iters=6)

        tau = np.zeros(q.m.nu)
        for i in range(4):
            qa, da = q.leg_qadr[i], q.leg_dadr[i]
            qd = q.d.qpos[qa]
            vd = q.d.qvel[da]
            if stance[i]:
                if not prev_stance[i]:
                    foothold[i] = q.foot_pos(i)
                    q_ref[i] = q.ik(i, foothold[i], iters=8)
                J = q.foot_jac(i)
                tau[3 * i:3 * i + 3] = J.T @ f[i] + kp_q * (q_ref[i] - qd) - kd_q * vd
            else:
                ref = swing_ref[i] if swing_ref[i] is not None else Q_NOM[3 * i:3 * i + 3]
                tau[3 * i:3 * i + 3] = kp_q * (ref - qd) - kd_q * vd
        prev_stance = stance[:]
        q.d.ctrl[:] = np.clip(tau, -24, 24)

        for _ in range(n_sub):
            mujoco.mj_step(q.m, q.d)
        feet_now = [q.foot_pos(i) for i in range(4)]

        if step % 5 == 0:
            log["t"].append(t)
            log["vx"].append(float(v_w[0]))
            log["vy"].append(float(v_w[1]))
            log["vz"].append(float(v_w[2]))
            log["z"].append(float(pos[2]))
            log["roll"].append(float(roll))
            log["pitch"].append(float(pitch))
            log["vx_tgt"].append(vx_tgt)
            log["n_stance"].append(int(sum(stance)))

    n = len(log["t"])
    settle = int(0.3 * n)
    def stat(key):
        a = np.array(log[key], dtype=float)
        return a[settle:] if n > settle else a

    summary = {
        "mode": args.mode,
        "vx_target": vx_tgt,
        "duration_s": float(args.dur),
        "fell": fell_at is not None,
        "fell_at_s": None if fell_at is None else round(float(fell_at), 3),
        "mean_vx": round(float(stat("vx").mean()), 3) if n else None,
        "vx_rmse": round(float(np.sqrt(((stat("vx") - vx_tgt) ** 2).mean())), 3) if n else None,
        "mean_height": round(float(stat("z").mean()), 4) if n else None,
        "height_std": round(float(stat("z").std()), 4) if n else None,
        "max_abs_roll_deg": round(float(np.degrees(np.abs(stat("roll")).max())), 1) if n else None,
        "max_abs_pitch_deg": round(float(np.degrees(np.abs(stat("pitch")).max())), 1) if n else None,
        "n_samples": n,
        "total_mass": round(MASS_TOTAL, 2),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    os.makedirs(args.outdir, exist_ok=True)
    tag = "stand" if args.mode == "stand" else f"trot_{args.vx:.1f}"
    with open(os.path.join(args.outdir, f"result_{tag}.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    np.savez(os.path.join(args.outdir, f"log_{tag}.npz"),
             **{k: np.array(v) for k, v in log.items()})


if __name__ == "__main__":
    main()
