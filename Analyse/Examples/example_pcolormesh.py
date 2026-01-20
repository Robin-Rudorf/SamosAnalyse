#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np


# 1. Daten vorbereiten
x = np.arange(11)  # x-Koordinaten (0, 1, 2, 3, 4)
y = np.arange(11)  # y-Koordinaten (0, 1, 2, 3)

x=[ 0.12 ,0.121, 0.122 , 0.123 ,0.124 ] 

# C muss ein (len(y)-1) x (len(x)-1) Array sein, wenn X, Y die Kanten definieren
# Hier erstellen wir C so, dass es zu den Kanten passt
C = np.random.rand(10, 4) # 3 Zeilen (y-Richtung), 4 Spalten (x-Richtung)
print(C)

# 2. Plot erstellen
plt.figure(figsize=(11, 6))
mesh = plt.pcolormesh(x, y, C, cmap='viridis') # 'viridis' ist eine Farbpalette

# 3. Farbleiste hinzufügen (optional, aber nützlich)
plt.colorbar(mesh, label='Werte')

# 4. Achsenbeschriftungen und Titel (optional)
plt.xlabel('X-Achse')
plt.ylabel('Y-Achse')
plt.title('Einfaches pcolormesh Beispiel')

# 5. Plot anzeigen
plt.savefig('tom.png')
