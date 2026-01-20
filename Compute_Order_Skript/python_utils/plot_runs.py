#!/usr/bin/env python3

import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import argparse

# -------------------------- CONFIG (edit here) --------------------------

CSV_PATH = "compute_order.csv"

CONFIG = dict(
            x="tau",
            y="O_var",
            group=None,
            title=None,           # auto if None
            xlabel=None,          # default to column name if None
            ylabel=None,          # default to column name if None
            output=None,          # auto filename if None
            dpi=200,
            marker_every=1,
            x_size=11,            # Diagramm Width (inch)
            y_size=7,             # Diagramm Hight (inch)
            colormap="none",      # Colormap siehe matplotlib-docu
            markersize=10
        )


VALID_COLS = ["cc","rand","tau","v","k","nu","gamma","permult","line","O_mean","O_var","frames_ok","art","isglassy","datacount","minSelfInt"]
# ----------------------- END CONFIG (stop editing) ----------------------


def read_csv_safely(path):
    try:
        df = pd.read_csv(path)
        if set(VALID_COLS).issubset(df.columns):
            return df
    except Exception:
        pass
    df = pd.read_csv(path, header=None, names=VALID_COLS)
    return df

def ensure_numeric(df):
    for c in VALID_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def plot_one(df, cfg, output, title, xcol, ycol, group, xsize, cmap, markersize):
    xcol = xcol or cfg.get("x")
    ycol = ycol or cfg.get("y")
    group_col = group or cfg.get("group")
    title = title or cfg.get("title")
    xlabel = cfg.get("xlabel") or xcol
    ylabel = cfg.get("ylabel") or ycol
    output = output or cfg.get("output")
    dpi = int(cfg.get("dpi",200))
    xsize = int(xsize or cfg.get("x_size",11))
    ysize = int(cfg.get("y_size",7))
    marker_every = max(1, int(cfg.get("marker_every",1)))
    colormap=cmap or cfg.get("colormap")
    markersize=int(markersize or cfg.get("markersize",10))

    if xsize < ysize:
        xsize=ysize

    if ysize < xsize/3:
        ysize=int(xsize/3)

    if xcol not in VALID_COLS or ycol not in VALID_COLS:
        print(f"[SKIP] Invalid x/y in config: x={xcol} y={ycol}", file=sys.stderr)
        return None

    if group_col == "none":
        group_col=None

    if group_col is not None and group_col not in VALID_COLS:
        print(f"[SKIP] Invalid group column: {group_col}", file=sys.stderr)
        return None

    # drop NaN
    gdf = df.dropna(subset=[xcol, ycol])

    if gdf.empty:
        print("[WARN] No data after filtering; skipping plot.", file=sys.stderr)
        return None

    if group_col is None:
        groups = [(None, gdf)]
    else:
        groups = list(gdf.groupby(group_col, dropna=True))

    if colormap == "none":
        colormap=None

    if colormap is not None:
        plt.rcParams['axes.prop_cycle']=plt.cycler("color",getattr(plt.cm,colormap)(np.linspace(0,1,len(groups))))

    plt.figure(figsize=(xsize,ysize))

    for label, sub in groups:
        sub = sub.sort_values(by=xcol)

        x = sub[xcol].values
        y = sub[ycol].values

        plt.plot(x, y, marker=".", ms=markersize, markevery=marker_every, linewidth=1.5, label=f"{group_col}={label}" if group_col is not None else None)

    auto_title = f"{ycol} vs {xcol}" + (f" grouped by {group_col}" if group_col else "")
    plt.title(title or auto_title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    if group_col is not None:
        plt.legend(title=group_col, bbox_to_anchor=(1.02,1), loc="upper left", frameon=True)
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.locator_params(axis='x', nbins=xsize)
    plt.locator_params(axis='y', nbins=10)
    plt.tight_layout()

    outpath = output or f"{xcol}_vs_{ycol}" + (f"_by_{group_col}" if group_col else "") + ".png"
    plt.savefig(outpath, dpi=dpi)
    plt.close()
    return outpath

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", default=None, help="Optional: override CSV_PATH from config")
    ap.add_argument("--output", default=None, help="Optional: output-file")
    ap.add_argument("--title", default=None, help="Optional: title")
    ap.add_argument("--x", default=None, help="Optional: x")
    ap.add_argument("--y", default=None, help="Optional: y")
    ap.add_argument("--group", default=None, help="Optional: group")
    ap.add_argument("--xsize", default=None, help="Optional: Diagramm width in inch")
    ap.add_argument("--cmap", default=None, help="Optional: Colormap")
    ap.add_argument("--ms", default=None, help="Optional: Markersize")

    args, _ = ap.parse_known_args() 

    csv_path = Path(args.csv or CSV_PATH)
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = read_csv_safely(csv_path)
    df = ensure_numeric(df)

    Plot_Err=0
    out = plot_one(df, CONFIG, args.output, args.title, args.x, args.y, args.group, args.xsize, args.cmap, args.ms)
    if out:
        print(f"Saved plot to {out}")
    else:
        print(f"Skipped.", file=sys.stderr)
        Plot_Err=1

    sys.exit(Plot_Err)

if __name__ == "__main__":
    main()
