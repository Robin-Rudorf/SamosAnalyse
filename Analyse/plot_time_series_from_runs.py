#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_time_series_from_runs.py

Erzeugt für jeden Run unterhalb eines Basisverzeichnisses (Default: ./open_boundaries)
die Zeitserie des Ordnungsparameters O(t), so wie er in compute_order.py definiert ist:

    O_frame = sqrt(P^2 + R^2 + Delta_net^2)

Die Frame-Dateien werden genau wie in compute_order.py gesucht und gelesen
(cell_*.dat oder cell_full_*.dat), inkl. 'keys:'-Header.

WICHTIG:
- Standardmäßig wird KEIN COM-Abzug der Geschwindigkeit gemacht
  (Lab-Frame, also V wie aus der Simulation).
- Wenn du explizit im COM-Frame auswerten willst, nutze die Option --remove-com.

Für jeden Run wird gespeichert (Standard):
  - analyse/time_series/timeseries_<Parameterkombination>.png
  - analyse/time_series/timeseries_<Parameterkombination>.csv   (Spalten: t, O)

Aufrufbeispiele:
  python3 plot_time_series_from_runs.py
  python3 plot_time_series_from_runs.py --discard-first 100
  python3 plot_time_series_from_runs.py --remove-com
  python3 plot_time_series_from_runs.py --out-dir analyse/time_series_com
"""

import  os, re
import argparse
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shutil





# ---------- Hilfsfunktionen ----------

def normalize(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / (n + eps)

def find_run_directories(base_dir):
    """
    Suche rekursiv nach Verzeichnissen, die mindestens eine cell_*.dat
    oder cell_full_*.dat Datei enthalten.
    """
    run_dirs = []
    for dirpath, dirnames, filenames in os.walk(base_dir):
        has_cell = any(fn.startswith("cell_") and fn.endswith(".dat")
                       for fn in filenames)
        has_cell_full = any(fn.startswith("cell_full_") and fn.endswith(".dat")
                            for fn in filenames)
        if has_cell or has_cell_full:
            run_dirs.append(dirpath)         
    return sorted(run_dirs)

 
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



def compute_time_series_for_run(run_dir, discard_first, remove_com=False):
    """
    Berechne O(t) für einen einzelnen Run (run_dir).

    remove_com = False  -> Lab-Frame (keine COM-Drift-Subtraktion)
    remove_com = True   -> COM-Frame (V -> V - mean(V))

    Gibt (times, O_values) zurück.
    """
    files = find_frame_files(run_dir)
    if not files:
        print(f"[WARN] Keine Frame-Dateien in {run_dir}")
        return [], []

    # Transienten verwerfen
    if discard_first > 0:
        files = files[discard_first:]
        if not files:
            print(f"[WARN] Alle Frames verworfen in {run_dir} (discard_first zu groß).")
            return [], []

    times = []
    O_values = []

    for fp in files:
        try:
            df = read_dat_with_keys(fp)
        except Exception as e:
            print(f"[WARN] Kann {fp} nicht lesen: {e}")
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

        # HIER: COM-Abzug optional, default = False
        if remove_com:
            V = V - V.mean(axis=0, keepdims=True)

        O_frame = compute_O_frame(X, V)
        t = extract_frame_index(fp)

        times.append(t)
        O_values.append(O_frame)

    return times, O_values


def make_output_basename(run_dir, base_dir):
    
    base= run_dir.replace(base_dir+os.sep,"").replace(os.sep, "_")
    return base


def plot_and_save_time_series(run_dir, base_dir, out_dir,
                              times, O_values,
                              remove_com=False):
    """
    Speichere PNG und CSV für einen Run im zentralen out_dir.
    """
    if not times:
        print(f"[WARN] Keine Daten für Plot in {run_dir}")
        return
    
    

    # sortieren nach Zeit
    times = np.array(times)
    O_values = np.array(O_values)
    idx = np.argsort(times)
    times = times[idx]
    O_values = O_values[idx]

    # Plot-Titel

    title = make_output_basename(run_dir, base_dir)
    if remove_com:
        title += " (COM-drift removed)"
    else:
        title += " (Lab frame)"

    # Basis-Dateiname – mit Suffix für COM/Lab
    suffix = "_COM" if remove_com else "_LAB"
    base_name = make_output_basename(run_dir, base_dir)+suffix

    # Plot
    plt.figure(figsize=(8, 4))
    plt.plot(times, O_values, linewidth=1)
    plt.xlabel("time (frame index)")
    plt.ylabel("O(t)")
    plt.title(title, fontsize=10)
    plt.tight_layout()

    png_path = os.path.join(out_dir, base_name + ".png")
    plt.savefig(png_path, dpi=200)
    plt.close()

    # CSV
    csv_path = os.path.join(out_dir, base_name + ".csv")
    with open(csv_path, "w") as f:
        f.write("# t, O(t)\n")
        for t, o in zip(times, O_values):
            f.write(f"{t},{o}\n")

    print(f"[OK] {png_path}")


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Plotte O(t)-Zeitserien für alle Runs unterhalb eines Basis-Ordners "
            "unter Verwendung derselben O-Definition wie compute_order.py.\n"
            "Standard: Lab-Frame (keine COM-Drift-Subtraktion). "
            "Mit --remove-com kannst du in den COM-Frame wechseln."
        )
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="samos_runs",
        help="Basisverzeichnis der Runs (Default: ./samos_runs)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=os.path.join("analyse", "time_series"),
        help="Zielordner für alle Time-Series-Dateien "
             "(Default: ./analyse/time_series)",
    )
    parser.add_argument(
        "--discard-first",
        type=int,
        default=0,
        help="Anzahl Frames am Anfang, die verworfen werden sollen (Default: 0)",
    )
    parser.add_argument(
        "--remove-com",
        action="store_true",
        help=(
            "COM-Drift der Geschwindigkeiten entfernen (V -> V - mean(V)). "
            "Ohne diese Option wird im Lab-Frame ausgewertet."
        ),
    )

    args = parser.parse_args()

    base_dir = os.path.abspath(args.base_dir)
    out_dir = os.path.abspath(args.out_dir)
    if not os.path.isdir(base_dir):
        print(f"[ERROR] Basisverzeichnis existiert nicht: {base_dir}")
        return

    remove_com = args.remove_com

    if  os.path.isdir(out_dir):
        shutil.rmtree(out_dir)   

    os.makedirs(out_dir, exist_ok=True)

    run_dirs = find_run_directories(base_dir)
    if not run_dirs:
        print(f"[ERROR] Keine Run-Verzeichnisse unter {base_dir} gefunden.")
        return

    print(f"Gefundene Runs: {len(run_dirs)}")
    print(f"Output-Ordner: {out_dir}")
    print(f"Frame-Discard: {args.discard_first}")
    print(f"COM-Drift-Abzug: {'JA (COM-frame)' if remove_com else 'NEIN (Lab-frame)'}")

    for rd in run_dirs:
        times, O_vals = compute_time_series_for_run(
            rd,
            discard_first=args.discard_first,
            remove_com=remove_com,
        )
        plot_and_save_time_series(
            rd, base_dir, out_dir,
            times, O_vals,
            remove_com=remove_com,
        )


if __name__ == "__main__":
    main()
