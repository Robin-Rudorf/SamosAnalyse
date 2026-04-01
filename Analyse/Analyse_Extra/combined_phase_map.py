#!/usr/bin/env python3
"""
combined_phase_map.py
---------------------
Build a combined flocking + rigidity phase map from compute_order.csv.

Place this script in the SAME folder as:
  - compute_order.csv
  - compute_order.csv.cols.txt

The script:
1) reads and parses the CSV,
2) converts tau -> J if needed,
3) averages over seeds for each parameter point,
4) classifies each point into one of four phases:
      solid                : unordered + rigid
      solid flock          : ordered   + rigid
      liquid flock         : ordered   + fluid/relaxing
      liquid               : unordered + fluid/relaxing
5) plots a publication-style combined phase map with:
      - pastel phase background
      - black markers at sampled parameter points
      - flocking boundary contour
      - rigidity boundary contour
      - optional region labels
      - missing / failed parameter points shown in light gray
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap, BoundaryNorm

# =========================
# USER SETTINGS (edit here)
# =========================
MODE = "tau"               # "tau" or "J"
RIGIDITY_MODE = "alpha"    # "alpha" or "selfint"

# Flocking threshold
O_THRESHOLD = 0.60

# Rigidity threshold
ALPHA_SOLID_THRESHOLD = 100.0
SELFINT_SOLID_THRESHOLD = 0.30

# X axis: usually 'permult', interpreted as p0
X_COL = "permult"
X_LABEL = r"$p_0$"

# Auto-pick most frequent cc if None
CC_VALUE = None

# Additional exact-match filters; None => auto-pick most frequent
FILTERS = {
    "v": None,
    "nu": None,
    "gamma": None,
    "line": None,
    "k": None,
}

# Plot appearance
WRITE_REGION_LABELS = True
WRITE_POINT_MARKERS = True
SHOW_BOUNDARY_LINES = True
OUTPUT_DPI = 320
FIGSIZE = (8.0, 5.6)

FLOCK_LINE_COLOR = "#d62728"  # red
RIGID_LINE_COLOR = "#1f77b4"  # blue

# Phase colors: solid, solid flock, liquid flock, liquid
PHASE_COLORS = [
    "#d9d9d9",  # solid / glassy disordered
    "#cfe8ff",  # solid flock
    "#f7d4dc",  # liquid flock
    "#dff0d0",  # liquid
]
# =========================

ORDER_COL_CANDIDATES = ["O_mean", "Omean", "order_mean", "mean_order", "O"]

ALPHA_COL_CANDIDATES = [
    "alpha_relaxation_time",
    "alpha_relaxation",
    "alpha_relax",
    "alpha_relax_time",
    "tau_alpha",
    "alpha_tau",
    "alpha",
]

SELFINT_COL_CANDIDATES = [
    "minSelfInt",
    "min_selfint",
    "selfint_min",
    "Fs_min",
    "minFs",
]


def read_cols_file(cols_path: Path) -> List[str]:
    txt = cols_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"Cols:\s*([\s\S]+)", txt)
    if not m:
        raise ValueError(f"Could not find 'Cols:' in {cols_path}")
    tail = m.group(1).strip()
    for line in tail.splitlines():
        line = line.strip()
        if not line:
            continue
        if "," in line:
            return [c.strip() for c in line.split(",") if c.strip()]
    raise ValueError(f"Could not parse column names from {cols_path}")


def csv_has_header(csv_path: Path, cols: List[str]) -> bool:
    first = csv_path.open("r", encoding="utf-8", errors="ignore").readline().strip()
    toks = [t.strip() for t in first.split(",")]
    hits = sum(1 for t in toks if t in set(cols))
    return hits >= 2


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def pick_existing_column(df: pd.DataFrame, candidates: List[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    norm_map = {norm_name(col): col for col in df.columns}
    for c in candidates:
        nc = norm_name(c)
        if nc in norm_map:
            return norm_map[nc]
    raise ValueError(
        "Could not find column. Tried: "
        + ", ".join(candidates)
        + ". Available columns: "
        + ", ".join(map(str, list(df.columns)[:50]))
    )


def auto_pick_mode_value(df: pd.DataFrame, key: str):
    if key not in df.columns:
        return None
    s = df[key].dropna()
    if s.empty:
        return None
    return s.value_counts().idxmax()


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any], cc_value) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    chosen = {}
    out = df.copy()

    if "cc" in out.columns:
        cc_use = auto_pick_mode_value(out, "cc") if cc_value is None else cc_value
        chosen["cc"] = cc_use
        if cc_use is not None:
            out = out[out["cc"] == cc_use]

    for k, v in filters.items():
        if k not in out.columns:
            continue
        if v is None:
            v = auto_pick_mode_value(out, k)
        chosen[k] = v
        if v is not None:
            out = out[out[k] == v]
    return out, chosen


def compute_J(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "tau" not in out.columns:
        raise ValueError("Expected column 'tau' in compute_order.csv")
    tau = pd.to_numeric(out["tau"], errors="coerce")
    if MODE.lower() == "tau":
        out["J"] = 1.0 / tau
    elif MODE.lower() == "j":
        out["J"] = tau
    else:
        raise ValueError("MODE must be 'tau' or 'J'")
    out = out[np.isfinite(out["J"]) & (out["J"] > 0)]
    return out


def compute_edges(vals: np.ndarray) -> np.ndarray:
    vals = np.asarray(sorted(np.unique(vals)), dtype=float)
    if vals.size == 1:
        v = vals[0]
        return np.array([v - 0.5, v + 0.5], dtype=float)
    mids = 0.5 * (vals[:-1] + vals[1:])
    first = vals[0] - 0.5 * (vals[1] - vals[0])
    last = vals[-1] + 0.5 * (vals[-1] - vals[-2])
    return np.concatenate([[first], mids, [last]])


def classify_phase(ordered: bool, rigid: bool) -> int:
    # 0 solid, 1 solid flock, 2 liquid flock, 3 liquid
    if ordered and rigid:
        return 1
    if ordered and not rigid:
        return 2
    if (not ordered) and rigid:
        return 0
    return 3


def get_region_label(code: int) -> str:
    return {
        0: "Solid",
        1: "Solid flock",
        2: "Liquid flock",
        3: "Liquid",
    }[code]


def main():
    here = Path(__file__).resolve().parent
    csv_path = here / "compute_order.csv"
    cols_path = here / "compute_order.csv.cols.txt"

    if not csv_path.exists():
        raise SystemExit(f"Missing {csv_path}")
    if not cols_path.exists():
        raise SystemExit(f"Missing {cols_path}")

    cols = read_cols_file(cols_path)
    if csv_has_header(csv_path, cols):
        df = pd.read_csv(csv_path)
    else:
        df = pd.read_csv(csv_path, header=None, names=cols)

    df = compute_J(df)
    df, chosen = apply_filters(df, FILTERS, CC_VALUE)

    if df.empty:
        raise SystemExit("No rows left after filtering. Adjust FILTERS/CC_VALUE.")

    order_col = pick_existing_column(df, ORDER_COL_CANDIDATES)
    if RIGIDITY_MODE.lower() == "alpha":
        rigid_col = pick_existing_column(df, ALPHA_COL_CANDIDATES)
        rigid_thresh = ALPHA_SOLID_THRESHOLD
        rigid_label = r"$\tau_{\alpha}$"
    elif RIGIDITY_MODE.lower() == "selfint":
        rigid_col = pick_existing_column(df, SELFINT_COL_CANDIDATES)
        rigid_thresh = SELFINT_SOLID_THRESHOLD
        rigid_label = r"$\min F_s$"
    else:
        raise ValueError("RIGIDITY_MODE must be 'alpha' or 'selfint'")

    needed = [X_COL, "J", order_col, rigid_col]
    for c in needed:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    work = df.copy()
    for c in [X_COL, "J", order_col, rigid_col]:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna(subset=[X_COL, "J", order_col, rigid_col]).copy()

    # Aggregate over seeds / repeats
    agg = (
        work.groupby([X_COL, "J"], dropna=False)
        .agg(
            Obar=(order_col, "mean"),
            Rbar=(rigid_col, "mean"),
            n=(order_col, "size"),
        )
        .reset_index()
        .sort_values([X_COL, "J"])
    )

    if agg.empty:
        raise SystemExit("No aggregated data available after grouping.")

    x_vals = np.array(sorted(agg[X_COL].unique()), dtype=float)
    y_vals = np.array(sorted(agg["J"].unique()), dtype=float)

    # Full rectangular grid to show missing points too
    grid_index = pd.MultiIndex.from_product([x_vals, y_vals], names=[X_COL, "J"])
    full = agg.set_index([X_COL, "J"]).reindex(grid_index).reset_index()

    O_grid = full.pivot(index="J", columns=X_COL, values="Obar").to_numpy(dtype=float)
    R_grid = full.pivot(index="J", columns=X_COL, values="Rbar").to_numpy(dtype=float)

    # Classify phases
    phase_grid = np.full_like(O_grid, np.nan, dtype=float)
    for iy in range(O_grid.shape[0]):
        for ix in range(O_grid.shape[1]):
            o = O_grid[iy, ix]
            r = R_grid[iy, ix]
            if not np.isfinite(o) or not np.isfinite(r):
                continue
            ordered = (o >= O_THRESHOLD)
            rigid = (r >= rigid_thresh)
            phase_grid[iy, ix] = classify_phase(ordered, rigid)

    x_edges = compute_edges(x_vals)
    y_edges = compute_edges(y_vals)

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111)

    cmap = ListedColormap(PHASE_COLORS)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)

    # Background phases
    ax.pcolormesh(
        x_edges,
        y_edges,
        phase_grid,
        cmap=cmap,
        norm=norm,
        shading="flat",
        alpha=0.95,
    )

    # Missing points as light gray squares
    missing = ~np.isfinite(phase_grid)
    if np.any(missing):
        Xm, Ym = np.meshgrid(x_vals, y_vals)
        ax.scatter(
            Xm[missing],
            Ym[missing],
            s=52,
            marker="s",
            facecolor="#f2f2f2",
            edgecolor="#bdbdbd",
            linewidth=0.8,
            zorder=5,
            label="missing / failed",
        )

    # Sampled points
    if WRITE_POINT_MARKERS:
        sampled = np.isfinite(O_grid) & np.isfinite(R_grid)
        Xs, Ys = np.meshgrid(x_vals, y_vals)
        ax.scatter(
            Xs[sampled],
            Ys[sampled],
            s=22,
            c="k",
            marker="o",
            linewidths=0,
            zorder=6,
        )

    # Boundary lines
    if SHOW_BOUNDARY_LINES and len(x_vals) >= 2 and len(y_vals) >= 2:
        if np.isfinite(O_grid).sum() >= 4:
            try:
                ax.contour(
                    x_vals,
                    y_vals,
                    O_grid,
                    levels=[O_THRESHOLD],
                    colors=[FLOCK_LINE_COLOR],
                    linewidths=2.2,
                    zorder=7,
                )
            except Exception:
                pass

        if np.isfinite(R_grid).sum() >= 4:
            try:
                ax.contour(
                    x_vals,
                    y_vals,
                    R_grid,
                    levels=[rigid_thresh],
                    colors=[RIGID_LINE_COLOR],
                    linewidths=2.2,
                    linestyles=["--"],
                    zorder=7,
                )
            except Exception:
                pass

    # Region labels
    if WRITE_REGION_LABELS:
        for code in [0, 1, 2, 3]:
            mask = (phase_grid == code)
            if np.any(mask):
                Xc, Yc = np.meshgrid(x_vals, y_vals)
                xm = float(np.median(Xc[mask]))
                ym = float(np.median(Yc[mask]))
                ax.text(
                    xm, ym,
                    get_region_label(code),
                    ha="center", va="center",
                    fontsize=12,
                    color="black",
                    weight="semibold",
                    zorder=8,
                )

    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(r"$J$")
    ax.set_xlim(x_edges[0], x_edges[-1])
    ax.set_ylim(y_edges[0], y_edges[-1])

    handles = [
        mpl.lines.Line2D([0], [0], color=FLOCK_LINE_COLOR, lw=2.2, label=fr"$\langle O \rangle_t = {O_THRESHOLD:g}$"),
        mpl.lines.Line2D([0], [0], color=RIGID_LINE_COLOR, lw=2.2, ls="--", label=fr"{rigid_label} = {rigid_thresh:g}"),
    ]

    if np.any(missing):
        handles.append(
            mpl.lines.Line2D([0], [0], marker="s", color="none",
                             markerfacecolor="#f2f2f2", markeredgecolor="#bdbdbd",
                             markersize=7, label="missing / failed")
        )

    ax.legend(handles=handles, frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0))

    title_parts = []
    if "cc" in chosen and chosen["cc"] is not None:
        title_parts.append(f"cc={int(chosen['cc'])}")
    for key in ["v", "nu", "gamma", "line", "k"]:
        if key in chosen and chosen[key] is not None:
            title_parts.append(f"{key}={chosen[key]}")
    title_parts.append(f"rigidity={RIGIDITY_MODE}")
    ax.set_title(", ".join(title_parts), fontsize=12)

    fig.tight_layout()

    outdir = here / "combined_phase_map_out"
    outdir.mkdir(parents=True, exist_ok=True)

    cc_tag = f"cc{int(chosen['cc'])}" if ("cc" in chosen and chosen["cc"] is not None) else "ccNA"
    outname = f"combined_phase_map__{cc_tag}__mode{MODE.lower()}__rigid{RIGIDITY_MODE.lower()}.png"
    outpath = outdir / outname
    fig.savefig(outpath, dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close(fig)

    print("[INFO] Mode:", MODE)
    print("[INFO] Rigidity mode:", RIGIDITY_MODE)
    print("[INFO] Order column:", order_col)
    print("[INFO] Rigidity column:", rigid_col)
    print("[INFO] Filters used:", chosen)
    print("[INFO] Wrote:", outpath)


if __name__ == "__main__":
    main()
