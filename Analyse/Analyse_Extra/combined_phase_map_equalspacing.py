#!/usr/bin/env python3
"""
combined_phase_map_equalspacing.py
---------------------------------
Improved combined flocking + rigidity phase map from compute_order.csv.

Place this script in the SAME folder as:
  - compute_order.csv
  - compute_order.csv.cols.txt

Features:
- equal spacing between sampled parameter values on BOTH axes
- no black sample-point dots by default
- missing / failed parameter points shown as light-gray cells only
- smoother boundary lines drawn in index-space
- cleaner publication-style appearance
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap, BoundaryNorm

# =========================
# USER SETTINGS (edit here)
# =========================
MODE = "J"                # "tau" (external: J=1/tau) or "J" (pair: tau column already is J)
RIGIDITY_MODE = "alpha"   # "alpha" or "selfint"

O_THRESHOLD = 0.60
ALPHA_SOLID_THRESHOLD = 100.0
SELFINT_SOLID_THRESHOLD = 0.30

X_COL = "permult"
X_LABEL = r"$p_0$"

CC_VALUE = None
FILTERS = {
    "v": None,
    "nu": None,
    "gamma": None,
    "line": None,
    "k": None,
}

FIGSIZE = (8.2, 5.8)
OUTPUT_DPI = 340
SHOW_BOUNDARY_LINES = True
SHOW_REGION_LABELS = True
SHOW_SAMPLE_MARKERS = False

FLOCK_LINE_COLOR = "#d62728"
RIGID_LINE_COLOR = "#1f77b4"

PHASE_COLORS = [
    "#d9d9d9",  # solid
    "#cfe8ff",  # solid flock
    "#f7d4dc",  # liquid flock
    "#dff0d0",  # liquid
]
MISSING_COLOR = "#efefef"
MISSING_EDGE = "#b8b8b8"
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
        + ", ".join(map(str, list(df.columns)[:60]))
    )


def auto_pick_mode_value(df: pd.DataFrame, key: str):
    if key not in df.columns:
        return None
    s = df[key].dropna()
    if s.empty:
        return None
    return s.value_counts().idxmax()


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any], cc_value):
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


def classify_phase(ordered: bool, rigid: bool) -> int:
    if ordered and rigid:
        return 1
    if ordered and not rigid:
        return 2
    if (not ordered) and rigid:
        return 0
    return 3


def phase_label(code: int) -> str:
    return {0: "Solid", 1: "Solid flock", 2: "Liquid flock", 3: "Liquid"}[code]


def crossing_indices_from_columns(Z: np.ndarray, thresh: float, prefer: str = "last_above"):
    ny, nx = Z.shape
    pts = []
    for ix in range(nx):
        col = Z[:, ix]
        if np.sum(np.isfinite(col)) < 2:
            continue

        valid = np.where(np.isfinite(col))[0]
        yv = valid.astype(float)
        zv = col[valid]

        mask_above = zv >= thresh
        changes = np.where(mask_above[:-1] != mask_above[1:])[0]
        if len(changes) == 0:
            continue

        j = int(changes[-1] if prefer == "last_above" else changes[0])
        y0, y1 = yv[j], yv[j + 1]
        z0, z1 = zv[j], zv[j + 1]
        if not np.isfinite(z0) or not np.isfinite(z1) or z1 == z0:
            continue

        frac = (thresh - z0) / (z1 - z0)
        frac = min(max(frac, 0.0), 1.0)
        pts.append((float(ix), float(y0 + frac * (y1 - y0))))
    return pts


def choose_region_positions(phase_grid: np.ndarray):
    ny, nx = phase_grid.shape
    Xc, Yc = np.meshgrid(np.arange(nx), np.arange(ny))
    out = {}
    for code in [0, 1, 2, 3]:
        mask = phase_grid == code
        if np.any(mask):
            out[code] = (float(np.median(Xc[mask])), float(np.median(Yc[mask])))
    return out


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
        raise SystemExit("No rows left after filtering.")

    order_col = pick_existing_column(df, ORDER_COL_CANDIDATES)
    if RIGIDITY_MODE.lower() == "alpha":
        rigid_col = pick_existing_column(df, ALPHA_COL_CANDIDATES)
        rigid_thresh = ALPHA_SOLID_THRESHOLD
        rigid_legend = r"$\tau_\alpha=100$"
    elif RIGIDITY_MODE.lower() == "selfint":
        rigid_col = pick_existing_column(df, SELFINT_COL_CANDIDATES)
        rigid_thresh = SELFINT_SOLID_THRESHOLD
        rigid_legend = r"$\min F_s=0.30$"
    else:
        raise ValueError("RIGIDITY_MODE must be 'alpha' or 'selfint'")

    for c in [X_COL, "J", order_col, rigid_col]:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    work = df.copy()
    for c in [X_COL, "J", order_col, rigid_col]:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    work = work.dropna(subset=[X_COL, "J", order_col, rigid_col]).copy()

    agg = (
        work.groupby([X_COL, "J"], dropna=False)
        .agg(Obar=(order_col, "mean"), Rbar=(rigid_col, "mean"), n=(order_col, "size"))
        .reset_index()
        .sort_values([X_COL, "J"])
    )
    if agg.empty:
        raise SystemExit("No aggregated data available.")

    x_vals = np.array(sorted(agg[X_COL].unique()), dtype=float)
    j_vals = np.array(sorted(agg["J"].unique()), dtype=float)

    full_index = pd.MultiIndex.from_product([x_vals, j_vals], names=[X_COL, "J"])
    full = agg.set_index([X_COL, "J"]).reindex(full_index).reset_index()

    O_grid = full.pivot(index="J", columns=X_COL, values="Obar").to_numpy(dtype=float)
    R_grid = full.pivot(index="J", columns=X_COL, values="Rbar").to_numpy(dtype=float)

    ny, nx = O_grid.shape
    phase_grid = np.full((ny, nx), np.nan, dtype=float)
    for iy in range(ny):
        for ix in range(nx):
            o = O_grid[iy, ix]
            r = R_grid[iy, ix]
            if not np.isfinite(o) or not np.isfinite(r):
                continue
            phase_grid[iy, ix] = classify_phase(o >= O_THRESHOLD, r >= rigid_thresh)

    x_edges = np.arange(nx + 1) - 0.5
    y_edges = np.arange(ny + 1) - 0.5

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111)

    cmap = ListedColormap(PHASE_COLORS)
    cmap.set_bad(MISSING_COLOR)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N)

    ax.pcolormesh(
        x_edges,
        y_edges,
        phase_grid,
        cmap=cmap,
        norm=norm,
        shading="flat",
        alpha=1.0,
        edgecolors="white",
        linewidth=0.6,
        antialiased=True,
    )

    missing = ~np.isfinite(phase_grid)
    if np.any(missing):
        Xm, Ym = np.meshgrid(np.arange(nx), np.arange(ny))
        ax.scatter(
            Xm[missing], Ym[missing],
            s=52, marker="s",
            facecolor=MISSING_COLOR, edgecolor=MISSING_EDGE,
            linewidth=1.0, zorder=6,
        )

    if SHOW_SAMPLE_MARKERS:
        sampled = np.isfinite(phase_grid)
        Xm, Ym = np.meshgrid(np.arange(nx), np.arange(ny))
        ax.scatter(Xm[sampled], Ym[sampled], s=10, c="k", zorder=7)

    if SHOW_BOUNDARY_LINES:
        flock_pts = crossing_indices_from_columns(O_grid, O_THRESHOLD, prefer="last_above")
        rigid_pts = crossing_indices_from_columns(R_grid, rigid_thresh, prefer="last_above")
        if len(flock_pts) >= 2:
            xf, yf = zip(*flock_pts)
            ax.plot(xf, yf, color=FLOCK_LINE_COLOR, lw=2.6, zorder=8)
        if len(rigid_pts) >= 2:
            xr, yr = zip(*rigid_pts)
            ax.plot(xr, yr, color=RIGID_LINE_COLOR, lw=2.8, ls="--", zorder=8)

    if SHOW_REGION_LABELS:
        pos = choose_region_positions(phase_grid)
        for code, (x0, y0) in pos.items():
            ax.text(
                x0, y0, phase_label(code),
                ha="center", va="center",
                fontsize=12, weight="semibold",
                color="black", zorder=9
            )

    ax.set_xticks(np.arange(nx))
    ax.set_xticklabels([f"{v:g}" for v in x_vals])

    ax.set_yticks(np.arange(ny))
    y_labels = []
    for v in j_vals:
        if v < 1:
            y_labels.append(f"{v:.2f}")
        elif v < 10:
            y_labels.append(f"{v:.1f}")
        else:
            y_labels.append(f"{v:.0f}")
    ax.set_yticklabels(y_labels)

    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(r"$J$")
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(-0.5, ny - 0.5)

    handles = [
        mpl.lines.Line2D([0], [0], color=FLOCK_LINE_COLOR, lw=2.6, label=fr"$\langle O\rangle_t={O_THRESHOLD:g}$"),
        mpl.lines.Line2D([0], [0], color=RIGID_LINE_COLOR, lw=2.8, ls="--", label=rigid_legend),
        mpl.lines.Line2D([0], [0], marker="s", color="none", markerfacecolor=MISSING_COLOR,
                         markeredgecolor=MISSING_EDGE, markersize=8, label="missing / failed"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0))

    title_parts = []
    if "cc" in chosen and chosen["cc"] is not None:
        title_parts.append(f"cc={int(chosen['cc'])}")
    for key in ["v", "nu", "gamma", "line", "k"]:
        if key in chosen and chosen[key] is not None:
            title_parts.append(f"{key}={chosen[key]}")
    ax.set_title(", ".join(title_parts), fontsize=12)

    fig.tight_layout()
    outdir = here / "combined_phase_map_out"
    outdir.mkdir(parents=True, exist_ok=True)

    cc_tag = f"cc{int(chosen['cc'])}" if ("cc" in chosen and chosen["cc"] is not None) else "ccNA"
    outname = f"combined_phase_map_equalspacing__{cc_tag}__mode{MODE.lower()}__rigid{RIGIDITY_MODE.lower()}.png"
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
