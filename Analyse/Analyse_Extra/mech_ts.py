#!/usr/bin/env python3
"""
mech_ts.py  (mechanism time series)

What it computes per run (from faces_*.fc + cell_*.dat):
  1) T1-like rearrangement proxy from topology changes between consecutive faces files
     - We reconstruct cell-cell neighbors from shared edges in faces_*.fc
     - Then count neighbor changes between frames (gained + lost)
     - A single ideal T1 changes 2 old + 2 new neighbor relations -> 4 changes
       so we report t1_estimate = neighbor_changes / 4 (as a heuristic)

  2) Boundary vs Bulk polarization from cell_*.dat
     P_edge(t) = |<n_hat>_boundary|, P_bulk(t) = |<n_hat>_bulk|
     (boundary taken from the "boundary" column in cell_*.dat if present;
      otherwise inferred from faces boundary edges)

  3) Optional overlay with O(t)
     If a matching time_series CSV is found (folder named "time_series" somewhere above),
     it will be loaded and interpolated onto the same time axis.

How to use
----------
Option A (single run):
  - Put this script inside a RUN folder that contains faces_*.fc and cell_*.dat
  - Run:  python mech_ts.py
  - It will write outputs into ./mechanism_out/ (next to the script)

Option B (batch):
  - Put this script above your samos_runs tree (e.g. project root)
  - Run:  python mech_ts.py
  - It will find all run folders under any "samos_runs" directory that contain faces_*.fc,
    and process each run, writing outputs under ./mechanism_out/<relative_path>/

Outputs per run:
  - mech_timeseries.csv
  - mech_overlay.png   (O vs T1 proxy + P_edge vs P_bulk)

Notes
-----
- Requires: numpy, pandas, matplotlib
- ffmpeg not needed (no video), only plots + CSV.
"""

import re
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# CONFIG (edit if needed)
# =========================
SEARCH_ROOT = "."
SAMOS_DIRNAME = "samos_runs"

FACES_GLOB = "faces_*.fc"
CELL_GLOB  = "cell_*.dat"

OUT_BASEDIR_NAME = "mechanism_out"
OUT_CSV_NAME = "mech_timeseries.csv"
OUT_PLOT_NAME = "mech_overlay.png"

# Frame controls (important if you have many snapshots)
FRAME_STRIDE = 1           # 1=use every frame, 2=every 2nd faces/cell frame, ...
MAX_FRAMES: Optional[int] = None  # e.g. 800 to cap

# Boundary/bulk polarization uses cell_*.dat boundary flag by default
USE_CELL_BOUNDARY_FLAG = True

# Optional O(t) overlay (from your existing time_series directory)
AUTO_FIND_TIME_SERIES = True
TIME_SERIES_DIRNAME = "time_series"  # script searches upward for this folder
# Your time_series files are named like:
# cc_1024;rand_1;tau_0.17;...;permult_2.8;line_0.1.csv

# Switch detection thresholds (for marking switch time on plots, optional)
O_HIGH = 0.80
HOLD_POINTS = 10            # consecutive samples above O_HIGH after interpolation

# Plot style
FIG_DPI = 220
VERBOSE = True
# =========================


def log(msg: str) -> None:
    if VERBOSE:
        print(msg, flush=True)


def extract_step_from_name(name: str) -> int:
    """
    Extract integer step from faces_0000064130.fc or cell_0000064130.dat
    """
    m = re.search(r"_(\d+)\.(fc|dat)$", name)
    if not m:
        # fallback: last number group
        m2 = re.search(r"(\d+)", name)
        if not m2:
            return -1
        return int(m2.group(1))
    return int(m.group(1))


def parse_faces_neighbors(path: Path) -> Tuple[Set[Tuple[int, int]], Set[int]]:
    """
    Read faces file and reconstruct:
      - neighbor_pairs: set of (cellA, cellB) for internal edges
      - boundary_faces: set of face ids that have at least one boundary edge
    The file mostly contains lines:
      row face v1 v2
    and may contain one extra long line describing the outer boundary face. We ignore non-4-int lines.
    """
    edge_to_faces: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
    # Keep track which faces appear at all
    faces_seen: Set[int] = set()

    for line in path.read_text(errors="ignore").splitlines():
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        try:
            _, face, v1, v2 = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))
        except Exception:
            continue
        faces_seen.add(face)
        a, b = (v1, v2) if v1 < v2 else (v2, v1)
        edge_to_faces[(a, b)].add(face)

    neighbor_pairs: Set[Tuple[int, int]] = set()
    boundary_faces: Set[int] = set()

    for _, fs in edge_to_faces.items():
        if len(fs) == 2:
            i, j = sorted(fs)
            if i != j:
                neighbor_pairs.add((i, j))
        elif len(fs) == 1:
            (i,) = tuple(fs)
            boundary_faces.add(i)

    return neighbor_pairs, boundary_faces


def read_cell_frame(path: Path) -> pd.DataFrame:
    """
    Read one cell_*.dat snapshot into DataFrame using the 'keys:' header line.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip()
    if not header.startswith("keys:"):
        raise ValueError(f"{path}: first line does not start with 'keys:'")
    keys = header.replace("keys:", "").split()
    df = pd.read_csv(path, sep=r"\s+", engine="python", names=keys, skiprows=1)

    for c in ("id", "nx", "ny"):
        if c not in df.columns:
            raise KeyError(f"{path}: missing '{c}' in columns: {list(df.columns)}")

    if "boundary" not in df.columns:
        df["boundary"] = 0

    # Numeric conversion
    for c in ("id", "nx", "ny", "boundary"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["id", "nx", "ny", "boundary"]).copy()
    df["id"] = df["id"].astype(int)
    df["boundary"] = df["boundary"].astype(int)

    return df


def polarization_magnitude(df: pd.DataFrame, ids: Optional[Set[int]] = None) -> float:
    """
    Compute |<n_hat>| over selected ids (if ids is None, use all rows).
    """
    if ids is not None:
        sub = df[df["id"].isin(ids)]
    else:
        sub = df
    if sub.empty:
        return float("nan")
    nx = sub["nx"].to_numpy(dtype=float)
    ny = sub["ny"].to_numpy(dtype=float)
    norm = np.sqrt(nx * nx + ny * ny)
    mask = norm > 0
    if mask.sum() == 0:
        return float("nan")
    nx = nx[mask] / norm[mask]
    ny = ny[mask] / norm[mask]
    mx = float(np.mean(nx))
    my = float(np.mean(ny))
    return float(math.sqrt(mx * mx + my * my))


def find_time_series_file(run_dir: Path) -> Optional[Path]:
    """
    Try to locate a matching time_series CSV by walking upward to find TIME_SERIES_DIRNAME,
    then matching tokens from the run_dir path (cc_, rand_, tau_, permult_).
    """
    # Collect tokens from path parts
    parts = [p.name for p in run_dir.resolve().parts]
    tokens = {}
    for p in parts:
        if p.startswith("cc_"):
            tokens["cc"] = p
        elif p.startswith("rand_"):
            tokens["rand"] = p
        elif p.startswith("tau_"):
            tokens["tau"] = p
        elif p.startswith("permult_"):
            tokens["permult"] = p

    if len(tokens) < 3:
        return None

    # Find nearest ancestor containing TIME_SERIES_DIRNAME
    cur = run_dir.resolve()
    ts_dir = None
    for anc in [cur] + list(cur.parents):
        cand = anc / TIME_SERIES_DIRNAME
        if cand.is_dir():
            ts_dir = cand
            break
    if ts_dir is None:
        return None

    # Match files by requiring that filename contains the tokens
    candidates = list(ts_dir.glob("*.csv"))
    best = None
    best_score = -1
    for fp in candidates:
        name = fp.name
        score = 0
        for k, tok in tokens.items():
            if tok in name:
                score += 1
        if score > best_score:
            best_score = score
            best = fp
    if best is None or best_score < 3:
        return None
    return best


def read_O_timeseries(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read O(t) from 2-column CSV; tries comma-separated first.
    """
    df = pd.read_csv(path, header=None)
    if df.shape[1] < 2:
        raise ValueError(f"{path}: expected at least 2 columns")
    t = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy()
    O = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy()
    mask = np.isfinite(t) & np.isfinite(O)
    return t[mask], O[mask]


def detect_switch_time(x: np.ndarray, y: np.ndarray, thresh: float, hold_points: int) -> Optional[float]:
    """
    Detect first time where y stays >= thresh for hold_points consecutive samples.
    Returns x at the start of that window.
    """
    if len(y) < hold_points:
        return None
    above = (y >= thresh).astype(np.int32)
    window = np.ones(hold_points, dtype=np.int32)
    conv = np.convolve(above, window, mode="valid")
    idx = np.where(conv == hold_points)[0]
    if len(idx) == 0:
        return None
    return float(x[int(idx[0])])


def process_run(run_dir: Path, out_dir: Path) -> None:
    """
    Compute timeseries + plots for one run directory.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    faces_files = sorted(run_dir.glob(FACES_GLOB), key=lambda p: extract_step_from_name(p.name))
    cell_files  = sorted(run_dir.glob(CELL_GLOB),  key=lambda p: extract_step_from_name(p.name))

    if not faces_files:
        raise ValueError("no faces_*.fc files")
    if not cell_files:
        raise ValueError("no cell_*.dat files")

    # Apply stride + max
    faces_files = faces_files[::max(1, FRAME_STRIDE)]
    cell_files  = cell_files[::max(1, FRAME_STRIDE)]
    if MAX_FRAMES is not None:
        faces_files = faces_files[:MAX_FRAMES]
        cell_files = cell_files[:MAX_FRAMES]

    # Align by step: keep intersection of steps between faces and cell files
    faces_map = {extract_step_from_name(p.name): p for p in faces_files}
    cell_map  = {extract_step_from_name(p.name): p for p in cell_files}
    steps = sorted(set(faces_map.keys()) & set(cell_map.keys()))
    if len(steps) < 3:
        raise ValueError("not enough matching faces/cell frames by step")

    # Precompute neighbor sets + boundary faces per step
    neighbor_sets: Dict[int, Set[Tuple[int, int]]] = {}
    boundary_faces_by_step: Dict[int, Set[int]] = {}

    for s in steps:
        neigh, bfaces = parse_faces_neighbors(faces_map[s])
        neighbor_sets[s] = neigh
        boundary_faces_by_step[s] = bfaces

    # Compute T1 proxy between consecutive steps
    rows = []
    prev_s = steps[0]
    prev_neigh = neighbor_sets[prev_s]

    for s in steps:
        # read cell frame
        cdf = read_cell_frame(cell_map[s])

        # boundary set
        if USE_CELL_BOUNDARY_FLAG and "boundary" in cdf.columns:
            edge_ids = set(cdf.loc[cdf["boundary"] != 0, "id"].astype(int).tolist())
        else:
            edge_ids = boundary_faces_by_step.get(s, set())

        all_ids = set(cdf["id"].astype(int).tolist())
        bulk_ids = all_ids - edge_ids

        P_edge = polarization_magnitude(cdf, edge_ids)
        P_bulk = polarization_magnitude(cdf, bulk_ids)

        if s == prev_s:
            # first row has no T1 diff
            rows.append(dict(step=s, dt=np.nan, neighbor_changes=np.nan, t1_est=np.nan,
                             n_neighbors=len(prev_neigh), P_edge=P_edge, P_bulk=P_bulk))
            continue

        neigh = neighbor_sets[s]
        gained = neigh - prev_neigh
        lost = prev_neigh - neigh
        changes = len(gained) + len(lost)
        dt = s - prev_s if (s - prev_s) != 0 else np.nan
        t1_est = changes / 4.0  # heuristic: one T1 ~ 4 neighbor relation changes

        rows.append(dict(step=s, dt=dt, neighbor_changes=changes, t1_est=t1_est,
                         n_neighbors=len(neigh), P_edge=P_edge, P_bulk=P_bulk))

        prev_s = s
        prev_neigh = neigh

    mech = pd.DataFrame(rows)

    # Try to load O(t) from time_series and interpolate onto 'step'
    O_path = None
    if AUTO_FIND_TIME_SERIES:
        O_path = find_time_series_file(run_dir)

    if O_path is not None and O_path.exists():
        try:
            tO, O = read_O_timeseries(O_path)
            # Interpolate O onto steps; assume time axis tO is also in "steps"
            # If not, this still gives a rough alignment.
            O_interp = np.interp(mech["step"].to_numpy(), tO, O, left=np.nan, right=np.nan)
            mech["O_interp"] = O_interp
            mech.attrs["O_source"] = str(O_path)
        except Exception as e:
            log(f"[WARN] Could not load O(t) from {O_path}: {e}")
            mech["O_interp"] = np.nan
    else:
        mech["O_interp"] = np.nan

    # Save CSV
    out_csv = out_dir / OUT_CSV_NAME
    mech.to_csv(out_csv, index=False)

    # Plot overlay
    fig = plt.figure(figsize=(10.5, 7.2))
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212, sharex=ax1)

    x = mech["step"].to_numpy()
    t1 = mech["t1_est"].to_numpy()
    ch = mech["neighbor_changes"].to_numpy()
    P_edge = mech["P_edge"].to_numpy()
    P_bulk = mech["P_bulk"].to_numpy()
    Oi = mech["O_interp"].to_numpy()

    # Top: O and T1 proxy
    ax1.set_title(run_dir.as_posix())
    ax1.grid(True, alpha=0.3)

    # Left axis: O if available
    if np.any(np.isfinite(Oi)):
        ax1.plot(x, Oi, marker=None, linewidth=1.8, label="O(t) (interpolated)")
        ax1.set_ylabel("O(t)")
    else:
        ax1.plot(x, P_bulk, linewidth=1.8, label="P_bulk(t) (fallback)")
        ax1.set_ylabel("|<n_hat>| (bulk)")

    # Right axis: T1 proxy
    ax1b = ax1.twinx()
    ax1b.plot(x, t1, linewidth=1.5, alpha=0.85, label="T1 proxy (changes/4)")
    ax1b.set_ylabel("T1 proxy")

    # Switch marker (based on O if available, else P_bulk)
    y_for_switch = Oi if np.any(np.isfinite(Oi)) else P_bulk
    sw = detect_switch_time(x, np.nan_to_num(y_for_switch, nan=-1.0), O_HIGH, HOLD_POINTS)
    if sw is not None:
        ax1.axvline(sw, linestyle="--", linewidth=1.2)
        ax2.axvline(sw, linestyle="--", linewidth=1.2)

    # Legend (combine)
    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax1b.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, frameon=False, loc="upper right")

    # Bottom: edge vs bulk polarization
    ax2.grid(True, alpha=0.3)
    ax2.plot(x, P_edge, linewidth=1.8, label="P_edge(t)")
    ax2.plot(x, P_bulk, linewidth=1.8, label="P_bulk(t)")
    ax2.set_xlabel("simulation step")
    ax2.set_ylabel("|<n_hat>|")
    ax2.legend(frameon=False, loc="upper right")

    fig.tight_layout()
    out_plot = out_dir / OUT_PLOT_NAME
    fig.savefig(out_plot, dpi=FIG_DPI)
    plt.close(fig)

    log(f"[OK] {run_dir} -> {out_dir}")
    log(f"     wrote {out_csv.name}, {out_plot.name}")


def find_run_dirs(root: Path) -> List[Path]:
    """
    Find candidate run directories:
    - If current dir itself contains faces+cell, include it.
    - Otherwise, search under any samos_runs for folders containing faces_*.fc.
    """
    run_dirs = set()

    # current dir as run?
    if any(root.glob(FACES_GLOB)) and any(root.glob(CELL_GLOB)):
        run_dirs.add(root)

    # search under samos_runs
    for sd in root.rglob(SAMOS_DIRNAME):
        if not sd.is_dir():
            continue
        for f in sd.rglob(FACES_GLOB):
            run_dirs.add(f.parent)

    return sorted(run_dirs)


def main():
    root = Path(SEARCH_ROOT).resolve()
    script_dir = Path(__file__).resolve().parent
    out_root = script_dir / OUT_BASEDIR_NAME
    out_root.mkdir(parents=True, exist_ok=True)

    run_dirs = find_run_dirs(root)
    if not run_dirs:
        raise SystemExit(f"No run folders found (need {FACES_GLOB} + {CELL_GLOB}) under {root}")

    log(f"[INFO] Found {len(run_dirs)} run folder(s). Writing outputs under: {out_root}")

    n_ok = 0
    n_fail = 0
    for rd in run_dirs:
        try:
            rel = rd.resolve().relative_to(root)
            out_dir = out_root / rel
            process_run(rd, out_dir)
            n_ok += 1
        except Exception as e:
            log(f"[ERROR] {rd}: {e}")
            n_fail += 1

    log(f"[DONE] processed={n_ok}, failed={n_fail}")


if __name__ == "__main__":
    main()
