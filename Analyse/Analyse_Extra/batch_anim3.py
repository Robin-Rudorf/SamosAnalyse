#!/usr/bin/env python3
"""
batch_anim3.py

Same as batch_anim_outdir.py, but writes MP4s in a widely compatible format
(H.264 + yuv420p + faststart) to avoid "encoding settings" playback errors.

Output directory (next to this script):
  ./animations/<relative_path_to_run>/polarity.mp4  (or .gif if ffmpeg missing)
"""

import re
import math
import shutil
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter

# =========================
# CONFIG (edit if needed)
# =========================
SEARCH_ROOT = "."
SAMOS_DIRNAME = "samos_runs"
FRAME_GLOB = "cell_*.dat"

OUT_BASEDIR_NAME = "animations"
OUT_BASENAME = "polarity"

FPS = 20
FRAME_STRIDE = 1
MAX_FRAMES: Optional[int] = None

COLORMAP = "twilight"
POINT_SIZE = 14

SHOW_BOUNDARY = True
BOUNDARY_EDGEWIDTH = 0.6
BOUNDARY_EDGECOLOR = "k"

USE_QUIVER = False
QUIVER_SUBSAMPLE = 1
QUIVER_SCALE = 25

SKIP_IF_EXISTS = True
VERBOSE = True
# =========================


def log(msg: str) -> None:
    if VERBOSE:
        print(msg, flush=True)


def extract_index(fname: str) -> int:
    m = re.search(r"(\d+)\.dat$", fname)
    return int(m.group(1)) if m else -1


def read_frame(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip()
    if not header.startswith("keys:"):
        raise ValueError(f"{path}: first line does not start with 'keys:'")

    keys = header.replace("keys:", "").split()
    # pandas: delim_whitespace deprecated -> use regex whitespace separator
    df = pd.read_csv(path, sep=r"\s+", engine="python", names=keys, skiprows=1)

    for c in ("x", "y", "nx", "ny"):
        if c not in df.columns:
            raise KeyError(f"{path}: missing required column '{c}'. Found: {list(df.columns)}")

    if "boundary" not in df.columns:
        df["boundary"] = 0

    return df


def list_run_dirs(samos_dir: Path) -> List[Path]:
    run_dirs = set()
    for f in samos_dir.rglob(FRAME_GLOB):
        if f.is_file():
            run_dirs.add(f.parent)
    return sorted(run_dirs)


def out_dir_for_run(out_root: Path, run_dir: Path, search_root: Path) -> Path:
    rel = run_dir.resolve().relative_to(search_root.resolve())
    out_dir = out_root / rel
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def make_animation(run_dir: Path, out_dir: Path) -> bool:
    use_mp4 = shutil.which("ffmpeg") is not None
    out_file = out_dir / f"{OUT_BASENAME}.mp4" if use_mp4 else out_dir / f"{OUT_BASENAME}.gif"

    if SKIP_IF_EXISTS and out_file.exists():
        log(f"[SKIP] {run_dir} -> {out_file} (exists)")
        return False

    files = sorted(run_dir.glob(FRAME_GLOB), key=lambda p: extract_index(p.name))
    if not files:
        return False

    files = files[::max(1, FRAME_STRIDE)]
    if MAX_FRAMES is not None:
        files = files[:MAX_FRAMES]

    df0 = read_frame(files[0])
    x0 = df0["x"].to_numpy()
    y0 = df0["y"].to_numpy()
    theta0 = np.arctan2(df0["ny"].to_numpy(), df0["nx"].to_numpy())
    boundary0 = df0["boundary"].to_numpy().astype(int)

    margin = 0.05
    xmin, xmax = float(x0.min()), float(x0.max())
    ymin, ymax = float(y0.min()), float(y0.max())
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

    norm = mpl.colors.Normalize(vmin=-math.pi, vmax=math.pi)
    cmap = mpl.colormaps[COLORMAP]

    sc = ax.scatter(x0, y0, c=theta0, cmap=cmap, norm=norm, s=POINT_SIZE)

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

    title = ax.set_title(f"{run_dir.name}  frame 0/{len(files)-1}")

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

        title.set_text(f"{run_dir.name}  frame {frame_idx}/{len(files)-1}  ({path.name})")
        return ()

    anim = FuncAnimation(fig, update, frames=len(files), interval=1000 / FPS, blit=False)

    try:
        if use_mp4:
            # Highly compatible H.264 encoding:
            # - yuv420p pixel format (needed for many players)
            # - faststart for web/quicktime
            # - baseline-ish profile for older players
            writer = FFMpegWriter(
                fps=FPS,
                codec="libx264",
                bitrate=2500,
                extra_args=[
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-profile:v", "baseline",
                    "-level", "3.0"
                ],
            )
            anim.save(out_file.as_posix(), writer=writer)
        else:
            writer = PillowWriter(fps=FPS)
            anim.save(out_file.as_posix(), writer=writer)
    finally:
        plt.close(fig)

    log(f"[OK] {run_dir} -> {out_file}")
    return True


def main():
    search_root = Path(SEARCH_ROOT).resolve()
    script_dir = Path(__file__).resolve().parent
    out_root = script_dir / OUT_BASEDIR_NAME
    out_root.mkdir(parents=True, exist_ok=True)

    log(f"[INFO] Searching under: {search_root}")
    log(f"[INFO] Writing animations under: {out_root}")

    samos_dirs = [p for p in search_root.rglob(SAMOS_DIRNAME) if p.is_dir()]
    if not samos_dirs:
        raise SystemExit(f"No '{SAMOS_DIRNAME}' directory found under {search_root}")

    total_runs = 0
    total_written = 0

    for sd in samos_dirs:
        run_dirs = list_run_dirs(sd)
        if not run_dirs:
            continue
        log(f"[INFO] Found {len(run_dirs)} run folder(s) under: {sd}")
        for rd in run_dirs:
            total_runs += 1
            try:
                out_dir = out_dir_for_run(out_root, rd, search_root)
                wrote = make_animation(rd, out_dir)
                total_written += 1 if wrote else 0
            except Exception as e:
                log(f"[ERROR] {rd}: {e}")

    log(f"[DONE] runs found: {total_runs}, animations written: {total_written}")


if __name__ == "__main__":
    main()
