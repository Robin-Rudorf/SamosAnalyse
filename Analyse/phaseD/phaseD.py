#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_phase_diagram.py

Liest eine compute_order-CSV mit Spalten

  cc, rand, tau, v, k, nu, gamma, permult, line,
  O_mean, O_var, frames_ok,
  alpha_relaxation_time, isglassy, datacount, minSelfInt

und baut ein "großes" Phasendiagramm im (permult, tau)-Raum für
eine gegebene Zellzahl und ein gegebenes Parameterset.

Was das Skript macht:
---------------------
1. CSV einlesen.
2. Auf gewünschte cc und Parameter (v, nu, gamma, line, k) filtern.
3. Über Seeds (rand) mitteln:
   - <O_mean>
   - fraction_flock = Anteil der Seeds mit O_mean > O_thresh
   - glass_fraction = Mittelwert von isglassy (0/1)
   - <alpha_relaxation_time>
4. 2D-Gitter über (permult, tau) bauen.
5. Phase Diagram Plot:
   - Farbkarte: <O_mean> (0 = ungeordnet, 1 = volle Ordnung).
   - Kontur: glass_fraction = 0.5 (ungefähre Solid–Fluid-Grenze).
   - Optional: Kontur für fraction_flock = 0.5 (Übergang zur flocking Phase).

Output:
-------
- phase_diagram_perm_tau.png in demselben Ordner.

Aufruf-Beispiele:
-----------------
  python3 plot_phase_diagram.py
  python3 plot_phase_diagram.py --csv compute_order.csv --cc 1024
  python3 plot_phase_diagram.py --cc 256 --v 0.05 --nu 0.15 --gamma 0.1 --line 0.1

Passen dir die Defaults für O_thresh usw. nicht, ändere sie einfach im Kopf.
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os


VALID_COLS = ["cc","rand","tau","v","k","nu","gamma","p0","line","O_mean","O_var","frames_ok","alpha_relaxation_time","isglassy","datacount","minSelfInt"]


def make_edges(vals):
    """
    Aus sortierten Gitterpunkten vals die Kanten für pcolormesh bauen.
    vals: 1D-array (z.B. permult-Werte)
    Rückgabe: Kanten-Array der Länge len(vals)+1
    """
    vals = np.asarray(vals)
    if len(vals) == 1:
        # Degenerierter Fall: eine einzelne Spalte
        d = 0.5
        return np.array([vals[0] - d, vals[0] + d])
    diffs = np.diff(vals)
    # mittlere Abstände nehmen
    step = np.median(diffs)
    edges = np.zeros(len(vals) + 1)
    edges[1:-1] = 0.5 * (vals[:-1] + vals[1:])
    edges[0] = vals[0] - step / 2.0
    edges[-1] = vals[-1] + step / 2.0
    return edges


def main():
    parser = argparse.ArgumentParser(
        description="Erzeuge ein (p0, tau)-Phasendiagramm aus compute_order-CSV."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="compute_order_p0.csv",
        help="Pfad zur CSV-Datei (Default: compute_order.csv)",
    )
    parser.add_argument(
        "--cc",
        type=int,
        default=1024,
        help="Zellzahl, auf die gefiltert wird (cc-Spalte). Default: 1024",
    )
    # optionale Filter für andere Parameter; None = ignoriere
    parser.add_argument("--v", type=float, default=None, help="Filter für v (optional)")
    parser.add_argument("--k", type=float, default=None, help="Filter für k (optional)")
    parser.add_argument("--nu", type=float, default=None, help="Filter für nu (optional)")
    parser.add_argument("--gamma", type=float, default=None, help="Filter für gamma (optional)")
    parser.add_argument("--line", type=float, default=None, help="Filter für line tension (optional)")

    parser.add_argument(
        "--O_thresh",
        type=float,
        default=0.8,
        help="Schwellwert für 'flocking' (O_mean > O_thresh). Default: 0.8",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="phase_diagram_perm_tau.png",
        help="Name der Output-PNG-Datei",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {args.csv}")

    print(f"Lese CSV: {args.csv}")
    df = pd.read_csv(args.csv, header=None, names=VALID_COLS)

    #df = pd.read_csv(args.csv)

    # Grundfilter: Zellzahl
    df = df[df['cc'] == args.cc]
    if df.empty:
        raise RuntimeError(f"Keine Daten für cc={args.cc} gefunden.")

    # Optionale weitere Filter
    for name in ["v", "k", "nu", "gamma", "line"]:
        val = getattr(args, name)
        if val is not None:
            if name not in df.columns:
                raise RuntimeError(f"Spalte '{name}' nicht in CSV vorhanden.")
            # Toleranz für float-Vergleich
            tol = 1e-8
            df = df[np.isclose(df[name], val, atol=tol)]
            print(f"Filter {name} = {val}: {len(df)} Zeilen übrig")

    if df.empty:
        raise RuntimeError("Nach den Filtern ist das DataFrame leer. Filter anpassen!")

    # isglassy sollte 0/1 sein; sicherheitshalber
    df["isglassy"] = df["isglassy"].astype(float)

    # zusätzliche Klassifikation: flocking ja/nein pro Run
    df["is_flock"] = (df["O_mean"] > args.O_thresh).astype(float)

    # Gruppiere über Seeds: (p0, tau)
    group_cols = ["p0", "tau"]
    grouped = df.groupby(group_cols)

    summary = grouped.agg(
        O_mean_avg=("O_mean", "mean"),
        O_mean_std=("O_mean", "std"),
        glass_fraction=("isglassy", "mean"),
        flock_fraction=("is_flock", "mean"),
        alpha_mean=("alpha_relaxation_time", "mean"),
        alpha_median=("alpha_relaxation_time", "median"),
        minSelfInt_mean=("minSelfInt", "mean"),
        runs=("O_mean", "size"),
    ).reset_index()

    print("Zusammenfassung über Seeds (erste Zeilen):")
    print(summary.head())

    # Gitter-Koordinaten
    perm_vals = np.sort(summary["p0"].unique())
    tau_vals = np.sort(summary["tau"].unique())

    # Hilfsfunktion zum Pivoten
    def pivot_to_grid(value_col):
        pivot = summary.pivot(index="tau", columns="p0", values=value_col)
        # reindex, um sicherzugehen, dass Reihenfolge stimmt
        pivot = pivot.reindex(index=tau_vals, columns=perm_vals)
        return pivot.values

    O_grid = pivot_to_grid("O_mean_avg")
    glass_grid = pivot_to_grid("glass_fraction")
    flock_grid = pivot_to_grid("flock_fraction")

    # Kanten für pcolormesh
    perm_edges = make_edges(perm_vals)
    tau_edges = make_edges(tau_vals)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Farbkarte: mittleres O_mean
    cmap = plt.get_cmap("viridis")
    im = ax.pcolormesh(perm_edges, tau_edges, O_grid, cmap=cmap, shading="auto", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(r"$\langle O_{\mathrm{mean}} \rangle$ over seeds")

    # Kontur: Solid–Fluid-Grenze aus glass_fraction = 0.5
    try:
        cs1 = ax.contour(
            perm_vals,
            tau_vals,
            glass_grid,
            levels=[0.5],
            colors="white",
            linewidths=1.5,
        )
        cs1.collections[0].set_label("glass fraction = 0.5 (solid–fluid boundary)")
    except Exception as e:
        print(f"Warnung: konnte glass_fraction-Kontur nicht plotten: {e}")

    # Kontur: flocking-Grenze aus flock_fraction = 0.5
    try:
        cs2 = ax.contour(
            perm_vals,
            tau_vals,
            flock_grid,
            levels=[0.5],
            colors="red",
            linestyles="--",
            linewidths=1.5,
        )
        cs2.collections[0].set_label(f"flock fraction = 0.5 (O_mean>{args.O_thresh:g})")
    except Exception as e:
        print(f"Warnung: konnte flock_fraction-Kontur nicht plotten: {e}")

    ax.set_xlabel("p0 (∝ target shape index $p_0$)")
    ax.set_ylabel(r"alignment time $\tau$")
    ax.set_title(f"Phase diagram for cc={args.cc}")

    # Legende nur, wenn Konturen vorhanden
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper right", fontsize=8, frameon=True)

    fig.tight_layout()
    fig.savefig(args.output, dpi=300)
    print(f"Phasendiagramm gespeichert als: {args.output}")


if __name__ == "__main__":
    main()
