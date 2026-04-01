#!/usr/bin/env python3
"""
stability_pub.py
----------------
Publication-style stability analysis from O(t) time series files.

Place this script in a folder that contains:
  - compute_order.csv  (optional; not required for this script)
  - a subfolder "time_series/" with per-run CSV files, OR the per-run CSVs directly.

Expected time-series CSV format (no header):
  col0 = time (simulation step or tau-like time axis)
  col1 = O(t)

Expected filename pattern (same as your pipeline):
  cc_1024;rand_1;tau_0.17;v0_0.05;k_1.0;nu_0.1;gamma_0.1;permult_2.8;line_0.1.csv

Outputs (created under ./stability_pub_out/):
  - runs_parsed.csv
  - stability_agg.csv
  - line_frac_final_ordered_vs_J.png
  - line_median_switch_time_vs_J.png
  - survival_curves.png
  - bars_switched_vs_censored.png
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ======================
# USER SETTINGS
# ======================
TIME_SERIES_DIRNAME = "time_series"     # set to "" to search current folder only
GLOB_PATTERN = "*.csv"

O_LOW = 0.20
O_HIGH = 0.80
HOLD_POINTS = 10

TRANSIENT_CUT = 150_000
EARLY_WINDOW = 30_000

USE_J_DIRECT = False  # if True, you must encode J in filenames and extend parser

SURVIVAL_MAX_CURVES = 5

DPI = 220
FONTSIZE = 12
TITLE_FONTSIZE = 14
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
    O_early: float
    O_late: float
    started_unordered: bool
    final_ordered: bool
    switched_U_to_O: bool
    t_switch: Optional[float]
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
    t = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
    O = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(t) & np.isfinite(O)
    t, O = t[mask], O[mask]
    if len(t) < 5:
        raise ValueError(f"{path}: too few valid samples")
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


def compute_run_record(path: Path) -> RunRecord:
    params = parse_params_from_filename(path.name)
    t, O = read_timeseries_csv(path)

    T_end = float(np.max(t))
    T_min = float(np.min(t))

    early_mask = (t >= T_min) & (t <= T_min + EARLY_WINDOW)
    if early_mask.sum() < 3:
        early_mask = (t <= T_min + max(EARLY_WINDOW, (T_end - T_min) * 0.1))
    O_early = float(np.mean(O[early_mask])) if early_mask.sum() else float("nan")

    late_mask = (t >= TRANSIENT_CUT)
    if late_mask.sum() < 5:
        late_mask = (t >= (T_min + 0.8 * (T_end - T_min)))
    O_late = float(np.mean(O[late_mask])) if late_mask.sum() else float("nan")

    started_unordered = bool(np.isfinite(O_early) and (O_early <= O_LOW))
    final_ordered = bool(np.isfinite(O_late) and (O_late >= O_HIGH))

    sw_mask = (t >= TRANSIENT_CUT)
    t_sw = None
    if sw_mask.sum() >= HOLD_POINTS:
        t_sw = first_sustained_crossing(t[sw_mask], O[sw_mask], O_HIGH, HOLD_POINTS)

    censored = (t_sw is None)
    switched = started_unordered and (t_sw is not None)

    tau = params["tau"]
    if USE_J_DIRECT:
        J = None
    else:
        J = (1.0 / tau) if (tau is not None and tau > 0) else None

    return RunRecord(
        path=path,
        cc=int(params["cc"]) if params["cc"] is not None else None,
        rand=int(params["rand"]) if params["rand"] is not None else None,
        tau=float(tau) if tau is not None else None,
        permult=float(params["permult"]) if params["permult"] is not None else None,
        J=float(J) if J is not None else None,
        T_end=T_end,
        O_early=O_early,
        O_late=O_late,
        started_unordered=started_unordered,
        final_ordered=final_ordered,
        switched_U_to_O=switched,
        t_switch=t_sw,
        censored=censored,
    )


def pick_survival_levels(agg: pd.DataFrame, key: str) -> List[float]:
    df = agg.dropna(subset=[key, "frac_final_ordered"]).sort_values(key)
    if df.empty:
        return []
    mid = df[(df["frac_final_ordered"] > 0.05) & (df["frac_final_ordered"] < 0.95)]
    levels = mid[key].tolist()
    if len(levels) < SURVIVAL_MAX_CURVES:
        levels = df[key].tolist()
    if len(levels) > SURVIVAL_MAX_CURVES:
        idx = np.linspace(0, len(levels) - 1, SURVIVAL_MAX_CURVES).round().astype(int)
        levels = [levels[i] for i in idx]
    return levels


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
        return np.array([float(np.min(times)), float(np.max(times))]), np.array([1.0, 1.0])
    return np.array(t_out), np.array(S_out)


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

    records: List[RunRecord] = []
    for fp in files:
        try:
            records.append(compute_run_record(fp))
        except Exception as e:
            print(f"[WARN] Skipping {fp.name}: {e}")

    if not records:
        raise SystemExit("No valid runs parsed.")

    df = pd.DataFrame([r.__dict__ for r in records])
    cols = ["path", "cc", "rand", "permult", "tau", "J", "T_end", "O_early", "O_late",
            "started_unordered", "final_ordered", "switched_U_to_O", "t_switch", "censored"]
    df = df[cols].copy()
    df.to_csv(out_dir / "runs_parsed.csv", index=False)

    agg_rows = []
    for (perm, tau, J, cc), g in df.groupby(["permult", "tau", "J", "cc"], dropna=False):
        frac_ord = float(np.mean(g["final_ordered"].astype(float)))
        n = int(len(g))
        switched = g[g["switched_U_to_O"] & g["t_switch"].notna()]
        med_t = float(np.median(switched["t_switch"])) if len(switched) else float("nan")
        frac_switched = float(np.mean(g["switched_U_to_O"].astype(float)))
        frac_censored = float(np.mean(g["censored"].astype(float)))
        agg_rows.append(dict(
            permult=perm, tau=tau, J=J, cc=cc,
            n_runs=n,
            frac_final_ordered=frac_ord,
            frac_switched=frac_switched,
            frac_censored=frac_censored,
            median_t_switch=med_t,
        ))
    agg = pd.DataFrame(agg_rows).sort_values(["permult", "tau", "cc"])
    agg.to_csv(out_dir / "stability_agg.csv", index=False)

    plt.rcParams.update({"font.size": FONTSIZE})

    # Line: fraction final ordered vs J
    fig = plt.figure(figsize=(8.5, 5.5))
    ax = fig.add_subplot(111)
    for (perm, cc), g in agg.groupby(["permult", "cc"], dropna=False):
        g = g.dropna(subset=["J", "frac_final_ordered"]).sort_values("J")
        if g.empty:
            continue
        label = f"permult={perm:g}" + (f", cc={int(cc)}" if pd.notna(cc) else "")
        ax.plot(g["J"], g["frac_final_ordered"], marker="o", linewidth=2.0, label=label)
    ax.set_xlabel("Alignment strength  J  (external convention: J = 1/τ)")
    ax.set_ylabel("Fraction final ordered")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.set_title("Stability: basin of attraction vs alignment strength", fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "line_frac_final_ordered_vs_J.png", dpi=DPI)
    plt.close(fig)

    # Line: median switch time vs J
    fig = plt.figure(figsize=(8.5, 5.5))
    ax = fig.add_subplot(111)
    for (perm, cc), g in agg.groupby(["permult", "cc"], dropna=False):
        g = g.dropna(subset=["J", "median_t_switch"]).sort_values("J")
        if g.empty:
            continue
        label = f"permult={perm:g}" + (f", cc={int(cc)}" if pd.notna(cc) else "")
        ax.plot(g["J"], g["median_t_switch"], marker="o", linewidth=2.0, label=label)
    ax.set_xlabel("Alignment strength  J  (external convention: J = 1/τ)")
    ax.set_ylabel("Median switching time (steps)  [switched only]")
    ax.grid(True, alpha=0.3)
    ax.set_title("Stability: switching time scale", fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "line_median_switch_time_vs_J.png", dpi=DPI)
    plt.close(fig)

    # Bars: switched vs censored per tau (stacked)
    fig = plt.figure(figsize=(9.0, 5.6))
    ax = fig.add_subplot(111)
    # Choose one permult/cc group if multiple exist
    g0 = agg.copy()
    if g0["permult"].nunique() > 1:
        perm0 = float(g0["permult"].dropna().iloc[0])
        g0 = g0[g0["permult"] == perm0]
        subtitle = f"(permult={perm0:g})"
    else:
        subtitle = ""
    if g0["cc"].notna().any() and g0["cc"].nunique(dropna=True) > 1:
        cc0 = float(g0["cc"].dropna().iloc[0])
        g0 = g0[g0["cc"] == cc0]
        subtitle = subtitle[:-1] + (f", cc={int(cc0)})" if subtitle.endswith(")") else f"(cc={int(cc0)})")
    g0 = g0.dropna(subset=["tau", "frac_switched", "frac_censored"]).sort_values("tau")
    x = np.arange(len(g0))
    ax.bar(x, g0["frac_switched"], label="switched (U→O)")
    ax.bar(x, g0["frac_censored"], bottom=g0["frac_switched"], label="censored (no switch)")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:.3g}" for v in g0["tau"]], rotation=45, ha="right")
    ax.set_xlabel("τ")
    ax.set_ylabel("Fraction of runs")
    ax.set_ylim(0, 1.02)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_title("Switching vs censoring within the observation window " + subtitle, fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "bars_switched_vs_censored.png", dpi=DPI)
    plt.close(fig)

    # Survival curves (KM)
    fig = plt.figure(figsize=(9.0, 5.8))
    ax = fig.add_subplot(111)
    for (perm, cc), gagg in agg.groupby(["permult", "cc"], dropna=False):
        levels = pick_survival_levels(gagg, "tau")
        if not levels:
            continue
        for tau_val in levels:
            sub = df[(df["permult"] == perm) & (df["tau"] == tau_val)]
            if pd.notna(cc):
                sub = sub[sub["cc"] == cc]
            sub = sub[sub["started_unordered"]]
            if sub.empty:
                continue
            t_event = sub["t_switch"].to_numpy(dtype=float)
            cens = sub["censored"].to_numpy(dtype=bool)
            t_fill = sub["T_end"].to_numpy(dtype=float)
            times = np.where(np.isfinite(t_event), t_event, t_fill)
            t_km, S_km = kaplan_meier(times, cens)
            label = f"permult={perm:g}, τ={tau_val:g}" + (f", cc={int(cc)}" if pd.notna(cc) else "")
            ax.step(t_km, S_km, where="post", linewidth=2.0, label=label)

    ax.set_xlabel("time (simulation steps)")
    ax.set_ylabel("Survival  S(t) = P(not yet switched)")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.set_title("Kaplan–Meier survival curves (right-censoring aware)", fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / "survival_curves.png", dpi=DPI)
    plt.close(fig)

    print("[OK] Wrote:")
    for fn in ["runs_parsed.csv", "stability_agg.csv",
               "line_frac_final_ordered_vs_J.png", "line_median_switch_time_vs_J.png",
               "survival_curves.png", "bars_switched_vs_censored.png"]:
        print(" ", out_dir / fn)


if __name__ == "__main__":
    main()
