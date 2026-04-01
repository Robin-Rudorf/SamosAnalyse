#!/usr/bin/env python3
"""
stability_pub3.py
-----------------
Publication-style stability analysis from O(t) time-series CSVs.

Key features:
- Uses J = 1/tau everywhere (x-axis ordering, labels, colors).
- Survival curves use a colormap + colorbar (no legend in the plot).
- Legends (when needed) are moved outside the axes.
- Cleaner, minimal scientific labels: "S(t)", "fraction", "t (steps)", "J".
- Outcome bars use 3 classes that sum to 1:
    (1) already ordered at transient
    (2) switched after transient
    (3) never ordered within window (right-censored)

Folder layout:
- Put this script next to a folder "time_series/" containing run CSVs.
  (Or set TIME_SERIES_DIRNAME="" to search the current folder.)

Time-series CSV format (no header):
  col0 = time (simulation steps)
  col1 = O(t)

Outputs written under ./stability_pub_out/ (one set per (permult, cc) group):
  - runs_parsed.csv
  - stability_agg.csv
  - frac_final_ordered_vs_J__permultX__ccY.png
  - median_tswitch_vs_J__permultX__ccY.png
  - outcomes_bars__permultX__ccY.png
  - survival__permultX__ccY.png
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
TIME_SERIES_DIRNAME = "time_series"   # set to "" to search current folder only
GLOB_PATTERN = "*.csv"

# Order threshold + hysteresis guard
O_HIGH = 0.80
HOLD_POINTS = 10  # consecutive samples above O_HIGH

# Transient cut defines the observation window start (same units as col0 in CSV)
TRANSIENT_CUT = 150_000

# Plot aesthetics
DPI = 260
FONTSIZE = 12
TITLE_FONTSIZE = 13
LINEWIDTH = 2.2

# If there are many tau values, downsample for survival curves
MAX_SURVIVAL_CURVES = 8

# Colormap for J-coded curves
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
    O_at_transient: float
    ordered_at_transient: bool
    final_ordered: bool
    t_switch: Optional[float]              # first sustained crossing time >= TRANSIENT_CUT
    switched_after_transient: bool
    censored_after_transient: bool


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
    tau = params["tau"]
    J = (1.0 / tau) if (tau is not None and tau > 0) else None

    # O at transient: mean of first HOLD_POINTS samples at/after TRANSIENT_CUT
    idx0 = np.where(t >= TRANSIENT_CUT)[0]
    if len(idx0) == 0:
        O_at = float(O[-1])
    else:
        i0 = int(idx0[0])
        i1 = min(len(O), i0 + HOLD_POINTS)
        O_at = float(np.mean(O[i0:i1]))
    ordered_at_transient = bool(np.isfinite(O_at) and O_at >= O_HIGH)

    # final ordered: mean over last 20% of the trajectory
    t_min = float(np.min(t))
    late_mask = (t >= (t_min + 0.8 * (T_end - t_min)))
    O_late = float(np.mean(O[late_mask])) if late_mask.sum() else float("nan")
    final_ordered = bool(np.isfinite(O_late) and O_late >= O_HIGH)

    # switching time in the observation window
    sw_mask = (t >= TRANSIENT_CUT)
    t_sw = None
    if sw_mask.sum() >= HOLD_POINTS:
        t_sw = first_sustained_crossing(t[sw_mask], O[sw_mask], O_HIGH, HOLD_POINTS)

    if ordered_at_transient:
        switched_after = False
        censored_after = False
    else:
        switched_after = (t_sw is not None)
        censored_after = (t_sw is None)

    return RunRecord(
        path=path,
        cc=int(params["cc"]) if params["cc"] is not None else None,
        rand=int(params["rand"]) if params["rand"] is not None else None,
        tau=float(tau) if tau is not None else None,
        permult=float(params["permult"]) if params["permult"] is not None else None,
        J=float(J) if J is not None else None,
        T_end=T_end,
        O_at_transient=O_at,
        ordered_at_transient=ordered_at_transient,
        final_ordered=final_ordered,
        t_switch=t_sw,
        switched_after_transient=switched_after,
        censored_after_transient=censored_after,
    )


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
            t0, t1 = TRANSIENT_CUT, float(np.max(times))
        return np.array([t0, t1], dtype=float), np.array([1.0, 1.0], dtype=float)

    return np.array(t_out, dtype=float), np.array(S_out, dtype=float)


def downsample(vals: List[float], k: int) -> List[float]:
    if len(vals) <= k:
        return vals
    idx = np.linspace(0, len(vals) - 1, k).round().astype(int)
    return [vals[i] for i in idx]


def save_line_frac_final(agg_g: pd.DataFrame, outpath: Path, subtitle: str):
    g = agg_g.dropna(subset=["J", "frac_final_ordered"]).sort_values("J")
    fig = plt.figure(figsize=(7.6, 5.0))
    ax = fig.add_subplot(111)
    ax.plot(g["J"], g["frac_final_ordered"], marker="o", linewidth=LINEWIDTH)
    ax.set_xlabel("J")
    ax.set_ylabel("final ordered fraction")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
    fig.tight_layout()
    fig.savefig(outpath, dpi=DPI)
    plt.close(fig)


def save_line_median_tswitch(agg_g: pd.DataFrame, outpath: Path, subtitle: str):
    g = agg_g.dropna(subset=["J", "median_t_switch_switched"]).sort_values("J")
    fig = plt.figure(figsize=(7.6, 5.0))
    ax = fig.add_subplot(111)
    ax.plot(g["J"], g["median_t_switch_switched"], marker="o", linewidth=LINEWIDTH)
    ax.set_xlabel("J")
    ax.set_ylabel("median $t_{switch}$ (steps)")
    ax.grid(True, alpha=0.3)
    ax.set_title(subtitle, fontsize=TITLE_FONTSIZE)
    fig.tight_layout()
    fig.savefig(outpath, dpi=DPI)
    plt.close(fig)


def save_bars_threeway(agg_g: pd.DataFrame, outpath: Path, subtitle: str):
    g = agg_g.dropna(subset=["J"]).sort_values("J")
    x = np.arange(len(g))
    a = g["frac_ordered_at_transient"].to_numpy(float)
    b = g["frac_switched_after"].to_numpy(float)
    c = g["frac_censored_after"].to_numpy(float)

    fig = plt.figure(figsize=(8.2, 5.2))
    ax = fig.add_subplot(111)

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
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def save_survival(df_g: pd.DataFrame, agg_g: pd.DataFrame, outpath: Path, subtitle: str):
    g = agg_g.dropna(subset=["tau", "J"]).sort_values("J")
    levels_tau = g["tau"].to_list()
    levels_J = g["J"].to_list()
    if len(levels_tau) > MAX_SURVIVAL_CURVES:
        keep_idx = np.linspace(0, len(levels_tau)-1, MAX_SURVIVAL_CURVES).round().astype(int)
        levels_tau = [levels_tau[i] for i in keep_idx]
        levels_J = [levels_J[i] for i in keep_idx]

    cmap = mpl.cm.get_cmap(CMAP_NAME)
    J_min, J_max = float(np.min(levels_J)), float(np.max(levels_J))
    norm = mpl.colors.Normalize(vmin=J_min, vmax=J_max)

    fig = plt.figure(figsize=(8.2, 5.2))
    ax = fig.add_subplot(111)

    T_end_group = float(np.nanmax(df_g["T_end"].to_numpy(dtype=float)))
    ax.set_xlim(TRANSIENT_CUT, T_end_group)

    for tau_val, J_val in zip(levels_tau, levels_J):
        sub = df_g[df_g["tau"] == tau_val].copy()
        if sub.empty:
            continue

        at_risk = sub[~sub["ordered_at_transient"]].copy()
        f0 = float(len(at_risk) / len(sub))
        if f0 == 0.0:
            continue  # curve would be identically 0; bars already show this

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
    fig.savefig(outpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


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

    def nanmedian_switched(s: pd.Series) -> float:
        arr = s.to_numpy(dtype=float)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return np.nan
        return float(np.median(arr))

    # median switching time among switched-after-transient only
    df_sw = df[df["switched_after_transient"] & df["t_switch"].notna()].copy()
    med_sw = df_sw.groupby(["permult", "cc", "tau", "J"], dropna=False)["t_switch"].apply(nanmedian_switched).rename("median_t_switch_switched")

    agg = df.groupby(["permult", "cc", "tau", "J"], dropna=False).agg(
        n_runs=("tau", "size"),
        frac_final_ordered=("final_ordered", "mean"),
        frac_ordered_at_transient=("ordered_at_transient", "mean"),
        frac_switched_after=("switched_after_transient", "mean"),
        frac_censored_after=("censored_after_transient", "mean"),
    ).reset_index()

    agg = agg.merge(med_sw.reset_index(), on=["permult", "cc", "tau", "J"], how="left")
    agg = agg.sort_values(["permult", "cc", "J"])
    agg.to_csv(out_dir / "stability_agg.csv", index=False)

    for (perm, cc), agg_g in agg.groupby(["permult", "cc"], dropna=False):
        df_g = df[(df["permult"] == perm) & (df["cc"] == cc)].copy()

        tag = f"permult{perm:g}__cc{int(cc)}" if pd.notna(cc) else f"permult{perm:g}"
        subtitle = f"permult={perm:g}, cc={int(cc)}" if pd.notna(cc) else f"permult={perm:g}"

        save_line_frac_final(agg_g, out_dir / f"frac_final_ordered_vs_J__{tag}.png", subtitle)
        save_line_median_tswitch(agg_g, out_dir / f"median_tswitch_vs_J__{tag}.png", subtitle)
        save_bars_threeway(agg_g, out_dir / f"outcomes_bars__{tag}.png", subtitle)
        save_survival(df_g, agg_g, out_dir / f"survival__{tag}.png", subtitle)

    print("[OK] Wrote outputs under:", out_dir)


if __name__ == "__main__":
    main()
