#!/usr/bin/env python3
"""
Generator für Anfangsbedingungen im Active-Vertex-Model (SAMoS/AVM-Stil).

Erzeugt:
  - <prefix>.input    : Partikeldaten (Zellzentren + Randpunkte)
  - <prefix>.boundary : Boundary-Segmente (Index, id_start, id_end)

Spalten im .input:
  keys: id radius x y z vx vy vz nx ny nz nvx nvy nvz area type boundary

Anlehnung an:
  - Barton et al., PLoS Comput Biol 2017, Active Vertex Model
  - SAMoS (Soft Active Matter on Surfaces)
"""

import math
import random
import argparse


def generate_hex_positions(n_cells, A0=3.0):
    """
    Erzeuge n_cells Positionen auf ungefähr hexagonaler Packung in einer Scheibe.

    Returns
    -------
    positions : list of (x, y)
    R_domain  : effektiver Radius der Zellscheibe
    """
    # hexagonaler Abstand so, dass Fläche pro Zelle ~ A0 ist:
    a = math.sqrt(2.0 * A0 / math.sqrt(3.0))  # Gitterabstand
    # Start-Radius aus Gesamtfläche
    R = math.sqrt(n_cells * A0 / math.pi)

    while True:
        dy = math.sqrt(3.0) / 2.0 * a
        nx_max = int(math.ceil(R / a)) + 1
        ny_max = int(math.ceil(R / dy)) + 1

        pts = []
        for j in range(-ny_max, ny_max + 1):
            y = j * dy
            offset = (j & 1) * a / 2.0  # Offset für hexagonales Gitter
            for i in range(-nx_max, nx_max + 1):
                x = i * a + offset
                if x * x + y * y <= R * R:
                    pts.append((x, y))

        if len(pts) >= n_cells:
            random.shuffle(pts)
            return pts[:n_cells], R

        # Falls zu wenige Punkte, Radius leicht vergrößern und neu versuchen
        R *= 1.05


def write_input_and_boundary(
    n_cells,
    prefix="epi_init",
    A0=3.0,
    seed=None,
):
    """
    Schreibe <prefix>.input und <prefix>.boundary für n_cells Zellen.
    """
    if seed is not None:
        random.seed(seed)

    # Zellzentren
    positions, R = generate_hex_positions(n_cells, A0=A0)

    # Boundary-Parameter
    # etwas außerhalb der Zellscheibe
    R_boundary = R + math.sqrt(A0 / math.pi)
    # Anzahl Boundarypunkte so, dass der Abstand ~ sqrt(A0) ist
    M = max(8, int(round(2.0 * math.pi * R_boundary / math.sqrt(A0))))

    input_filename = f"{prefix}.input"
    boundary_filename = f"{prefix}.boundary"

    # -------- .input schreiben --------
    with open(input_filename, "w") as f:
        # Header
        f.write(
            "keys: id radius x y z vx vy vz nx ny nz nvx nvy nvz area type boundary\n"
        )

        # Zellen (type=2, boundary=0)
        for pid, (x, y) in enumerate(positions):
            radius = random.uniform(0.85, 1.15)
            z = 0.0
            vx = vy = vz = 0.0

            # Zufällige in-plane Orientierung
            phi = 2.0 * math.pi * random.random()
            nx = math.cos(phi)
            ny = math.sin(phi)
            nz = 0.0

            # Sheet-Normalenvektor
            nvx = 0.0
            nvy = 0.0
            nvz = 1.0

            area = A0
            ptype = 2
            boundary_flag = 0

            f.write(
                f"{pid:d} "
                f"{radius:.5f} "
                f"{x:.6f} {y:.6f} {z:.1f} "
                f"{vx:.6f} {vy:.6f} {vz:.6f} "
                f"{nx:.6f} {ny:.6f} {nz:.1f} "
                f"{nvx:.1f} {nvy:.1f} {nvz:.1f} "
                f"{area:.1f} {ptype:d} {boundary_flag:d}\n"
            )

        # Boundary-Punkte (type=1, boundary=1)
        start_id = n_cells
        for j in range(M):
            angle = 2.0 * math.pi * j / M
            x = R_boundary * math.cos(angle)
            y = R_boundary * math.sin(angle)

            radius = random.uniform(0.85, 1.15)
            z = 0.0
            vx = vy = vz = 0.0

            # radialer Normalenvektor im Sheet
            nx = math.cos(angle)
            ny = math.sin(angle)
            nz = 0.0

            nvx = 0.0
            nvy = 0.0
            nvz = 1.0

            area = A0
            ptype = 1
            boundary_flag = 1
            pid = start_id + j

            f.write(
                f"{pid:d} "
                f"{radius:.5f} "
                f"{x:.6f} {y:.6f} {z:.1f} "
                f"{vx:.6f} {vy:.6f} {vz:.6f} "
                f"{nx:.6f} {ny:.6f} {nz:.1f} "
                f"{nvx:.1f} {nvy:.1f} {nvz:.1f} "
                f"{area:.1f} {ptype:d} {boundary_flag:d}\n"
            )

    # -------- .boundary schreiben --------
    with open(boundary_filename, "w") as fb:
        fb.write("#\n")
        for seg in range(M):
            id_start = start_id + seg
            id_end = start_id + ((seg + 1) % M)  # schließe den Ring
            fb.write(f"{seg:d} {id_start:d} {id_end:d}\n")

    print(f"Wrote {input_filename} and {boundary_filename}")
    print(f"  -> {n_cells} cells, {M} boundary vertices, R ≈ {R:.3f}, R_b ≈ {R_boundary:.3f}")


def main():
    parser = argparse.ArgumentParser(
        description="AVM/SAMoS Initial Condition Generator (input + boundary)."
    )
    parser.add_argument(
        "n_cells",
        type=int,
        help="Anzahl der Zellen im Epithel",
    )
    parser.add_argument(
        "-o",
        "--prefix",
        type=str,
        default="epi_init",
        help="Prefix für Ausgabedateien (default: epi_init -> epi_init.input / .boundary)",
    )
    parser.add_argument(
        "--area",
        type=float,
        default=3.0,
        help="Target-Zellfläche A0 (default: 3.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Zufallsseed für reproduzierbare Konfigurationen",
    )

    args = parser.parse_args()
    write_input_and_boundary(
        n_cells=args.n_cells,
        prefix=args.prefix,
        A0=args.area,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
