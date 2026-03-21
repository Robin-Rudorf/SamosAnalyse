#!/usr/bin/env python3
"""
Feedback test without censoring:
Compare alpha_relaxation_time (tau_alpha) between flocking and non-flocking
outcomes at a fixed bistable tau.

Put this script into the same folder as:
  - compute_order.csv
  - compute_order.csv.cols.txt

Edit CONFIG and run:
  python feedback_no_censor.py
"""

import os
import sys
from typing import List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# CONFIG (edit these)
# =========================
CSV_FILE = "compute_order.csv"
COLS_FILE = "compute_order.csv.cols.txt"
OUTDIR = "feedback_no_censor_out"

TARGET_TAU = 0.159   # <-- set your bistable tau here
TAU_TOL = 0.0        # if tau is floating, use e.g. 1e-6 or 0.001

FLOCK_THRESH = 0.8
NONFLOCK_THRESH = 0.2

# Optional: if you still have some extreme values, you can filter them:
TAU_ALPHA_MIN = None   # e.g. 0
TAU_ALPHA_MAX = None   # e.g. 1e6
# =========================


def read_cols(path_cols: str) -> List[str]:
    with open(path_cols, "r", encoding="utf-8") as f:
        txt = f.read().strip()
    if "Cols:" in txt:
        txt = txt.split("Cols:", 1)[1].strip()
    txt = txt.replace("\n", "").replace(" ", "")
    cols = [c for c in txt.split(",") if c]
    if not cols:
        raise ValueError(f"Could not parse columns from {path_cols}")
    return cols


def safe_float_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def classify(o: float) -> str:
    if o >= FLOCK_THRESH:
        return "flock"
    if o <= NONFLOCK_THRESH:
        return "nonflock"
    return "intermediate"


def main():
    if not os.path.exists(CSV_FILE):
        print(f"ERROR: CSV not found: {CSV_FILE}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(COLS_FILE):
        print(f"ERROR: Cols file not found: {COLS_FILE}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTDIR, exist_ok=True)

    cols = read_cols(COLS_FILE)
    df = pd.read_csv(CSV_FILE, header=None, names=cols)

    # Required columns
    for c in ["tau", "O_mean", "alpha_relaxation_time"]:
        if c not in df.columns:
            raise KeyError(f"Missing '{c}'. Available: {list(df.columns)}")

    # Numeric conversion
    df["tau"] = safe_float_series(df["tau"])
    df["O_mean"] = safe_float_series(df["O_mean"])
    df["alpha_relaxation_time"] = safe_float_series(df["alpha_relaxation_time"])

    # Drop missing
    df = df.dropna(subset=["tau", "O_mean", "alpha_relaxation_time"]).copy()

    # Filter to chosen tau
    df = df[np.abs(df["tau"] - TARGET_TAU) <= TAU_TOL].copy()
    if df.empty:
        raise ValueError(
            f"No rows left after filtering on tau={TARGET_TAU} with tol={TAU_TOL}. "
            "Increase TAU_TOL or check tau values in the CSV."
        )

    # Optional tau_alpha range filter
    if TAU_ALPHA_MIN is not None:
        df = df[df["alpha_relaxation_time"] >= TAU_ALPHA_MIN].copy()
    if TAU_ALPHA_MAX is not None:
        df = df[df["alpha_relaxation_time"] <= TAU_ALPHA_MAX].copy()

    # Classify
    df["class"] = df["O_mean"].apply(classify)

    # Main comparison set: flock vs nonflock
    df2 = df[df["class"].isin(["nonflock", "flock"])].copy()
    if df2.empty:
        raise ValueError(
            "No rows classified as flock/nonflock with current thresholds. "
            "Adjust thresholds or choose a different TARGET_TAU."
        )

    suffix = f"tau{TARGET_TAU:g}_tol{TAU_TOL:g}"

    # Summary
    summary = (df2.groupby("class")
               .agg(
                   n=("alpha_relaxation_time", "size"),
                   tau_alpha_median=("alpha_relaxation_time", "median"),
                   tau_alpha_mean=("alpha_relaxation_time", "mean"),
                   tau_alpha_std=("alpha_relaxation_time", "std"),
                   O_mean_mean=("O_mean", "mean"),
               )
               .reset_index())
    summary_path = os.path.join(OUTDIR, f"summary_{suffix}.csv")
    summary.to_csv(summary_path, index=False)

    # Save filtered labeled data
    labeled_path = os.path.join(OUTDIR, f"filtered_labeled_{suffix}.csv")
    df.to_csv(labeled_path, index=False)

    # -------------------------
    # Plot 1: Box + jitter points of tau_alpha by class
    # -------------------------
    fig1 = plt.figure(figsize=(6.6, 4.6))
    ax1 = fig1.add_subplot(111)

    classes = ["nonflock", "flock"]
    data = [df2.loc[df2["class"] == c, "alpha_relaxation_time"].values for c in classes]
    ax1.boxplot(data, labels=classes, showfliers=False)

    rng = np.random.default_rng(0)
    for i, c in enumerate(classes, start=1):
        y = df2.loc[df2["class"] == c, "alpha_relaxation_time"].values
        x = rng.normal(loc=i, scale=0.04, size=len(y))
        ax1.scatter(x, y, s=18, alpha=0.75)

    ax1.set_ylabel("alpha_relaxation_time (tau_alpha)")
    ax1.set_title(
        f"tau_alpha by outcome at tau={TARGET_TAU:g} (tol={TAU_TOL:g})\n"
        f"nonflock: O_mean <= {NONFLOCK_THRESH}, flock: O_mean >= {FLOCK_THRESH}"
    )
    ax1.grid(True, axis="y", alpha=0.3)

    out1 = os.path.join(OUTDIR, f"tau_alpha_by_class_{suffix}.png")
    fig1.tight_layout()
    fig1.savefig(out1, dpi=220)
    plt.close(fig1)

    # -------------------------
    # Plot 2: Scatter tau_alpha vs O_mean (color by class, includes intermediate)
    # -------------------------
    fig2 = plt.figure(figsize=(6.8, 5.0))
    ax2 = fig2.add_subplot(111)

    for cls in ["nonflock", "intermediate", "flock"]:
        sub = df[df["class"] == cls]
        if sub.empty:
            continue
        ax2.scatter(sub["O_mean"].values, sub["alpha_relaxation_time"].values,
                    s=18, alpha=0.8, label=cls)

    ax2.set_xlabel("O_mean")
    ax2.set_ylabel("alpha_relaxation_time (tau_alpha)")
    ax2.set_title(f"tau_alpha vs O_mean at tau={TARGET_TAU:g} (tol={TAU_TOL:g})")
    ax2.grid(True, alpha=0.3)
    ax2.legend(frameon=False)

    out2 = os.path.join(OUTDIR, f"scatter_tau_alpha_vs_Omean_{suffix}.png")
    fig2.tight_layout()
    fig2.savefig(out2, dpi=220)
    plt.close(fig2)

    # -------------------------
    # Plot 3 (optional): Overlaid histogram of tau_alpha for flock vs nonflock
    # -------------------------
    fig3 = plt.figure(figsize=(6.8, 4.6))
    ax3 = fig3.add_subplot(111)

    ta_nf = df2.loc[df2["class"] == "nonflock", "alpha_relaxation_time"].values
    ta_f = df2.loc[df2["class"] == "flock", "alpha_relaxation_time"].values

    bins = 30
    ax3.hist(ta_nf, bins=bins, density=True, alpha=0.5, label="nonflock")
    ax3.hist(ta_f, bins=bins, density=True, alpha=0.5, label="flock")

    ax3.set_xlabel("alpha_relaxation_time (tau_alpha)")
    ax3.set_ylabel("density")
    ax3.set_title(f"tau_alpha distribution at tau={TARGET_TAU:g}")
    ax3.grid(True, alpha=0.3)
    ax3.legend(frameon=False)

    out3 = os.path.join(OUTDIR, f"hist_tau_alpha_flock_vs_nonflock_{suffix}.png")
    fig3.tight_layout()
    fig3.savefig(out3, dpi=220)
    plt.close(fig3)

    print("Done.")
    print(f"  Wrote: {summary_path}")
    print(f"  Wrote: {out1}")
    print(f"  Wrote: {out2}")
    print(f"  Wrote: {out3}")
    print(f"  Wrote: {labeled_path}")


if __name__ == "__main__":
    main()