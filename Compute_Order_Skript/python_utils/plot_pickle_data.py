#!/usr/bin/env python3

import sys,os,glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
#from pathlib import Path
import argparse

# -------------------------- CONFIG (edit here) --------------------------
CONFIG=dict(
        group="permult",      # Group by
        style_MSD="logxy",    # line , logx , logxy
        style_SelfInt="logx",
        dpi=200,              # Diagramm DPI
        x_size=11,            # Diagramm Width (inch)
        y_size=7,             # Diagramm Hight (inch)
        title="",             # Title-Prefix
        cmap="none"           # Colormap
       )

VALID_COLS = ["cc","rand","tau","v","k","nu","gamma","permult","line","time","MSD","SelfInt","DataCount"]
LEN_FIX_COLS = 9
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

def plot_one(df, output, title, xcol, ycol, group_col, style_MSD, style_SelfInt, xsize, ysize, dpi, cmap):

    if xsize < ysize:
        xsize=ysize

    if ysize < xsize/3:
        ysize=int(xsize/3)

    if xcol not in VALID_COLS or ycol not in VALID_COLS:
        print(f"[SKIP] Invalid x/y in config: x={xcol} y={ycol}", file=sys.stderr)
        return None

    if group_col == "none":
        group_col=None

    if cmap == "none":
        cmap=None


    if group_col is not None and group_col not in VALID_COLS:
        print(f"[SKIP] Invalid group column: {group_col}", file=sys.stderr)
        return None

    gdf = df.dropna(subset=[xcol, ycol])

    if group_col is None:
        groups = [(None, gdf)]
    else:
        groups = list(gdf.groupby(group_col, dropna=True))

    if cmap is not None:
        plt.rcParams['axes.prop_cycle']=plt.cycler("color",getattr(plt.cm,cmap)(np.linspace(0,1,len(groups))))

    plt.figure(figsize=(xsize,ysize))

    for label, sub in groups:
        sub = sub.sort_values(by=xcol)
        x = sub[xcol].values
        y = sub[ycol].values

        style="line"
        if style_MSD == "logx" and ycol == "MSD":
            style="logx"
        if style_MSD == "logxy" and ycol == "MSD":
            style="logxy"
        if style_SelfInt == "logx" and ycol == "SelfInt":
            style="logx"
        if style_SelfInt == "logxy" and ycol == "SelfInt":
            style="logxy"


        if style == "logx":
            plt.semilogx(x, y, linewidth=1.5, label=f"{group_col}={label}" if group_col is not None else None)
        elif style == "logxy":
            plt.loglog(x, y, linewidth=1.5, label=f"{group_col}={label}" if group_col is not None else None)
        else:
            plt.plot(x, y, linewidth=1.5, label=f"{group_col}={label}" if group_col is not None else None)

    plt.title(title,fontsize=10)
    plt.xlabel(xcol)
    plt.ylabel(ycol)
    if group_col is not None:
        plt.legend(title=group_col, bbox_to_anchor=(1.02,1), loc="upper left", frameon=True)
    plt.grid(True, linestyle="--", alpha=0.3)
    if style == "line":
        plt.locator_params(axis='x', nbins=xsize)
        plt.locator_params(axis='y', nbins=10)
    plt.tight_layout()

    plt.savefig(output, dpi=dpi)
    plt.close()
    return output

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", default="pickle_data.csv", help="Optional: csv-file")
    ap.add_argument("--group", default=None, help="Optional: group")
    ap.add_argument("--xsize", default=None, help="Optional: Diagramm width in inch")
    ap.add_argument("--title", default=None, help="Optional: Title-Prefix")
    ap.add_argument("--style_msd", default=None, help="Optional: Style for MSD (line , logx , logxy)")
    ap.add_argument("--style_selfint", default=None, help="Optional: Style for SelfInt (line , logx , logxy)")
    ap.add_argument("--cmap", default=None, help="Optional: Color-Map")

    args, _ = ap.parse_known_args() 

    group=args.group or CONFIG.get("group")
    title_pre=args.title or CONFIG.get("title","")
    style_msd=args.style_msd or CONFIG.get("style_MSD","line")
    style_selfint=args.style_selfint or CONFIG.get("style_SelfInt","line")
    xsize = int(args.xsize or CONFIG.get("x_size",11))
    ysize = int(CONFIG.get("y_size",7))
    dpi = int(CONFIG.get("dpi",200))
    cmap=args.cmap or CONFIG.get("cmap","none")

    csv_file=args.csv
    csv_root,csv_ext=os.path.splitext(csv_file)
    files=glob.glob(csv_root+"*"+csv_ext)

    if len(files)<1:
        print(f"No files found {csv_root}*{csv_ext}")
        sys.exit(1)

    Plot_Err=0
    for f in files:

        output=os.path.splitext(f)[0]
        print(f"Input: {os.path.basename(f)}")

        df = read_csv_safely(f)

        title=title_pre
        for i in range(LEN_FIX_COLS):
            if VALID_COLS[i] == group:
                continue
            wert=df[VALID_COLS[i]].values[:1][0]
            if i != 0 or title != "":
                title=title+" , "
            title=title+VALID_COLS[i]+": "+str(wert)

        df = ensure_numeric(df)

        for y_wert in ["MSD","SelfInt"]:
            out = plot_one(df, output+";"+y_wert+".png", title, "time", y_wert, group, style_msd, style_selfint, xsize, ysize, dpi, cmap)
            if out:
                print(f"Saved: {out}")
            else:
                print(f"Error: {output};{y_wert}.png", file=sys.stderr)
                Plot_Err=1

    sys.exit(Plot_Err)

if __name__ == "__main__":
    main()
