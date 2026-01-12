#!/usr/bin/env python3


#############################

import os,sys,glob
import matplotlib.pyplot as plt
import csv
import numpy as np
import argparse

## PARAMETER

# CSV-Datei(en) - Wildcards erlaubt
CSV_FILE = "analyse/compute_order_*.csv"

# Spalten in csv-Datei
VALID_COLS = ["cc","rand","tau","v","k","nu","gamma","permult","line","O_mean","O_var","frames_ok"]

# X-Achse
XCOL="tau"

# Y-Achse
YCOL="permult"

# Color-Wert
WCOL="O_mean"

# X-Label
XLABEL=XCOL

# Y-Label
YLABEL=YCOL

# W-Label
WLABEL=WCOL

# Title-Prefix
TITLE=""

# Scatter Point Size (0 disable scatter)
SCATTER=5

# Colormap
#COLORMAP="Reds"
COLORMAP="viridis_r"

# Diagramm x-width in inch
XSIZE=15

# Diagramm y-width in inch
YSIZE=7

# Color-Wert logarithmisch ( 0 oder 1)
LOG=0


################################################################################

# ---------- Plotfunktion ----------
def plot(csv_file,xcol,ycol,wcol,xlabel,ylabel,wlabel,xsize,ysize,title,scatter,cmap,log,valid_cols):

    xcol_int=-1
    ycol_int=-1
    wcol_int=-1
    for i in range(len(valid_cols)):
        if xcol==valid_cols[i]:
            xcol_int=i
        if ycol==valid_cols[i]:
            ycol_int=i
        if wcol==valid_cols[i]:
            wcol_int=i

    if xcol_int==-1 or ycol_int==-1 or wcol_int==-1:
        print(f"Error: xcol: {xcol} , ycol: {ycol} , wcol: {wcol}", file=sys.stderr)
        print(f"Valid Cols: {valid_cols}", file=sys.stderr)
        return



    x=[]
    y=[]
    w=[] # Wert Color
    xval=[] # Alle x-werte (einmalig)
    yval=[] # Alle y-werte (einmalig)
    with open(csv_file,'r') as f:
        data=csv.reader(f,delimiter=",")
        for row in data:
            x.append(float(row[xcol_int]))
            y.append(float(row[ycol_int]))
            w.append(float(row[wcol_int]))

            try:
                xval.index(float(row[xcol_int]))
            except ValueError:
                xval.append(float(row[xcol_int]))

            try:
                yval.index(float(row[ycol_int]))
            except ValueError:
                yval.append(float(row[ycol_int]))

    if not x:
        print(f"[WARN] Keine Daten für Plot in csv", file=sys.stderr)
        return

    #Koordinaten (Gitter muss 1 größer als pltarray sein) 
    x_koord=np.arange(len(xval)+1) 
    y_koord=np.arange(len(yval)+1)

    # Enthält die x- und y-Werte jeweils nur einmal
    xval.sort() 
    yval.sort()

    # Statt x und y -Werten werden die entsprechenden Koordinaten in x2 und y2 geschrieben
    x2=[]
    for i in x:
        x2.append(xval.index(i))

    y2=[]
    for i in y:
        y2.append(yval.index(i))

    pltarray=np.zeros((len(yval),len(xval)))

    for i in range(len(w)):
        wert=w[i]
        if log == 1:
            wert=np.log10(w[i])
        else:
            wert=w[i]
        pltarray[y2[i]][x2[i]]=wert

    # Für die richtige Tick-Anzahl, Wert spielt keine Rolle - xval und yval werden im Diagramm angezeigt
    xval.append(max(xval)) # Letzter Wert wird nicht angezeigt
    yval.append(max(yval))

    xticks=[]
    yticks=[]

    # Ticks erstellen, so dass Wert in der Mitte der Balken erscheint.
    for i in x_koord:
        xticks.append(i+0.5)

    for i in y_koord:
        yticks.append(i+0.5)

    # Plot
    fig,ax=plt.subplots()
    fig.set_figwidth(xsize)
    fig.set_figheight(ysize)

    mesh=ax.pcolormesh(x_koord,y_koord,pltarray,cmap=cmap)
    #mesh=ax.pcolormesh(x_koord,y_koord,pltarray,cmap=cmap,vmin=0.5) # Color-Skala erst bei 0.5 beginnen

    if scatter>0:
        # Marker für scatter erstellen
        markerx=[]
        markery=[]
        for i in range(len(xticks)-1):
            for j in range(len(yticks)-1):
                if pltarray[j][i]!=0:
                    markerx.append(xticks[i])
                    markery.append(yticks[j])

        ax.scatter(markerx,markery,marker=".",s=scatter,color="black")

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    cbar=fig.colorbar(mesh,label=wlabel)

    if log == 1:
        cy=cbar.ax.get_yticks()
        cy1=[]
        cy2=[]
        for i in range(len(cy)-1):
            cy1.append(cy[i])
            cy2.append(round(np.power(10,cy[i])))
        cbar.ax.set_yticks(cy1)
        cbar.ax.set_yticklabels(cy2)


    # der 2. Parameter erscheint im Diagramm
    plt.xticks(xticks,xval,fontsize=8,rotation=90)
    plt.yticks(yticks,yval,fontsize=8)

    # Letzten Wert der Ticks und 0 nicht angezeigen:
    plt.xlim(0.01,max(x_koord)-0.01)
    plt.ylim(0.01,max(y_koord)-0.01)

    plt.title(title, fontsize=10)
    plt.tight_layout()

    png_path=os.path.splitext(csv_file)[0]+"_col.png"
    plt.savefig(png_path,dpi=200)
    plt.close()
    return png_path



# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", default=CSV_FILE, help="Optional: csv-file(s)")
    ap.add_argument("--xcol", default=XCOL, help="XCol")
    ap.add_argument("--ycol", default=YCOL, help="YCol")
    ap.add_argument("--wcol", default=WCOL, help="WCol (Color-Wert)")
    ap.add_argument("--xsize", default=XSIZE, help="Optional: Diagramm x-width in inch")
    ap.add_argument("--ysize", default=YSIZE, help="Optional: Diagramm y-width in inch")
    ap.add_argument("--xlabel", default=XLABEL, help="Optional: XLabel")
    ap.add_argument("--ylabel", default=YLABEL, help="Optional: YLabel")
    ap.add_argument("--wlabel", default=WLABEL, help="Optional: WLabel")
    ap.add_argument("--title", default=TITLE, help="Optional: Title-Prefix")
    ap.add_argument("--scatter", default=SCATTER, help="Optional: Scatter Point Size")
    ap.add_argument("--colormap", default=COLORMAP, help="Optional: Colormap")
    ap.add_argument("--log", default=LOG, help="Optional: Color-Wert logarithmisch")
    ap.add_argument("--valid_cols",default=None, help="Optional: Valid Cols (comma sparated)")


    args = ap.parse_args() 

    title=args.title
    xcol=args.xcol
    ycol=args.ycol
    wcol=args.wcol
    xsize=int(args.xsize)
    ysize=int(args.ysize)
    scatter=int(args.scatter)
    log=int(args.log)
    cmap=args.colormap
    xlabel=args.xlabel
    ylabel=args.ylabel
    wlabel=args.wlabel
    csv_file=args.csv


    valid_cols=VALID_COLS
    if args.valid_cols is not None:
        valid_cols=[item for item in args.valid_cols.split(',')]

    Plot_Err=0

    files=glob.glob(csv_file)
    if len(files)<1:
        print(f"No files found for {csv_file}")
        sys.exit(1)

    for f in files:
        output=os.path.splitext(f)[0]
        print(f"Input: {os.path.basename(f)}")

        out = plot(f,xcol,ycol,wcol,xlabel,ylabel,wlabel,xsize,ysize,title+os.path.splitext(os.path.basename(f))[0],scatter,cmap,log,valid_cols)
        if out:
            print(f"Saved: {os.path.basename(out)}")
        else:
            print(f"Error: {os.path.splitext(csv_file)[0]}.png", file=sys.stderr)
            Plot_Err=1

    sys.exit(Plot_Err)


if __name__ == "__main__":
    main()
