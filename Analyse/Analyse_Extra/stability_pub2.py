#!/usr/bin/env python3
"""
stability_pub2.py
-----------------
Improved publication-style stability analysis from O(t) time series files.

Fixes vs stability_pub.py:
- Survival curves now show ALL tau values clearly:
  * Uses "at-risk fraction" at TRANSIENT_CUT (unordered at transient).
  * Kaplan–Meier is computed conditionally on at-risk runs, then multiplied by f0.
  * Handles degenerate all-censored / all-switched-before-window cases gracefully.
- Bar plot now has THREE categories (sums to 1):
  * already ordered at transient
  * switched after transient
  * never ordered within window (censored among at-risk)

Place this script in a folder that contains:
  - compute_order.csv  (optional)
  - a subfolder "time_series/" with per-run CSV files (recommended), OR the per-run CSVs directly.

Expected time-series CSV format (no header):
  col0 = time (simulation steps)
  col1 = O(t)

Expected filename pattern (example):
  cc_1024;rand_1;tau_0.17;v0_0.05;k_1.0;nu_0.1;gamma_0.1;permult_2.8;line_0.1.csv

Outputs under ./stability_pub_out/:
  - runs_parsed.csv
  - stability_agg.csv
  - line_frac_final_ordered_vs_J.png
  - line_median_switch_time_vs_J.png
  - survival_curves.png
  - bars_threeway.png
"""

from __future__ import annotations

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

# Order thresholds
O_HIGH = 0.80
HOLD_POINTS = 10  # consecutive points above O_HIGH

# Transient handling
TRANSIENT_CUT = 150_000  # define "start of observation window"
EARLY_WINDOW = 30_000    # used only for reporting; not used in survival

# External-aligner convention: J = 1/tau (used for x-axis)
USE_J_DIRECT = False  # if True, extend parser to read J from filename

# Survival: plot all tau values found for each (permult,cc)
SURVIVAL_PLOT_ALL_TAU = True
SURVIVAL_MAX_CURVES = 8  # if too many, downsample evenly

# Plot style
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
    O_at_transient: float
    ordered_at_transient: bool
    final_ordered: bool
    t_switch: Optional[float]          # first sustained crossing time (>= TRANSIENT_CUT)
    switched_after_transient: bool     # unordered at transient AND switches later
    censored_after_transient: bool     # unordered at transient AND never switches


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

    # Early mean (for reporting only)
    early_mask = (t >= T_min) & (t <= T_min + EARLY_WINDOW)
    if early_mask.sum() < 3:
        early_mask = (t <= T_min + max(EARLY_WINDOW, (T_end - T_min) * 0.1))
    O_early = float(np.mean(O[early_mask])) if early_mask.sum() else float("nan")

    # Late mean (fallback = last 20%)
    late_mask = (t >= TRANSIENT_CUT)
    if late_mask.sum() < 5:
        late_mask = (t >= (T_min + 0.8 * (T_end - T_min)))
    O_late = float(np.mean(O[late_mask])) if late_mask.sum() else float("nan")
    final_ordered = bool(np.isfinite(O_late) and (O_late >= O_HIGH))

    # Order at transient: mean of first HOLD_POINTS samples at/after TRANSIENT_CUT
    idx0 = np.where(t >= TRANSIENT_CUT)[0]
    if len(idx0) == 0:
        # no data after transient cut; use last value
        O_at = float(O[-1])
    else:
        i0 = int(idx0[0])
        i1 = min(len(O), i0 + HOLD_POINTS)
        O_at = float(np.mean(O[i0:i1]))
    ordered_at_transient = bool(np.isfinite(O_at) and (O_at >= O_HIGH))

    # Switching time searched in [TRANSIENT_CUT, ...]
    sw_mask = (t >= TRANSIENT_CUT)
    t_sw = None
    if sw_mask.sum() >= HOLD_POINTS:
        t_sw = first_sustained_crossing(t[sw_mask], O[sw_mask], O_HIGH, HOLD_POINTS)

    # Categories relative to transient
    if ordered_at_transient:
        switched_after = False
        censored_after = False
    else:
        switched_after = (t_sw is not None)
        censored_after = (t_sw is None)

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
        O_at_transient=O_at,
        ordered_at_transient=ordered_at_transient,
        final_ordered=final_ordered,
        t_switch=t_sw,
        switched_after_transient=switched_after,
        censored_after_transient=censored_after,
    )


def kaplan_meier(times: np.ndarray, censored: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    KM survival on the at-risk subset (times are event or censor times).
    Returns step points (t, S_conditional).
    """
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
        # No events: return a flat conditional survival of 1 across the window
        return np.array([float(np.min(times)), float(np.max(times))]), np.array([1.0, 1.0])

    return np.array(t_out), np.array(S_out)


def downsample(vals: List[float], k: int) -> List[float]:
    if len(vals) <= k:
        return vals
    idx = np.linspace(0, len(vals) - 1, k).round().astype(int)
    return [vals[i] for i in idx]


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

    # Aggregate
    agg = df.groupby(["permult", "tau", "J", "cc"], dropna=False).agg(
        n_runs=("tau", "size"),
        frac_final_ordered=("final_ordered", "mean"),
        frac_ordered_at_transient=("ordered_at_transient", "mean"),
        frac_switched_after=("switched_after_transient", "mean"),
        frac_censored_after=("censored_after_transient", "mean"),
        median_t_switch=("t_switch", lambda s: float(np.nanmedian(s.to_numpy(dtype=float))) if np.isfinite(s.to_numpy(dtype=float)).any() else np.nan),
        T_end=("T_end", "max"),
    ).reset_index().sort_values(["permult", "tau", "cc"])
    agg.to_csv(out_dir / "stability_agg.csv", index=False)

    plt.rcParams.update({"font.size": FONTSIZE})

    # Line: final ordered vs J
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

    # Line: median switch time vs J (exclude NaNs)
    fig = plt.figure(figsize=(8.5, 5.5))
    ax = fig.add_subplot(111)
    for (perm, cc), g in agg.groupby(["permult", "cc"], dropna=False):
        g = g.dropna(subset=["J", "median_t_switch"]).sort_values("J")
        if g.empty:
            continue
        label = f"permult={perm:g}" + (f", cc={int(cc)}" if pd.notna(cc) else "")
        ax.plot(g["J"], g["median_t_switch"], marker="o", linewidth=2.0, label=label)
    ax.set_xlabel("Alignment strength  J  (external convention: J = 1/τ)")
    ax.set_ylabel("Median switching time (steps)  [including early ordering]")
    ax.grid(True, alpha=0.3)
    ax.set_title("Stability: switching time scale", fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "line_median_switch_time_vs_J.png", dpi=DPI)
    plt.close(fig)

    # Bars: three-way fractions (sums to 1)
    fig = plt.figure(figsize=(9.0, 5.8))
    ax = fig.add_subplot(111)

    # Choose one permult/cc if multiple exist (keep plot clean)
    g0 = agg.copy()
    subtitle = ""
    if g0["permult"].nunique() > 1:
        perm0 = float(g0["permult"].dropna().iloc[0])
        g0 = g0[g0["permult"] == perm0]
        subtitle = f"(permult={perm0:g})"
    if g0["cc"].notna().any() and g0["cc"].nunique(dropna=True) > 1:
        cc0 = float(g0["cc"].dropna().iloc[0])
        g0 = g0[g0["cc"] == cc0]
        subtitle = subtitle[:-1] + (f", cc={int(cc0)})" if subtitle.endswith(")") else f"(cc={int(cc0)})")

    g0 = g0.dropna(subset=["tau"]).sort_values("tau")
    x = np.arange(len(g0))

    a = g0["frac_ordered_at_transient"].to_numpy(float)
    b = g0["frac_switched_after"].to_numpy(float)
    c = g0["frac_censored_after"].to_numpy(float)

    ax.bar(x, a, label="already ordered at transient")
    ax.bar(x, b, bottom=a, label="switched after transient")
    ax.bar(x, c, bottom=a+b, label="never ordered (censored)")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{v:.3g}" for v in g0["tau"]], rotation=45, ha="right")
    ax.set_xlabel("τ")
    ax.set_ylabel("Fraction of runs")
    ax.set_ylim(0, 1.02)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_title("Outcomes relative to the observation window " + subtitle, fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "bars_threeway.png", dpi=DPI)
    plt.close(fig)

    # Survival curves: unconditional S(t) = P(still unordered at time t)
    fig = plt.figure(figsize=(9.2, 5.8))
    ax = fig.add_subplot(111)

    for (perm, cc), gagg in agg.groupby(["permult", "cc"], dropna=False):
        tau_vals = sorted([float(v) for v in gagg["tau"].dropna().unique()])
        if not tau_vals:
            continue
        if not SURVIVAL_PLOT_ALL_TAU:
            # pick near-transition subset
            tau_vals = downsample(tau_vals, SURVIVAL_MAX_CURVES)
        else:
            tau_vals = downsample(tau_vals, SURVIVAL_MAX_CURVES)

        # Determine a common T_end for axis limits in this group
        T_end_group = float(np.nanmax(gagg["T_end"].to_numpy(dtype=float)))

        for tau_val in tau_vals:
            sub = df[(df["permult"] == perm) & (df["tau"] == tau_val)]
            if pd.notna(cc):
                sub = sub[sub["cc"] == cc]
            if sub.empty:
                continue

            # At-risk subset: unordered at transient
            at_risk = sub[~sub["ordered_at_transient"]].copy()
            f0 = float(len(at_risk) / len(sub))

            if len(at_risk) == 0:
                # Everyone already ordered by transient -> survival is 0 in the window
                ax.plot([TRANSIENT_CUT, T_end_group], [0.0, 0.0],
                        linewidth=2.0, label=f"τ={tau_val:g} (f0=0)")
                continue

            # Event times are t_switch; censored if t_switch is NaN
            t_event = at_risk["t_switch"].to_numpy(dtype=float)
            cens = ~np.isfinite(t_event)
            times = np.where(np.isfinite(t_event), t_event, at_risk["T_end"].to_numpy(dtype=float))

            # KM conditional on at-risk, then scale by f0
            t_km, S_cond = kaplan_meier(times, cens)
            # Handle degenerate min=max (all censored with same T_end)
            if len(t_km) == 2 and t_km[0] == t_km[1]:
                t_km = np.array([TRANSIENT_CUT, T_end_group], dtype=float)
                S_cond = np.array([1.0, 1.0], dtype=float)

            S_uncond = f0 * S_cond

            ax.step(t_km, S_uncond, where="post", linewidth=2.0,
                    label=f"τ={tau_val:g} (f0={f0:.2f})")

    ax.set_xlabel("time (simulation steps)")
    ax.set_ylabel("Survival  S(t) = P(still unordered at time t)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlim(max(0.0, TRANSIENT_CUT - 0.05*(T_end_group - TRANSIENT_CUT)), T_end_group)
    ax.grid(True, alpha=0.3)
    ax.set_title("Survival curves (censoring aware, anchored at transient)", fontsize=TITLE_FONTSIZE)
    ax.legend(frameon=False, fontsize=10, ncol=2)
    fig.tight_layout()
    fig.savefig(out_dir / "survival_curves.png", dpi=DPI)
    plt.close(fig)

    print("[OK] Wrote:")
    for fn in ["runs_parsed.csv", "stability_agg.csv",
               "line_frac_final_ordered_vs_J.png",
               "line_median_switch_time_vs_J.png",
               "bars_threeway.png",
               "survival_curves.png"]:
        print(" ", out_dir / fn)


if __name__ == "__main__":
    main()
