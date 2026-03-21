#!/usr/bin/env python3
"""
stabmap.py  (stability map for first-order / metastable switching)

EXPECTED FOLDER STRUCTURE
-------------------------
Place this script in a folder that contains:
  ./time_series/
and inside time_series you have many CSV files like:
  cc_1024;rand_1;tau_0.17;v0_0.05;k_1.0;nu_0.1;gamma_0.1;permult_2.8;line_0.1.csv

Each time-series CSV is assumed to be:
  time, O(t)
with NO header (comma-separated), one row per sample.

WHAT IT DOES
------------
For each run, it extracts switching / stability metrics from O(t):
  - start_state (ordered / unordered / intermediate)
  - final_state (using a late-time window)
  - first passage time to ordered (U->O), using a high-threshold + hold time
Then it aggregates by (permult, tau) (and optionally by cc) and produces:
  - heatmap: fraction final-ordered
  - heatmap: median switching time (among switched runs)
  - line plots: fraction ordered vs tau for each permult
  - summary CSVs

OUTPUT
------
Creates ./stability_out/ next to this script.

USAGE
-----
  python stabmap.py
"""

import os
import re
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# CONFIG (edit if needed)
# =========================
TIME_SERIES_DIR = "time_series"
OUTDIR = "stability_out"

# O(t) thresholds for state classification
O_HIGH = 0.80   # ordered if O >= O_HIGH
O_LOW  = 0.20   # unordered if O <= O_LOW

# Transient cut (in the same units as the "time" column). If None, no cut.
TRANSIENT_CUT_TIME = 60000  # e.g. 150000, or None

# Hold-time for declaring that the ordered state is *stably* reached.
# Use either HOLD_DURATION_TIME (preferred) or HOLD_POINTS.
HOLD_DURATION_TIME = None  # e.g. 5000 (time units). If None, use HOLD_POINTS.
HOLD_POINTS = 30           # consecutive samples above O_HIGH (fallback)

# Late-time window for final_state / O_late
LATE_FRACTION = 0.20       # last 20% of post-transient samples

# Optional: only analyze some system sizes / parameters
FILTER_CC: Optional[List[int]] = None          # e.g. [1024, 2048], or None for all
FILTER_PERMULT: Optional[List[float]] = None   # e.g. [2.8, 3.0], or None
FILTER_TAU: Optional[List[float]] = None       # exact taus to keep, or None
TAU_TOL = 1e-12                               # matching tolerance for FILTER_TAU

# How to aggregate
AGG_BY_CC = False  # if True, aggregate by (permult, tau, cc). Else just (permult, tau).

# Plot controls
FIG_DPI = 220
MAX_TAU_TICKS = 12  # avoid unreadable x-axis

# p0 conversion (optional convenience)
P0_FROM_PERMULT = True  # if True, also report p0 = 1.1547 * permult in summary
# =========================


def parse_params_from_filename(fname: str) -> Dict[str, Any]:
    """
    Parse params from filenames like:
      cc_1024;rand_1;tau_0.17;...;permult_2.8;line_0.1.csv
    """
    base = Path(fname).name
    base = base[:-4] if base.endswith(".csv") else base
    parts = base.split(";")
    params: Dict[str, Any] = {}
    for p in parts:
        if "_" not in p:
            continue
        k, v = p.split("_", 1)
        params[k] = v

    # Cast common fields
    def to_int(x):
        try:
            return int(x)
        except Exception:
            return None

    def to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    for key in ["cc", "rand", "seed"]:
        if key in params:
            vi = to_int(params[key])
            if vi is not None:
                params[key] = vi

    for key in ["tau", "v0", "k", "nu", "gamma", "permult", "p0", "line"]:
        if key in params:
            vf = to_float(params[key])
            if vf is not None:
                params[key] = vf

    return params


def read_timeseries_csv(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read time, O(t) from a 2-column CSV with no header.
    """
    df = pd.read_csv(path, header=None, names=["t", "O"])
    t = pd.to_numeric(df["t"], errors="coerce").to_numpy()
    O = pd.to_numeric(df["O"], errors="coerce").to_numpy()
    mask = np.isfinite(t) & np.isfinite(O)
    t = t[mask]
    O = O[mask]
    if len(t) < 5:
        raise ValueError(f"Too few samples in {path}")
    return t, O


def apply_transient_cut(t: np.ndarray, O: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if TRANSIENT_CUT_TIME is None:
        return t, O
    mask = t >= TRANSIENT_CUT_TIME
    if mask.sum() < 5:
        # If cut removes almost everything, keep full series but warn via downstream summary
        return t, O
    return t[mask], O[mask]


def compute_hold_points(t: np.ndarray) -> int:
    if HOLD_DURATION_TIME is not None:
        dt = np.median(np.diff(t))
        if not np.isfinite(dt) or dt <= 0:
            return max(1, HOLD_POINTS)
        return max(1, int(math.ceil(HOLD_DURATION_TIME / dt)))
    return max(1, HOLD_POINTS)


def classify_value(o: float) -> str:
    if o >= O_HIGH:
        return "ordered"
    if o <= O_LOW:
        return "unordered"
    return "intermediate"


def classify_start_state(O: np.ndarray, n_smooth: int = 5) -> str:
    n = min(n_smooth, len(O))
    o0 = float(np.mean(O[:n]))
    return classify_value(o0)


def final_state_from_late_window(O: np.ndarray) -> Tuple[str, float]:
    n = len(O)
    start = int(math.floor((1.0 - LATE_FRACTION) * n))
    start = max(0, min(n - 1, start))
    o_late = float(np.mean(O[start:]))
    return classify_value(o_late), o_late


def first_passage_to_ordered(t: np.ndarray, O: np.ndarray, hold_pts: int) -> Tuple[Optional[float], bool]:
    """
    Return (t_switch, switched):
      t_switch is absolute time (same units as t) at which ordered is reached stably.
      switched is True if ordered reached; False otherwise.
    """
    above = (O >= O_HIGH).astype(np.int32)
    if len(above) < hold_pts:
        return None, False
    # Moving window sum: if equals hold_pts, we have hold_pts consecutive above-threshold samples
    window = np.ones(hold_pts, dtype=np.int32)
    conv = np.convolve(above, window, mode="valid")
    idx = np.where(conv == hold_pts)[0]
    if len(idx) == 0:
        return None, False
    i0 = int(idx[0])
    return float(t[i0]), True


def should_keep(params: Dict[str, Any]) -> bool:
    if FILTER_CC is not None:
        cc = params.get("cc", None)
        if cc not in FILTER_CC:
            return False
    if FILTER_PERMULT is not None:
        pm = params.get("permult", None)
        if pm is None:
            return False
        if not any(abs(pm - x) <= 1e-12 for x in FILTER_PERMULT):
            return False
    if FILTER_TAU is not None:
        tau = params.get("tau", None)
        if tau is None:
            return False
        if not any(abs(tau - x) <= TAU_TOL for x in FILTER_TAU):
            return False
    return True


def pivot_heatmap(df: pd.DataFrame, value_col: str, index_col: str, columns_col: str) -> pd.DataFrame:
    piv = df.pivot_table(index=index_col, columns=columns_col, values=value_col, aggfunc="mean")
    # Sort numeric axes
    piv = piv.sort_index(axis=0)
    piv = piv.reindex(sorted(piv.columns), axis=1)
    return piv


def plot_heatmap(piv: pd.DataFrame, title: str, xlabel: str, ylabel: str, outpath: Path,
                 vmin: Optional[float] = None, vmax: Optional[float] = None, cmap: str = "viridis"):
    fig = plt.figure(figsize=(9, 5.5))
    ax = fig.add_subplot(111)

    data = piv.to_numpy()
    im = ax.imshow(data, aspect="auto", origin="lower", vmin=vmin, vmax=vmax, cmap=cmap)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # ticks
    xvals = list(piv.columns)
    yvals = list(piv.index)

    # limit number of x ticks
    if len(xvals) > MAX_TAU_TICKS:
        step = max(1, len(xvals) // MAX_TAU_TICKS)
        xticks = list(range(0, len(xvals), step))
    else:
        xticks = list(range(len(xvals)))
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{xvals[i]:g}" for i in xticks], rotation=45, ha="right")

    ax.set_yticks(range(len(yvals)))
    ax.set_yticklabels([f"{y:g}" for y in yvals])

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel(value_col_pretty(value_col), rotation=90)

    fig.tight_layout()
    fig.savefig(outpath, dpi=FIG_DPI)
    plt.close(fig)


def value_col_pretty(col: str) -> str:
    return {
        "frac_final_ordered": "fraction final ordered",
        "frac_switched": "fraction switched (U→O)",
        "median_t_switch": "median switch time (among switched)",
        "mean_t_switch": "mean switch time (among switched)",
        "O_late_mean": "late-time mean order",
    }.get(col, col)


def main():
    root = Path(".").resolve()
    ts_dir = root / TIME_SERIES_DIR
    if not ts_dir.is_dir():
        raise SystemExit(f"Cannot find time_series directory at: {ts_dir}")

    outdir = root / OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(ts_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files found in {ts_dir}")

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []

    for fp in files:
        params = parse_params_from_filename(fp.name)
        if not should_keep(params):
            continue
        try:
            t, O = read_timeseries_csv(fp)
            t, O = apply_transient_cut(t, O)
            hold_pts = compute_hold_points(t)

            start_state = classify_start_state(O)
            final_state, o_late = final_state_from_late_window(O)

            t_switch_abs, reached = first_passage_to_ordered(t, O, hold_pts)

            # Define switching from unordered-ish start into ordered
            # If you start already ordered, count as not "switched" (but reached=True).
            switched = (start_state != "ordered") and reached

            # If switched, report switch time relative to start of post-transient window
            t0 = float(t[0])
            tmax = float(t[-1])
            t_switch_rel = None
            if t_switch_abs is not None:
                t_switch_rel = float(t_switch_abs - t0)

            row = dict(
                file=str(fp.name),
                cc=params.get("cc", None),
                rand=params.get("rand", params.get("seed", None)),
                tau=params.get("tau", None),
                permult=params.get("permult", None),
                p0=(1.1547 * params["permult"] if (P0_FROM_PERMULT and isinstance(params.get("permult", None), float)) else params.get("p0", None)),
                start_state=start_state,
                final_state=final_state,
                O_late=o_late,
                hold_points=hold_pts,
                reached_ordered=bool(reached),
                switched_U_to_O=bool(switched),
                t_switch_rel=(t_switch_rel if switched else np.nan),
                t_window=(tmax - t0),
                n_samples=len(t),
            )

            # Keep any other params too (v0, nu, line...) for debugging
            for k, v in params.items():
                if k not in row:
                    row[k] = v

            rows.append(row)

        except Exception as e:
            errors.append(f"{fp.name}: {e}")

    if not rows:
        raise SystemExit("No runs parsed (filters too strict or files unreadable).")

    runs = pd.DataFrame(rows)
    runs_path = outdir / "runs_parsed.csv"
    runs.to_csv(runs_path, index=False)

    # Aggregation
    group_cols = ["permult", "tau"] + (["cc"] if AGG_BY_CC else [])
    agg = (runs.groupby(group_cols)
           .agg(
               n_runs=("file", "size"),
               frac_final_ordered=("final_state", lambda s: float(np.mean(s == "ordered"))),
               frac_switched=("switched_U_to_O", "mean"),
               O_late_mean=("O_late", "mean"),
               median_t_switch=("t_switch_rel", lambda s: float(np.nanmedian(s)) if np.any(np.isfinite(s)) else np.nan),
               mean_t_switch=("t_switch_rel", lambda s: float(np.nanmean(s)) if np.any(np.isfinite(s)) else np.nan),
           )
           .reset_index())

    if P0_FROM_PERMULT and "permult" in agg.columns:
        agg["p0"] = 1.1547 * agg["permult"]

    agg_path = outdir / "stability_agg.csv"
    agg.to_csv(agg_path, index=False)

    # Heatmaps
    idx_name = "permult"  # y axis
    col_name = "tau"      # x axis

    # If AGG_BY_CC, make separate heatmaps per cc
    if AGG_BY_CC and "cc" in agg.columns:
        for cc, sub in agg.groupby("cc"):
            piv = pivot_heatmap(sub, "frac_final_ordered", idx_name, col_name)
            plot_heatmap(
                piv,
                title=f"Stability map: fraction final ordered (cc={cc})",
                xlabel="tau",
                ylabel=idx_name,
                outpath=outdir / f"heat_frac_final_ordered_cc{cc}.png",
                vmin=0.0, vmax=1.0, cmap="viridis"
            )

            piv2 = pivot_heatmap(sub, "median_t_switch", idx_name, col_name)
            plot_heatmap(
                piv2,
                title=f"Stability map: median switching time (cc={cc})",
                xlabel="tau",
                ylabel=idx_name,
                outpath=outdir / f"heat_median_t_switch_cc{cc}.png",
                vmin=None, vmax=None, cmap="magma"
            )
    else:
        piv = pivot_heatmap(agg, "frac_final_ordered", idx_name, col_name)
        plot_heatmap(
            piv,
            title="Stability map: fraction final ordered",
            xlabel="tau",
            ylabel=idx_name,
            outpath=outdir / "heat_frac_final_ordered.png",
            vmin=0.0, vmax=1.0, cmap="viridis"
        )

        piv2 = pivot_heatmap(agg, "median_t_switch", idx_name, col_name)
        plot_heatmap(
            piv2,
            title="Stability map: median switching time (among switched)",
            xlabel="tau",
            ylabel=idx_name,
            outpath=outdir / "heat_median_t_switch.png",
            vmin=None, vmax=None, cmap="magma"
        )

    # Line plots: fraction ordered vs tau per permult (and optionally per cc)
    def plot_lines(df: pd.DataFrame, ycol: str, title: str, outname: str):
        fig = plt.figure(figsize=(8.5, 5.0))
        ax = fig.add_subplot(111)

        if AGG_BY_CC and "cc" in df.columns:
            for (pm, cc), sub in df.groupby(["permult", "cc"]):
                sub = sub.sort_values("tau")
                ax.plot(sub["tau"].to_numpy(), sub[ycol].to_numpy(), marker="o", linewidth=1.5,
                        label=f"permult={pm:g}, cc={cc}")
        else:
            for pm, sub in df.groupby("permult"):
                sub = sub.sort_values("tau")
                ax.plot(sub["tau"].to_numpy(), sub[ycol].to_numpy(), marker="o", linewidth=1.5,
                        label=f"permult={pm:g}")

        ax.set_xlabel("tau")
        ax.set_ylabel(value_col_pretty(ycol))
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(frameon=False, fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(outdir / outname, dpi=FIG_DPI)
        plt.close(fig)

    plot_lines(agg, "frac_final_ordered", "Fraction final ordered vs tau", "lines_frac_final_ordered.png")
    plot_lines(agg, "median_t_switch", "Median switching time vs tau (switched only)", "lines_median_t_switch.png")

    # Write errors
    if errors:
        (outdir / "errors.txt").write_text("\n".join(errors), encoding="utf-8")

    print("[OK] Wrote:")
    print(f"  {runs_path}")
    print(f"  {agg_path}")
    print(f"  {outdir / 'heat_frac_final_ordered.png'} (or cc-specific variants)")
    print(f"  {outdir / 'heat_median_t_switch.png'} (or cc-specific variants)")
    print(f"  {outdir / 'lines_frac_final_ordered.png'}")
    print(f"  {outdir / 'lines_median_t_switch.png'}")
    if errors:
        print(f"  {outdir / 'errors.txt'}  (some files failed to parse)")


if __name__ == "__main__":
    main()
