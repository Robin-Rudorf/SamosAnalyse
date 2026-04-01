#!/usr/bin/env python3
"""
stability_pub4.py
-----------------
Same as stability_pub3.py, but fixes time-unit mismatches by introducing a TIME_SCALE.

Why:
Some pipelines store the first column in O(t) CSVs as "frame index" rather than true simulation steps.
If your O(t) file times are in frames (saved every dump_every steps), set TIME_SCALE = dump_every
so all plots and switching times are reported in true simulation steps.

Key parameters:
  TIME_SCALE          : multiply the CSV time column by this to get steps
  TRANSIENT_CUT_STEPS : observation window start, in true simulation steps

Outputs: see stability_pub3.py (written under ./stability_pub_out/)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# ======================
# USER SETTINGS
# ======================
TIME_SERIES_DIRNAME = "time_series"   # set "" to search current folder only
GLOB_PATTERN = "*.csv"

# If your CSV time is in frames (e.g. every 10 steps), set TIME_SCALE=10
TIME_SCALE = 1.0

# Order threshold + hysteresis guard
O_HIGH = 0.80
HOLD_POINTS = 10

# Observation window start in TRUE simulation steps
TRANSIENT_CUT_STEPS = 150_000

# Plot aesthetics
DPI = 260
FONTSIZE = 12
TITLE_FONTSIZE = 13
LINEWIDTH = 2.2
MAX_SURVIVAL_CURVES = 8
CMAP_NAME = "viridis"
# ======================


@dataclass
class RunRecord:
    path: Path
    cc: Optional[int]
    rand: Optional[int]
    tau: Optional[float]
    permult: Optional[float]
    J: Optional[float]
    T_end: float
    O_at_t0: float
    ordered_at_t0: bool
    final_ordered: bool
    t_switch: Optional[float]
    switched: bool
    censored: bool


def parse_params_from_filename(name: str) -> Dict[str, Optional[float]]:
    tokens = name.replace(".csv", "").split(";")
    out: Dict[str, Optional[float]] = {"cc": None, "rand": None, "tau": None, "permult": None}
    for tok in tokens:
        if tok.startswith("cc_"):
            out["cc"] = int(tok.split("_", 1)[1])
        elif tok.startswith("rand_"):
            out["rand"] = int(tok.split("_", 1)[1])
        elif tok.startswith("tau_"):
            out["tau"] = float(tok.split("_", 1)[1])
        elif tok.startswith("permult_"):
            out["permult"] = float(tok.split("_", 1)[1])
    return out


def read_timeseries_csv(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(path, header=None)
    if df.shape[1] < 2:
        raise ValueError(f"{path}: expected >=2 columns (time, O)")
    t_raw = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
    O = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(t_raw) & np.isfinite(O)
    t_raw, O = t_raw[mask], O[mask]
    if len(t_raw) < 5:
        raise ValueError(f"{path}: too few valid samples")
    # Convert to TRUE steps
    t = t_raw * float(TIME_SCALE)
    idx = np.argsort(t)
    return t[idx], O[idx]


def first_sustained_crossing(t: np.ndarray, O: np.ndarray, thresh: float, hold: int) -> Optional[float]:
    if len(O) < hold:
        return None
    above = (O >= thresh).astype(np.int32)
    conv = np.convolve(above, np.ones(hold, dtype=np.int32), mode="valid")
    hits = np.where(conv == hold)[0]
    if len(hits) == 0:
        return None
    return float(t[int(hits[0])])


def kaplan_meier(times: np.ndarray, censored: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    order = np.argsort(times)
    times = times[order]
    censored = censored[order]

    uniq = np.unique(times)
    at_risk = len(times)
    S = 1.0
    t_out, S_out = [], []

    for tu in uniq:
        mask = (times == tu)
        d = int((~censored[mask]).sum())
        c = int((censored[mask]).sum())
        if at_risk > 0 and d > 0:
            S *= (1.0 - d / at_risk)
            t_out.append(float(tu))
            S_out.append(float(S))
        at_risk -= (d + c)

    if not t_out:
        t0, t1 = float(np.min(times)), float(np.max(times))
        if t0 == t1:
            t0, t1 = TRANSIENT_CUT_STEPS, float(np.max(times))
        return np.array([t0, t1], dtype=float), np.array([1.0, 1.0], dtype=float)

    return np.array(t_out, dtype=float), np.array(S_out, dtype=float)


def downsample(vals: List[float], k: int) -> List[float]:
    if len(vals) <= k:
        return vals
    idx = np.linspace(0, len(vals) - 1, k).round().astype(int)
    return [vals[i] for i in idx]


def compute_run_record(path: Path) -> RunRecord:
    params = parse_params_from_filename(path.name)
    t, O = read_timeseries_csv(path)
    T_end = float(np.max(t))

    tau = params["tau"]
    J = (1.0 / tau) if (tau is not None and tau > 0) else None

    # O at t0 (start of observation window)
    idx0 = np.where(t >= TRANSIENT_CUT_STEPS)[0]
    if len(idx0) == 0:
        O_t0 = float(O[-1])
    else:
        i0 = int(idx0[0])
        i1 = min(len(O), i0 + HOLD_POINTS)
        O_t0 = float(np.mean(O[i0:i1]))
    ordered_t0 = bool(np.isfinite(O_t0) and O_t0 >= O_HIGH)

    # final ordered from last 20% (robust)
    t_min = float(np.min(t))
    late_mask = (t >= (t_min + 0.9 * (T_end - t_min)))
    O_late = float(np.mean(O[late_mask])) if late_mask.sum() else float("nan")
    final_ordered = bool(np.isfinite(O_late) and O_late >= O_HIGH)

    # switching time after t0
    sw_mask = (t >= TRANSIENT_CUT_STEPS)
    t_sw = None
    if sw_mask.sum() >= HOLD_POINTS:
        t_sw = first_sustained_crossing(t[sw_mask], O[sw_mask], O_HIGH, HOLD_POINTS)

    if ordered_t0:
        switched = False
        censored = False
    else:
        switched = (t_sw is not None)
        censored = (t_sw is None)

    return RunRecord(
        path=path,
        cc=int(params["cc"]) if params["cc"] is not None else None,
        rand=int(params["rand"]) if params["rand"] is not None else None,
        tau=float(tau) if tau is not None else None,
        permult=float(params["permult"]) if params["permult"] is not None else None,
        J=float(J) if J is not None else None,
        T_end=T_end,
        O_at_t0=O_t0,
        ordered_at_t0=ordered_t0,
        final_ordered=final_ordered,
        t_switch=t_sw,
        switched=switched,
        censored=censored,
    )


def main():
    base = Path(".").resolve()
    ts_dir = base / TIME_SERIES_DIRNAME if TIME_SERIES_DIRNAME else base
    if not ts_dir.exists():
        raise SystemExit(f"Could not find time-series directory: {ts_dir}")

    files = sorted([p for p in ts_dir.glob(GLOB_PATTERN) if p.is_file()])
    files = [p for p in files if ("cc_" in p.name and "tau_" in p.name and "permult_" in p.name)]
    if not files:
        raise SystemExit(f"No time-series files found in {ts_dir}.")

    out_dir = base / "stability_pub_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({"font.size": FONTSIZE})

    recs: List[RunRecord] = []
    for fp in files:
        try:
            recs.append(compute_run_record(fp))
        except Exception as e:
            print(f"[WARN] Skipping {fp.name}: {e}")
    if not recs:
        raise SystemExit("No valid runs parsed.")

    df = pd.DataFrame([r.__dict__ for r in recs])
    df.to_csv(out_dir / "runs_parsed.csv", index=False)

    # Aggregate (permult, cc, J)
    # 3-way outcome fractions relative to t0
    agg = df.groupby(["permult", "cc", "tau", "J"], dropna=False).agg(
        n_runs=("tau", "size"),
        frac_final_ordered=("final_ordered", "mean"),
        frac_ordered_at_t0=("ordered_at_t0", "mean"),
        frac_switched=("switched", "mean"),
        frac_censored=("censored", "mean"),
    ).reset_index().sort_values(["permult", "cc", "J"])

    # median switching time among switched only
    df_sw = df[df["switched"] & df["t_switch"].notna()].copy()
    med = df_sw.groupby(["permult", "cc", "tau", "J"], dropna=False)["t_switch"].median().rename("median_t_switch")
    agg = agg.merge(med.reset_index(), on=["permult", "cc", "tau", "J"], how="left")

    agg.to_csv(out_dir / "stability_agg.csv", index=False)

    # One set per group
    for (perm, cc), agg_g in agg.groupby(["permult", "cc"], dropna=False):
        df_g = df[(df["permult"] == perm) & (df["cc"] == cc)].copy()
        tag = f"permult{perm:g}__cc{int(cc)}" if pd.notna(cc) else f"permult{perm:g}"
        subtitle = f"permult={perm:g}, cc={int(cc)}" if pd.notna(cc) else f"permult={perm:g}"

        # final fraction vs J
        g = agg_g.dropna(subset=["J"]).sort_values("J")
        fig = plt.figure(figsize=(7.6, 5.0))
        ax = fig.add_subplot(111)
        ax.plot(g["J"], g["frac_final_ordered"], marker="o", linewidth=LINEWIDTH)
        ax.set_xlabel("J")
        ax.set_ylabel("final ordered fraction")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)
        ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
        fig.tight_layout()
        fig.savefig(out_dir / f"frac_final_ordered_vs_J__{tag}.png", dpi=DPI)
        plt.close(fig)

        # median switching time vs J
        fig = plt.figure(figsize=(7.6, 5.0))
        ax = fig.add_subplot(111)
        g2 = g.dropna(subset=["median_t_switch"])
        ax.plot(g2["J"], g2["median_t_switch"], marker="o", linewidth=LINEWIDTH)
        ax.set_xlabel("J")
        ax.set_ylabel("median $t_{switch}$ (steps)")
        ax.set_ylim(TRANSIENT_CUT_STEPS, None)  # correct baseline at t0
        ax.grid(True, alpha=0.3)
        ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
        fig.tight_layout()
        fig.savefig(out_dir / f"median_tswitch_vs_J__{tag}.png", dpi=DPI)
        plt.close(fig)

        # bars (3-way) vs J
        fig = plt.figure(figsize=(8.2, 5.2))
        ax = fig.add_subplot(111)
        x = np.arange(len(g))
        a = g["frac_ordered_at_t0"].to_numpy(float)
        b = g["frac_switched"].to_numpy(float)
        c = g["frac_censored"].to_numpy(float)

        col_a = "#0072B2"   # blue
        col_b = "#E69F00"   # orange
        col_c = "#999999"   # gray
        ax.bar(x, a, color=col_a, label="ordered at $t_0$")
        ax.bar(x, b, bottom=a, color=col_b, label="switched")
        ax.bar(x, c, bottom=a+b, color=col_c, label="censored")

        ax.set_xticks(x)
        ax.set_xticklabels([f"{v:.2f}" for v in g["J"]], rotation=45, ha="right")
        ax.set_xlabel("J")
        ax.set_ylabel("fraction")
        ax.set_ylim(0, 1.02)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
        ax.legend(frameon=False, bbox_to_anchor=(1.02, 1), loc="upper left")
        fig.tight_layout()
        fig.savefig(out_dir / f"outcomes_bars__{tag}.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

        # survival curves (unconditional S(t) = P(still unordered at time t)), colored by J
        # Downsample if many levels
        levels = g.dropna(subset=["tau","J"]).sort_values("J")[["tau","J"]].to_records(index=False)
        levels = list(levels)
        if len(levels) > MAX_SURVIVAL_CURVES:
            levels = downsample(levels, MAX_SURVIVAL_CURVES)

        cmap = mpl.cm.get_cmap(CMAP_NAME)
        J_vals = [float(rec[1]) for rec in levels]
        norm = mpl.colors.Normalize(vmin=min(J_vals), vmax=max(J_vals))

        fig = plt.figure(figsize=(8.2, 5.2))
        ax = fig.add_subplot(111)
        T_end_group = float(np.nanmax(df_g["T_end"].to_numpy(dtype=float)))
        ax.set_xlim(TRANSIENT_CUT_STEPS, T_end_group)

        for tau_val, J_val in levels:
            sub = df_g[df_g["tau"] == float(tau_val)].copy()
            if sub.empty:
                continue
            at_risk = sub[~sub["ordered_at_t0"]].copy()
            f0 = float(len(at_risk)/len(sub))
            if f0 == 0.0:
                continue
            t_event = at_risk["t_switch"].to_numpy(dtype=float)
            cens = ~np.isfinite(t_event)
            times = np.where(np.isfinite(t_event), t_event, at_risk["T_end"].to_numpy(dtype=float))
            t_km, S_cond = kaplan_meier(times, cens)
            S_uncond = f0 * S_cond
            ax.step(t_km, S_uncond, where="post", linewidth=LINEWIDTH, color=cmap(norm(J_val)))

        ax.set_xlabel("t (steps)")
        ax.set_ylabel("S(t)")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)
        ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
        sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("J", rotation=90)
        fig.tight_layout()
        fig.savefig(out_dir / f"survival__{tag}.png", dpi=DPI, bbox_inches="tight")
        plt.close(fig)

    print("[OK] Done. If your plot baseline looked like 1.5e6, set TIME_SCALE appropriately and rerun.")
    print("      TIME_SCALE=", TIME_SCALE, "TRANSIENT_CUT_STEPS=", TRANSIENT_CUT_STEPS)


if __name__ == "__main__":
    main()
