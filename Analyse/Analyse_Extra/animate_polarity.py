#!/usr/bin/env python3
"""
animate_polarity.py

Put this file into the SAME folder as:
  cell_0000000000.dat, cell_0000000001.dat, ...

It will create an animation where each cell is plotted at (x,y) and colored by
polarity angle theta = atan2(ny, nx) using a CYCLIC colormap.

Output:
  - polarity_animation.mp4  (if ffmpeg is installed)
  - otherwise polarity_animation.gif
"""

import re
import glob
import os
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter

# =========================
# CONFIG (edit if needed)
# =========================
FILE_GLOB = "cell_*.dat"
OUT_MP4 = "polarity_animation.mp4"
OUT_GIF = "polarity_animation.gif"
FPS = 20
MAX_FRAMES = None            # e.g. 500 to limit, or None for all frames

COLORMAP = "twilight"        # cyclic colormap: "twilight" or "hsv"
POINT_SIZE = 14

SHOW_BOUNDARY = True
BOUNDARY_EDGEWIDTH = 0.6
BOUNDARY_EDGECOLOR = "k"

USE_QUIVER = False           # True = draw arrows; False = only color
QUIVER_SUBSAMPLE = 1         # 1 = all cells, 2 = every 2nd, ...
QUIVER_SCALE = 25            # larger => shorter arrows
# =========================


def extract_index(fname: str) -> int:
    m = re.search(r"(\\d+)\\.dat$", fname)
    return int(m.group(1)) if m else -1


def read_frame(path: str) -> pd.DataFrame:
    # First line must be: "keys: id type x y ... nx ny ... boundary ..."
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip()

    if not header.startswith("keys:"):
        raise ValueError(f"{path}: first line does not start with 'keys:'")

    keys = header.replace("keys:", "").split()
    df = pd.read_csv(path, delim_whitespace=True, names=keys, skiprows=1)

    for c in ("x", "y", "nx", "ny"):
        if c not in df.columns:
            raise KeyError(f"{path}: missing required column '{c}'. Found: {list(df.columns)}")

    if "boundary" not in df.columns:
        df["boundary"] = 0

    return df


def main():
    files = sorted(glob.glob(FILE_GLOB), key=extract_index)
    if not files:
        raise SystemExit(f"No files found matching {FILE_GLOB} in {os.getcwd()}")

    if MAX_FRAMES is not None:
        files = files[:MAX_FRAMES]

    # Read first frame for init + axis limits
    df0 = read_frame(files[0])
    x0 = df0["x"].to_numpy()
    y0 = df0["y"].to_numpy()
    theta0 = np.arctan2(df0["ny"].to_numpy(), df0["nx"].to_numpy())
    boundary0 = df0["boundary"].to_numpy().astype(int)

    # Axis limits from first frame (with margin)
    margin = 0.05
    xmin, xmax = x0.min(), x0.max()
    ymin, ymax = y0.min(), y0.max()
    dx = max(1e-9, xmax - xmin)
    dy = max(1e-9, ymax - ymin)
    xmin -= margin * dx
    xmax += margin * dx
    ymin -= margin * dy
    ymax += margin * dy

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    # Cyclic angle coloring
    norm = mpl.colors.Normalize(vmin=-math.pi, vmax=math.pi)
    cmap = mpl.colormaps[COLORMAP]

    sc = ax.scatter(x0, y0, c=theta0, cmap=cmap, norm=norm, s=POINT_SIZE)

    # Boundary overlay
    if SHOW_BOUNDARY:
        mask_b = boundary0 != 0
        sc_b = ax.scatter(
            x0[mask_b], y0[mask_b],
            c=theta0[mask_b], cmap=cmap, norm=norm,
            s=POINT_SIZE * 1.3,
            edgecolors=BOUNDARY_EDGECOLOR, linewidths=BOUNDARY_EDGEWIDTH
        )
    else:
        sc_b = None

    # Optional arrows
    if USE_QUIVER:
        idx = np.arange(len(x0))[::max(1, QUIVER_SUBSAMPLE)]
        q = ax.quiver(
            x0[idx], y0[idx],
            df0["nx"].to_numpy()[idx], df0["ny"].to_numpy()[idx],
            angles="xy", scale_units="xy", scale=QUIVER_SCALE,
            width=0.003
        )
    else:
        q = None

    cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("polarity angle theta = atan2(ny, nx)")
    cbar.set_ticks([-math.pi, -math.pi/2, 0, math.pi/2, math.pi])
    cbar.set_ticklabels(["-pi", "-pi/2", "0", "pi/2", "pi"])

    title = ax.set_title(f"Frame 0 / {len(files)-1}")

    def update(frame_idx: int):
        path = files[frame_idx]
        df = read_frame(path)

        x = df["x"].to_numpy()
        y = df["y"].to_numpy()
        theta = np.arctan2(df["ny"].to_numpy(), df["nx"].to_numpy())
        boundary = df["boundary"].to_numpy().astype(int)

        sc.set_offsets(np.column_stack([x, y]))
        sc.set_array(theta)

        if sc_b is not None:
            mask = boundary != 0
            sc_b.set_offsets(np.column_stack([x[mask], y[mask]]))
            sc_b.set_array(theta[mask])

        if q is not None:
            idx = np.arange(len(x))[::max(1, QUIVER_SUBSAMPLE)]
            q.set_offsets(np.column_stack([x[idx], y[idx]]))
            q.set_UVC(df["nx"].to_numpy()[idx], df["ny"].to_numpy()[idx])

        title.set_text(f"Frame {frame_idx} / {len(files)-1}   ({Path(path).name})")
        return ()

    anim = FuncAnimation(fig, update, frames=len(files), interval=1000 / FPS, blit=False)

    # Save MP4 if ffmpeg exists, else GIF
    if shutil.which("ffmpeg") is not None:
        writer = FFMpegWriter(fps=FPS, codec="libx264", bitrate=2500)
        anim.save(OUT_MP4, writer=writer)
        print(f"[OK] Wrote {OUT_MP4}")
    else:
        writer = PillowWriter(fps=FPS)
        anim.save(OUT_GIF, writer=writer)
        print(f"[OK] ffmpeg not found; wrote {OUT_GIF}")

    plt.close(fig)


if __name__ == "__main__":
    main()
