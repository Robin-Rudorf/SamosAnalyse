#!/usr/bin/env python3
"""
combined_phase_map_truecontour_crossover.py
-------------------------------------------
Combined flocking + rigidity phase map with:

- equal spacing between sampled p0 and J values in the displayed grid
- TRUE contour lines taken from the underlying numerical fields
- contour segments projected onto the equal-spacing display
- optional crossover region (threshold-sensitive / ambiguous band)
- no black sample-point dots by default
- missing / failed parameter points shown as light-gray cells

Put this script in the SAME folder as:
  - compute_order.csv
  - compute_order.csv.cols.txt
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

# --- order thresholds ---
#   O < ORDER_LOW_THRESHOLD          -> unordered
#   O > ORDER_HIGH_THRESHOLD         -> ordered
#   otherwise                        -> crossover
ORDER_LOW_THRESHOLD = 0.50
ORDER_HIGH_THRESHOLD = 0.70

# --- rigidity thresholds ---
# alpha:
#   tau_alpha < ALPHA_LIQUID_THRESHOLD   -> liquid / relaxing
#   tau_alpha > ALPHA_SOLID_THRESHOLD    -> solid / rigid
#   otherwise                            -> crossover
ALPHA_LIQUID_THRESHOLD = 30.0
ALPHA_SOLID_THRESHOLD = 100.0

# self intermediate scattering:
#   minFs < SELFINT_LIQUID_THRESHOLD     -> liquid / relaxing
#   minFs > SELFINT_SOLID_THRESHOLD      -> solid / rigid
#   otherwise                            -> crossover
SELFINT_LIQUID_THRESHOLD = 0.15
SELFINT_SOLID_THRESHOLD = 0.30

# x-axis
X_COL = "permult"
X_LABEL = r"$p_0$"

# slice selection; None => auto-pick most frequent
CC_VALUE = None
FILTERS = {
    "v": None,
    "nu": None,
    "gamma": None,
    "line": None,
    "k": None,
}

# appearance
FIGSIZE = (8.3, 5.9)
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
    "#fff3bf",  # crossover
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


def classify_order(o: float) -> str:
    if o < ORDER_LOW_THRESHOLD:
        return "unordered"
    if o > ORDER_HIGH_THRESHOLD:
        return "ordered"
    return "crossover"


def classify_rigidity_alpha(a: float) -> str:
    if a < ALPHA_LIQUID_THRESHOLD:
        return "liquid"
    if a > ALPHA_SOLID_THRESHOLD:
        return "solid"
    return "crossover"


def classify_rigidity_selfint(s: float) -> str:
    if s < SELFINT_LIQUID_THRESHOLD:
        return "liquid"
    if s > SELFINT_SOLID_THRESHOLD:
        return "solid"
    return "crossover"


def classify_phase(o: float, r: float) -> int:
    o_state = classify_order(o)
    if RIGIDITY_MODE.lower() == "alpha":
        r_state = classify_rigidity_alpha(r)
    else:
        r_state = classify_rigidity_selfint(r)

    if o_state == "crossover" or r_state == "crossover":
        return 4  # crossover
    if o_state == "ordered" and r_state == "solid":
        return 1  # solid flock
    if o_state == "ordered" and r_state == "liquid":
        return 2  # liquid flock
    if o_state == "unordered" and r_state == "solid":
        return 0  # solid
    return 3      # liquid


def phase_label(code: int) -> str:
    return {0: "Solid", 1: "Solid flock", 2: "Liquid flock", 3: "Liquid"}[code]


def choose_region_positions(phase_grid: np.ndarray):
    ny, nx = phase_grid.shape
    Xc, Yc = np.meshgrid(np.arange(nx), np.arange(ny))
    out = {}
    for code in [0, 1, 2, 3]:  # skip crossover on purpose
        mask = phase_grid == code
        if np.any(mask):
            out[code] = (float(np.median(Xc[mask])), float(np.median(Yc[mask])))
    return out


def extract_true_contours(x_vals: np.ndarray, y_vals: np.ndarray, Z: np.ndarray, level: float):
    if np.sum(np.isfinite(Z)) < 4 or len(x_vals) < 2 or len(y_vals) < 2:
        return []

    fig = plt.figure()
    ax = fig.add_subplot(111)
    segments = []
    try:
        cs = ax.contour(x_vals, y_vals, Z, levels=[level])
        if hasattr(cs, "allsegs") and len(cs.allsegs) > 0:
            for seg in cs.allsegs[0]:
                if seg is not None and len(seg) >= 2:
                    segments.append(np.asarray(seg, dtype=float).copy())
        elif hasattr(cs, "collections"):
            for coll in cs.collections:
                for path in coll.get_paths():
                    v = path.vertices
                    if v is not None and len(v) >= 2:
                        segments.append(np.asarray(v, dtype=float).copy())
    finally:
        plt.close(fig)
    return segments


def project_true_to_display(vertices: np.ndarray, x_vals: np.ndarray, y_vals: np.ndarray):
    xs = vertices[:, 0]
    ys = vertices[:, 1]

    xd = np.interp(xs, x_vals, np.arange(len(x_vals), dtype=float))
    yd = np.interp(ys, y_vals, np.arange(len(y_vals), dtype=float))

    if len(vertices) >= 2:
        x_tol = max(1e-12, 1e-8 * max(1.0, np.max(np.abs(x_vals))))
        y_tol = max(1e-12, 1e-8 * max(1.0, np.max(np.abs(y_vals))))

        if abs(xs[0] - x_vals[0]) < x_tol:
            xd[0] = -0.5
        elif abs(xs[0] - x_vals[-1]) < x_tol:
            xd[0] = len(x_vals) - 0.5
        if abs(ys[0] - y_vals[0]) < y_tol:
            yd[0] = -0.5
        elif abs(ys[0] - y_vals[-1]) < y_tol:
            yd[0] = len(y_vals) - 0.5

        if abs(xs[-1] - x_vals[0]) < x_tol:
            xd[-1] = -0.5
        elif abs(xs[-1] - x_vals[-1]) < x_tol:
            xd[-1] = len(x_vals) - 0.5
        if abs(ys[-1] - y_vals[0]) < y_tol:
            yd[-1] = -0.5
        elif abs(ys[-1] - y_vals[-1]) < y_tol:
            yd[-1] = len(y_vals) - 0.5

    return np.column_stack([xd, yd])


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
        high_rigid = ALPHA_SOLID_THRESHOLD
        rigid_high_legend = fr"$\tau_\alpha={high_rigid:g}$"
    elif RIGIDITY_MODE.lower() == "selfint":
        rigid_col = pick_existing_column(df, SELFINT_COL_CANDIDATES)
        high_rigid = SELFINT_SOLID_THRESHOLD
        rigid_high_legend = fr"$\min F_s={high_rigid:g}$"
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
            phase_grid[iy, ix] = classify_phase(o, r)

    x_edges = np.arange(nx + 1) - 0.5
    y_edges = np.arange(ny + 1) - 0.5

    fig = plt.figure(figsize=FIGSIZE)
    ax = fig.add_subplot(111)

    cmap = ListedColormap(PHASE_COLORS)
    cmap.set_bad(MISSING_COLOR)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)

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
        zorder=1,
    )

    missing = ~np.isfinite(phase_grid)
    if np.any(missing):
        Xm, Ym = np.meshgrid(np.arange(nx), np.arange(ny))
        ax.scatter(
            Xm[missing], Ym[missing],
            s=54, marker="s",
            facecolor=MISSING_COLOR, edgecolor=MISSING_EDGE,
            linewidth=1.0, zorder=3,
        )

    if SHOW_SAMPLE_MARKERS:
        sampled = np.isfinite(phase_grid)
        Xm, Ym = np.meshgrid(np.arange(nx), np.arange(ny))
        ax.scatter(Xm[sampled], Ym[sampled], s=10, c="k", zorder=4)

    if SHOW_BOUNDARY_LINES:
        for seg in extract_true_contours(x_vals, j_vals, O_grid, ORDER_HIGH_THRESHOLD):
            disp = project_true_to_display(seg, x_vals, j_vals)
            ax.plot(disp[:, 0], disp[:, 1], color=FLOCK_LINE_COLOR, lw=2.7, zorder=5)
        for seg in extract_true_contours(x_vals, j_vals, R_grid, high_rigid):
            disp = project_true_to_display(seg, x_vals, j_vals)
            ax.plot(disp[:, 0], disp[:, 1], color=RIGID_LINE_COLOR, lw=2.9, ls="--", zorder=5)

    if SHOW_REGION_LABELS:
        pos = choose_region_positions(phase_grid)
        for code, (x0, y0) in pos.items():
            ax.text(
                x0, y0, phase_label(code),
                ha="center", va="center",
                fontsize=12, weight="semibold",
                color="black", zorder=6
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
        mpl.lines.Line2D([0], [0], color=FLOCK_LINE_COLOR, lw=2.7,
                         label=fr"$\langle O\rangle_t={ORDER_HIGH_THRESHOLD:g}$"),
        mpl.lines.Line2D([0], [0], color=RIGID_LINE_COLOR, lw=2.9, ls="--",
                         label=rigid_high_legend),
        mpl.patches.Patch(facecolor=PHASE_COLORS[4], edgecolor="none", label="crossover"),
        mpl.lines.Line2D([0], [0], marker="s", color="none", markerfacecolor=MISSING_COLOR,
                         markeredgecolor=MISSING_EDGE, markersize=8, label="missing / failed"),
    ]
    ax.legend(handles=handles, frameon=False, loc="center left", bbox_to_anchor=(1.02, 0.42))

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
    outname = f"combined_phase_map_truecontour_crossover__{cc_tag}__mode{MODE.lower()}__rigid{RIGIDITY_MODE.lower()}.png"
    outpath = outdir / outname
    fig.savefig(outpath, dpi=OUTPUT_DPI, bbox_inches="tight")
    plt.close(fig)

    print("[INFO] Mode:", MODE)
    print("[INFO] Rigidity mode:", RIGIDITY_MODE)
    print("[INFO] Order column:", order_col)
    print("[INFO] Rigidity column:", rigid_col)
    print("[INFO] Filters used:", chosen)
    print("[INFO] Wrote:", outpath)
    print("[INFO] Order band:", ORDER_LOW_THRESHOLD, ORDER_HIGH_THRESHOLD)
    if RIGIDITY_MODE.lower() == "alpha":
        print("[INFO] Alpha band:", ALPHA_LIQUID_THRESHOLD, ALPHA_SOLID_THRESHOLD)
    else:
        print("[INFO] SelfInt band:", SELFINT_LIQUID_THRESHOLD, SELFINT_SOLID_THRESHOLD)


if __name__ == "__main__":
    main()
