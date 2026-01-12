#!/usr/bin/env python3

# Verzeichnis der CSV-Dateien
csv_dir="analyse/time_series"

#############################

import os
import glob
import matplotlib.pyplot as plt
import csv


# ---------- Plotfunktion ----------


def plot_time_series(csv_file):
    x=[]
    y=[]
    with open(csv_file,'r') as f:
        data=csv.reader(f,delimiter=",")
        for row in data:
            x.append(int(row[0]))
            y.append(float(row[1]))

    if not x:
        print(f"[WARN] Keine Daten für Plot in csv")
        return

    # Plot
    title=os.path.splitext(os.path.basename(csv_file))[0]
    plt.figure(figsize=(8, 4))
    plt.plot(x,y,linewidth=1)
    plt.xlabel("time (frame index)")
    plt.ylabel("O(t)")
    plt.title(title, fontsize=10)
    plt.tight_layout()

    png_path=os.path.splitext(csv_file)[0]+".png"
    plt.savefig(png_path,dpi=200)
    plt.close()

    print(f"[OK] {png_path}")


# ---------- main ----------

def main():
    files=glob.glob(os.path.join(csv_dir, "*.csv"))
    for f in files:
        plot_time_series(f)

if __name__ == "__main__":
    main()
