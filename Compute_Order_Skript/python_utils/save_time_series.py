#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
save_time_series.py

Erzeugt für jeden Run unterhalb eines Basisverzeichnisses (Default: ./open_boundaries)
die Zeitserie des Ordnungsparameters O(t), so wie er in compute_order.py definiert ist:

    O_frame = sqrt(P^2 + R^2 + Delta_net^2)

Die Frame-Dateien werden genau wie in compute_order.py gesucht und gelesen
(cell_*.dat oder cell_full_*.dat), inkl. 'keys:'-Header.

Für jeden Run wird gespeichert (Standard):
 outfile.csv   (Spalten: t, O)

"""

import sys, os, re
import argparse
import glob
import pandas as pd
import numpy as np






# ---------- Hilfsfunktionen ----------

def normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + eps)

def find_frame_files(run_dir: str):
# Versuche beide üblichen Muster
    files = glob.glob(os.path.join(run_dir, "cell_*.dat"))
    files_full = glob.glob(os.path.join(run_dir, "cell_full_*.dat"))
    files = files if len(files) >= len(files_full) else files_full
    files.sort(key=extract_frame_index)
    return files


def read_dat_with_keys(path: str) -> pd.DataFrame:
    """
    Liest SAMoS/AVM-`.dat`; optional erste Zeile:
      'keys: id type x y z vx vy vz ...'
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        first = f.readline()
    if first.strip().lower().startswith("keys:"):
        cols = [c for c in first.strip()[5:].split() if c]
        return pd.read_csv(path, sep='\\s+', comment="#", header=None,
                           names=cols, skiprows=1, engine="python")
    return pd.read_csv(path, sep='\\s+', comment="#", engine="python")

def compute_O_frame(X: np.ndarray, V: np.ndarray) -> float:
    """
    O_frame = sqrt(P^2 + R^2 + Delta_net^2) für einen Frame.
      - P = || mean(vhat) ||
      - R = | mean( (rhat x vhat)_z ) |
      - Delta_net = | mean( rhat · vhat ) |
    """
    vhat = normalize(V)                                   # (N,2)
    P = float(np.linalg.norm(vhat.mean(axis=0)))          # || mean vhat ||

    com = X.mean(axis=0, keepdims=True)
    rhat = normalize(X - com)

    cross_z = rhat[:,0]*vhat[:,1] - rhat[:,1]*vhat[:,0]   # (N,)
    R = float(np.abs(cross_z.mean()))                     # |mean cross_z|

    dot = np.sum(rhat * vhat, axis=1)                     # (N,)
    Delta_net = float(np.abs(np.mean(dot)))               # |mean dot|

    return float(np.sqrt(P*P + R*R + Delta_net*Delta_net))

def extract_frame_index(path: str) -> int:
    m = list(re.finditer(r'(\d+)', os.path.basename(path)))
    return int(m[-1].group(1)) if m else 0



def compute_time_series_for_run(run_dir):
    """
    Berechne O(t) für einen einzelnen Run (run_dir).
    Gibt (times, O_values) zurück.
    """
    files = find_frame_files(run_dir)
    if len(files)<2:
        sys.stderr.write(f"[ERROR] Keine Frame-Dateien in {run_dir}\n")
        sys.exit(1)
        return [], [], 1

    times = []
    O_values = []
    Error=0
    for fp in files:
        try:
            df = read_dat_with_keys(fp)
        except Exception as e:
            sys.stderr.write(f"[WARN] Kann {fp} nicht lesen: {e}\n")
            Error=1
            continue

        cols = {c.lower(): c for c in df.columns}
        # benötigte Spalten
        required = ["x", "y", "vx", "vy"]
        if any(r not in cols for r in required):
            continue

        X = df[[cols["x"], cols["y"]]].to_numpy(float)
        V = df[[cols["vx"], cols["vy"]]].to_numpy(float)
        if X.shape[0] < 2:
            continue

        O_frame = compute_O_frame(X, V)
        t = extract_frame_index(fp)

        times.append(t)
        O_values.append(O_frame)

    return times, O_values, Error


def save_time_series(out_file, times, O_values):
    """
    Speichere CSV für einen Run
    """
    if len(times)<2:
        sys.stderr.write(f"[ERROR] Keine Daten in {run_dir}\n")
        sys.exit(1)
        return

    # sortieren nach Zeit
    times = np.array(times)
    O_values = np.array(O_values)
    idx = np.argsort(times)
    times = times[idx]
    O_values = O_values[idx]

    # CSV
    with open(out_file, "w") as f:
        for t, o in zip(times, O_values):
            f.write(f"{t},{o}\n")


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Erstelle O(t)-Zeitserie "
            "unter Verwendung derselben O-Definition wie compute_order.py."
        )
    )
    parser.add_argument(
        "--rundir",
        type=str,
        default=".",
        help="Verzeichnis mit den Samos-Dateien (Default: .)",
    )
    parser.add_argument(
        "--outfile",
        type=str,
        default="time_series.csv",
        help="CSV-Datei (Default: time_series.csv)",
    )



    args = parser.parse_args()

    run_dir = os.path.abspath(args.rundir)
    out_file = args.outfile
    if not os.path.isdir(run_dir):
        sys.stderr.write(f"[ERROR] Verzeichnis existiert nicht: {run_dir}\n")
        sys.exit(1)
        return


    print(f"save_time_series "+os.path.basename(out_file))

    times, O_vals, Error = compute_time_series_for_run(run_dir)
    save_time_series(out_file, times, O_vals)

    if Error == 1:
        sys.exit(1)

if __name__ == "__main__":
    main()
