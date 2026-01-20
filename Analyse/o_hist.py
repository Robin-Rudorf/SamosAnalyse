#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_omean_histograms_tau_range_combined.py

Liest eine compute_order-CSV (ohne Header, wie von deinem compute_order.py)
und plottet:

1) Für alle tau-Werte im Bereich [TAU_MIN, TAU_MAX]:
   -> je EIN Histogramm der O_mean-Werte (über alle Seeds/Runs mit diesem tau).

2) EIN zusätzliches "kombiniertes" Histogramm:
   -> alle O_mean-Werte aller Runs mit tau im Bereich [TAU_MIN, TAU_MAX]
      in EINEM Histogramm, um die globale Bimodalität im kritischen Fenster
      zu zeigen.

TAU_MIN und TAU_MAX werden direkt im Skript unten gesetzt.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# >>> HIER ANPASSEN <<<

CSV_FILE = "compute_order.csv"   # Name CSV (im selben Ordner wie dieses Skript)
TAU_MIN  = 0.10                  # untere Grenze für tau (inklusive)
TAU_MAX  = 0.30                  # obere Grenze für tau (inklusive)

# Feste Bins für O_mean im Bereich [0,1]:
# z.B. 21 Kanten => 20 Bins von Breite 0.05
BINS = np.linspace(0.0, 1.0, 21)

# ==========================


def load_compute_order(csv_file):
    """CSV ohne Header einlesen und Spalten sinnvoll benennen."""
    try:
        df = pd.read_csv(csv_file, header=None)
    except Exception as e:
        print(f"[ERROR] Kann Datei {csv_file} nicht lesen: {e}")
        sys.exit(1)

    if df.shape[1] < 10:
        print(f"[ERROR] Unerwartetes Format in {csv_file} (zu wenige Spalten).")
        sys.exit(1)

    # Nach deinem Format:
    # 0: N
    # 1: seed
    # 2: tau
    # 3: nu
    # 4: v0
    # 5: noise (nu_rot o.ä.)
    # 6: param6
    # 7: permult
    # 8: param8
    # 9: O_mean
    # 10: O_var
    # 11: n_frames
    df = df.rename(
        columns={
            0: "N",
            1: "seed",
            2: "tau",
            3: "nu",
            4: "v0",
            5: "noise",
            6: "param6",
            7: "permult",
            8: "param8",
            9: "O_mean",
            10: "O_var",
            11: "n_frames",
        }
    )

    return df


def main():
    if TAU_MAX < TAU_MIN:
        print("[ERROR] TAU_MAX muss >= TAU_MIN sein.")
        sys.exit(1)

    csv_path = os.path.abspath(CSV_FILE)
    if not os.path.isfile(csv_path):
        print(f"[ERROR] CSV-Datei nicht gefunden: {csv_path}")
        sys.exit(1)

    df = load_compute_order(csv_path)

    # alle einzigartigen tau-Werte im Bereich
    taus_all = np.sort(df["tau"].unique())
    taus_in_range = [t for t in taus_all if TAU_MIN <= t <= TAU_MAX]

    if not taus_in_range:
        print(
            f"[ERROR] Keine tau-Werte im Bereich [{TAU_MIN}, {TAU_MAX}] in {CSV_FILE}."
        )
        print("Verfügbare tau-Werte sind z.B.:")
        for t in taus_all:
            print(f"  {t}")
        sys.exit(1)

    print(f"[INFO] Datei: {CSV_FILE}")
    print(f"[INFO] tau-Bereich: [{TAU_MIN}, {TAU_MAX}]")
    print(f"[INFO] Gefundene tau-Werte im Bereich: {taus_in_range}")

    base_csv = os.path.splitext(os.path.basename(CSV_FILE))[0]
    out_dir = os.path.dirname(csv_path)

    N_values = sorted(df["N"].unique())
    N_str = "mixed"
    if len(N_values) == 1:
        N_str = str(int(N_values[0]))

    # ----- 1) Pro-tau-Histogramme -----
    all_ovals_in_range = []  # für das kombinierte Histogramm

    for tau_val in taus_in_range:
        # Zeilen für genau diesen tau-Wert
        mask = np.isclose(df["tau"].values, tau_val, rtol=0.0, atol=1e-9)
        sub = df.loc[mask]

        if sub.empty:
            print(f"[WARN] Keine Zeilen für tau = {tau_val} gefunden, überspringe.")
            continue

        ovals = sub["O_mean"].values
        seeds = sub["seed"].tolist()
        N_local = sorted(sub["N"].unique())
        if len(N_local) == 1:
            N_here = int(N_local[0])
        else:
            N_here = None  # gemischt

        all_ovals_in_range.extend(list(ovals))

        print(
            f"[INFO] tau = {tau_val}: {len(ovals)} Runs "
            f"(Seeds: {seeds}, N={'mixed' if N_here is None else N_here})"
        )

        # Histogramm für diesen einzelnen tau
        plt.figure(figsize=(6, 4))
        plt.hist(ovals, bins=BINS, edgecolor="black")
        plt.xlabel("O_mean")
        plt.ylabel("Anzahl Runs")
        title = f"O_mean-Histogramm für tau = {tau_val}"
        if N_here is not None:
            title += f" (N = {N_here})"
        plt.title(title)
        plt.tight_layout()

        tau_str = str(tau_val).replace(".", "p")
        out_name = f"hist_omean_{base_csv}_N{N_str}_tau{tau_str}.png"
        out_path = os.path.join(out_dir, out_name)
        plt.savefig(out_path, dpi=200)
        plt.close()

        print(f"[OK] Histogramm für tau = {tau_val} gespeichert als: {out_path}")

    # ----- 2) Kombiniertes Histogramm über den ganzen tau-Bereich -----

    all_ovals_in_range = np.array(all_ovals_in_range)
    if all_ovals_in_range.size == 0:
        print("[WARN] Keine O_mean-Werte im tau-Bereich gefunden, kein Gesamt-Histogramm.")
        return

    plt.figure(figsize=(6, 4))
    plt.hist(all_ovals_in_range, bins=BINS, edgecolor="black")
    plt.xlabel("O_mean")
    plt.ylabel("Anzahl Runs (alle tau im Bereich)")
    plt.title(
        f"O_mean-Histogramm für tau in [{TAU_MIN}, {TAU_MAX}] "
        f"(alle Runs, N={N_str})"
    )
    plt.tight_layout()

    tau_min_str = str(TAU_MIN).replace(".", "p")
    tau_max_str = str(TAU_MAX).replace(".", "p")
    combined_name = (
        f"hist_omean_combined_{base_csv}_N{N_str}_tau{tau_min_str}_to_{tau_max_str}.png"
    )
    combined_path = os.path.join(out_dir, combined_name)
    plt.savefig(combined_path, dpi=200)
    plt.close()

    print(f"[OK] Kombiniertes Histogramm gespeichert als: {combined_path}")


if __name__ == "__main__":
    main()
