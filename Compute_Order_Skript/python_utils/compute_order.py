#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einzel-Run-Analyzer für O:
O = sqrt(P^2 + R^2 + Delta_net^2)

Aufruf:
    python order_single.py <RUN_DIR> <DISCARD_FIRST_N> [--keep-lab]
    - RUN_DIR: Ordner mit den Frame-Dateien des Runs
    - DISCARD_FIRST_N: wie viele Frames am Anfang verwerfen (int >= 0)
    - --keep-lab: (optional) keine COM-Translation von vx,vy abziehen
                  (Default: Translation wird entfernt -> drift-robust)

Das Skript findet automatisch Dateien nach "cell_*.dat" ODER "cell_full_*.dat".
Erwartete Spalten pro Frame: x, y, vx, vy (optional Kopfzeile "keys: ...").


apt-get install python3-numpi
apt-get install python3-pandas
"""

import sys, os, re, glob
import numpy as np
import pandas as pd

import warnings





# ---------- Hilfsfunktionen ----------

def normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + eps)

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

def read_dat_with_keys(path: str) -> pd.DataFrame:
    """
    Liest SAMoS/AVM-`.dat`; optional erste Zeile:
      'keys: id type x y z vx vy vz ...'
    """
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        first = f.readline()
    if first.strip().lower().startswith("keys:"):
        cols = [c for c in first.strip()[5:].split() if c]
        return pd.read_csv(path, delim_whitespace=True, comment="#", header=None,
                           names=cols, skiprows=1, engine="python")
    return pd.read_csv(path, delim_whitespace=True, comment="#", engine="python")

def extract_frame_index(path: str) -> int:
    m = list(re.finditer(r'(\d+)', os.path.basename(path)))
    return int(m[-1].group(1)) if m else 0

def find_frame_files(run_dir: str):
    # Versuche beide üblichen Muster
    files = glob.glob(os.path.join(run_dir, "cell_*.dat"))
    files_full = glob.glob(os.path.join(run_dir, "cell_full_*.dat"))
    files = files if len(files) >= len(files_full) else files_full
    files.sort(key=extract_frame_index)
    return files

# ---------- Hauptlogik ----------

def main():
    warnings.filterwarnings("ignore")
   
    if len(sys.argv) != 6:
        sys.stderr.write("Usage: python order_single.py <RUN_DIR> <DISCARD_FIRST_N> 0\n")
        sys.exit(1)

    run_dir = sys.argv[1]
    dc_first=sys.argv[2]
    modus=sys.argv[3]
    csvtxt=sys.argv[4]
    csvfile=sys.argv[5]

    print("start compute_order " +csvtxt)

    try:
        discard_first_n = int(dc_first)
        assert discard_first_n >= 0
    except Exception:
        sys.stderr.write("ERROR: <DISCARD_FIRST_N> muss eine ganze Zahl >= 0 sein.\n")
        sys.exit(1)

    remove_translation = True
    if  modus == "0":
        remove_translation = False
    

    files = find_frame_files(run_dir)
    if not files:
        sys.stderr.write("ERROR: Keine Frame-Dateien in " + run_dir + "\n")
        sys.exit(2)

    # Transienten verwerfen
    if discard_first_n > 0:
        files = files[discard_first_n:]
        if not files:
            sys.stderr.write("ERROR: Alle Frames wurden verworfen (DISCARD_FIRST_N zu groß).\n")
            sys.exit(3)

    O_list = []
    frames_ok = 0

    for fp in files:
        try:
            df = read_dat_with_keys(fp)
        except Exception as e:
            sys.stderr.write(f"[WARN] Kann {fp} nicht lesen: {e}\n")
            continue

        cols = {c.lower(): c for c in df.columns}
        for required in ["x","y","vx","vy"]:
            if required not in cols:
                # unbrauchbarer Frame – überspringen
                break
        else:
            X = df[[cols["x"], cols["y"]]].to_numpy(float)
            V = df[[cols["vx"], cols["vy"]]].to_numpy(float)
            if X.shape[0] < 2:
                continue

            if remove_translation:
                V = V - V.mean(axis=0, keepdims=True)

            O_list.append(compute_O_frame(X, V))
            frames_ok += 1

    if frames_ok == 0:
        sys.stderr.write("O_mean=nan  O_var=nan  (0 Frames verwertbar)\n")
        sys.exit(4)

    O_arr = np.asarray(O_list, dtype=float)
    if frames_ok == 1:
        O_mean = float(O_arr.mean())
        O_var  = 0.0
    else:
        O_mean = float(O_arr.mean())
        O_var  = float(O_arr.var(ddof=1))

    # schlanke Konsolen-Ausgabe
    print(f"O_mean={O_mean:.6f}  O_var={O_var:.6f}  frames={frames_ok}  remove_translation={int(remove_translation)}")
    with open(csvfile, "a") as f:
        f.write(csvtxt +',' + str(O_mean) + ',' + str(O_var) + ',' + str(frames_ok) + '\n')
        f.close()

if __name__ == "__main__":
    main()
