#!/usr/bin/env python3
"""
plot_coupling_O_rigidity.py
---------------------------
Scatter/coupling plot between temporal mean order <O>_t and a rigidity/relaxation metric
read from compute_order.csv.

Put this script in the SAME folder as:
  - compute_order.csv
  - compute_order.csv.cols.txt

It can plot either:
  - alpha relaxation time vs <O>_t
  - minSelfInt (or another self-intermediate-scattering proxy) vs <O>_t

Config at the top:
  - MODE = "tau"   : external aligner, convert tau -> J = 1/tau
  - MODE = "J"     : pair aligner, the CSV 'tau' column already stores J
  - METRIC_MODE    : "alpha" or "selfint"
  - POINT_MODE     : "raw" (each run is a point) or "agg" (mean over seeds per parameter point)

Outputs go to ./coupling_O_rigidity_out/
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import math
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# =========================
# USER SETTINGS (edit here)
# =========================
MODE = "tau"          # "tau" (external, J=1/tau) or "J" (pair, tau column already is J)
METRIC_MODE = "alpha" # "alpha" or "selfint"
POINT_MODE = "raw"    # "raw" or "agg"

PERMULT_LIST = None   # e.g. [2.8] or 2.8

FILTERS = {
    "v": None,
    "nu": None,
    "gamma": None,
    "line": None,
    "k": None,
}

ORDER_COL = "O_mean"

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

CMAP_NAME = "viridis"
OUTPUT_DPI = 300
# =========================


def _read_cols_file(cols_path: Path) -> List[str]:
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


def _csv_has_header(csv_path: Path, cols: List[str]) -> bool:
    first = csv_path.open("r", encoding="utf-8", errors="ignore").readline().strip()
    toks = [t.strip() for t in first.split(",")]
    hits = sum(1 for t in toks if t in set(cols))
    return hits >= 2


def _auto_pick_mode_value(df: pd.DataFrame, key: str):
    if key not in df.columns:
        return None
    s = df[key].dropna()
    if s.empty:
        return None
    return s.value_counts().idxmax()


def _apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    chosen = {}
    out = df.copy()
    for k, v in filters.items():
        if k not in out.columns:
            continue
        if v is None:
            v = _auto_pick_mode_value(out, k)
        chosen[k] = v
        if v is not None:
            out = out[out[k] == v]
    return out, chosen


def _compute_J(df: pd.DataFrame) -> pd.DataFrame:
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


def _pick_existing_column(df: pd.DataFrame, candidates: List[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c

    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(s).lower())

    norm_map = {_norm(col): col for col in df.columns}
    for c in candidates:
        nc = _norm(c)
        if nc in norm_map:
            return norm_map[nc]

    raise ValueError(
        "Could not find any matching metric column. Tried: "
        + ", ".join(candidates)
        + ". Available columns include: "
        + ", ".join(map(str, list(df.columns)[:40]))
    )


def _prepare(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    if ORDER_COL not in df.columns:
        raise ValueError(f"Missing required column '{ORDER_COL}'")

    if METRIC_MODE.lower() == "alpha":
        metric_col = _pick_existing_column(df, ALPHA_COL_CANDIDATES)
    elif METRIC_MODE.lower() == "selfint":
        metric_col = _pick_existing_column(df, SELFINT_COL_CANDIDATES)
    else:
        raise ValueError("METRIC_MODE must be 'alpha' or 'selfint'")

    out = df.copy()
    for c in [ORDER_COL, metric_col, "permult", "cc", "J"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    needed = [ORDER_COL, metric_col, "permult", "cc", "J"]
    out = out.dropna(subset=[c for c in needed if c in out.columns]).copy()

    if POINT_MODE.lower() == "agg":
        gcols = ["permult", "cc", "J"]
        for c in ["v", "nu", "gamma", "line", "k"]:
            if c in out.columns:
                gcols.append(c)
        out = (
            out.groupby(gcols, dropna=False)[[ORDER_COL, metric_col]]
            .mean()
            .reset_index()
        )

    return out, metric_col


def _labels(metric_col: str) -> Tuple[str, str]:
    ylab = r"$\langle O \rangle_t$"
    if METRIC_MODE.lower() == "alpha":
        xlab = r"$\tau_{\alpha}$"
    else:
        xlab = r"$\min F_s$"
    return xlab, ylab


def _plot_one(df: pd.DataFrame, metric_col: str, permult_val: float, outdir: Path) -> Path:
    sub = df[df["permult"] == permult_val].copy()
    if sub.empty:
        raise ValueError(f"No data for permult={permult_val}")

    Jvals = sub["J"].to_numpy(float)
    norm = mpl.colors.Normalize(vmin=float(np.min(Jvals)), vmax=float(np.max(Jvals)))
    cmap = mpl.cm.get_cmap(CMAP_NAME)

    sqrtN = np.sqrt(sub["cc"].to_numpy(float))
    s = 25 + 2.5 * (sqrtN - np.min(sqrtN))

    fig = plt.figure(figsize=(7.2, 5.2))
    ax = fig.add_subplot(111)

    ax.scatter(
        sub[metric_col].to_numpy(float),
        sub[ORDER_COL].to_numpy(float),
        c=Jvals,
        cmap=cmap,
        norm=norm,
        s=s,
        alpha=0.85,
        edgecolors="none",
    )

    xlab, ylab = _labels(metric_col)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.3)
    ax.set_title(f"permult={permult_val:g}")

    cbar = fig.colorbar(mpl.cm.ScalarMappable(cmap=cmap, norm=norm), ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$J$", rotation=90)

    fig.tight_layout()
    fname = f"coupling_{METRIC_MODE.lower()}_vs_O__permult{permult_val:g}__mode{MODE.lower()}__{POINT_MODE.lower()}.png"
    outpath = outdir / fname
    fig.savefig(outpath, dpi=OUTPUT_DPI)
    plt.close(fig)
    return outpath


def main():
    here = Path(__file__).resolve().parent
    csv_path = here / "compute_order.csv"
    cols_path = here / "compute_order.csv.cols.txt"

    if not csv_path.exists():
        raise SystemExit(f"Missing {csv_path}")
    if not cols_path.exists():
        raise SystemExit(f"Missing {cols_path}")

    cols = _read_cols_file(cols_path)
    if _csv_has_header(csv_path, cols):
        df = pd.read_csv(csv_path)
    else:
        df = pd.read_csv(csv_path, header=None, names=cols)

    df = _compute_J(df)
    df_f, chosen = _apply_filters(df, FILTERS)
    if df_f.empty:
        raise SystemExit("No rows left after filtering. Try loosening FILTERS.")

    prepared, metric_col = _prepare(df_f)

    outdir = here / "coupling_O_rigidity_out"
    outdir.mkdir(parents=True, exist_ok=True)

    if PERMULT_LIST is None:
        permults = sorted(prepared["permult"].unique())
    elif isinstance(PERMULT_LIST, (int, float)):
        permults = [float(PERMULT_LIST)]
    else:
        permults = PERMULT_LIST

    written = []
    for p in permults:
        try:
            written.append(_plot_one(prepared, metric_col, float(p), outdir))
        except Exception as e:
            print(f"[WARN] Skipping permult={p}: {e}")

    print("[INFO] MODE:", MODE)
    print("[INFO] METRIC_MODE:", METRIC_MODE)
    print("[INFO] POINT_MODE:", POINT_MODE)
    print("[INFO] Metric column used:", metric_col)
    print("[INFO] Filters used:", chosen)
    print("[INFO] Wrote:")
    for w in written:
        print(" ", w)


if __name__ == "__main__":
    main()
