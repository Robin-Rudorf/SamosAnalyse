#!/usr/bin/env python3

#############################

import os,sys
import glob
import matplotlib.pyplot as plt
import csv
import numpy as np
import argparse

# ---------- Plotfunktion ----------

VALID_COLS = ["cc","rand","tau","v","k","nu","gamma","permult","line","Alpha-Relaxaion-Time","IsGlassy","DataCount"]
LEN_FIX_COLS = 9


def plot(csv_file,xcol,ycol,xlabel,ylabel,xsize,ysize,title_pre,png_suffix,scatter,cmap):

    wcol="Alpha-Relaxaion-Time"
    dcol="DataCount"
    xcol_int=-1
    ycol_int=-1
    wcol_int=-1
    dcol_int=-1
    for i in range(len(VALID_COLS)):
        if xcol==VALID_COLS[i]:
            xcol_int=i
        if ycol==VALID_COLS[i]:
            ycol_int=i
        if wcol==VALID_COLS[i]:
            wcol_int=i
        if dcol==VALID_COLS[i]:
            dcol_int=i

    if xcol_int==-1 or ycol_int==-1 or wcol_int==-1 or dcol_int==-1:
        print(f"Error: xcol: {xcol} , ycol: {ycol} , wcol {wcol} , dcol {dcol}", file=sys.stderr)
        return

    x=[]
    y=[]
    w=[] # Wert Color (ART)
    xval=[]
    yval=[]
    lastrow=[]
    with open(csv_file,'r') as f:
        data=csv.reader(f,delimiter=",")
        for row in data:
            if float(row[dcol_int])<26:
                continue
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

            lastrow=row

    if not x:
        print(f"[WARN] Keine Daten für Plot in csv", file=sys.stderr)
        return

    title=title_pre
    for i in range(LEN_FIX_COLS):
        if VALID_COLS[i] == xcol:
            continue
        if VALID_COLS[i] == ycol:
            continue

        wert=lastrow[i]
        if i != 0 or title != "":
            title=title+" , "
        title=title+VALID_COLS[i]+": "+str(wert)

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
        #pltarray[y2[i]][x2[i]]=w[i]
        pltarray[y2[i]][x2[i]]=np.log10(w[i])  # ART als log10 passt besser

    # Für die Tick-Anzahl, Wert spielt keine Rolle - diese Werte werden im Diagramm angezeigt:
    xval.append(max(xval))
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

    mesh=ax.pcolormesh(x_koord,y_koord,pltarray,cmap=cmap,vmin=0.5) # Color-Skala erst bei 0.5 beginnen

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
    cbar=fig.colorbar(mesh,shrink=1,label=wcol)

    # der 2. Parameter erscheint im Diagramm
    plt.xticks(xticks,xval,fontsize=8,rotation=90)
    plt.yticks(yticks,yval,fontsize=8)

    # Letzten Wert der Ticks und 0 nicht angezeigen:
    plt.xlim(0.01,max(x_koord)-0.01)
    plt.ylim(0.01,max(y_koord)-0.01)

    plt.title(title, fontsize=10)

    # Colorbar-Beschriftung
    cy=cbar.ax.get_yticks()
    cy1=[]
    cy2=[]
    for i in range(len(cy)-1):
        cy1.append(cy[i])
        cy2.append(round(np.power(10,cy[i])))
    cbar.ax.set_yticks(cy1)
    cbar.ax.set_yticklabels(cy2)

    plt.tight_layout()

    png_path=os.path.splitext(csv_file)[0]+png_suffix+".png"
    plt.savefig(png_path,dpi=200)
    plt.close()
    return png_path

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", default="art_pickle_data.csv", help="Optional: csv-file")
    ap.add_argument("--png_suffix", default="_color", help="Optional: png-suffix")
    ap.add_argument("--xcol", default="permult", help="XCol")
    ap.add_argument("--ycol", default="v", help="YCol")
    ap.add_argument("--xsize", default=8, help="Optional: Diagramm x-width in inch")
    ap.add_argument("--ysize", default=5, help="Optional: Diagramm y-width in inch")
    ap.add_argument("--xlabel", default="", help="Optional: XLabel")
    ap.add_argument("--ylabel", default="", help="Optional: YLabel")
    ap.add_argument("--title", default="", help="Optional: Title-Prefix")
    ap.add_argument("--scatter", default=5, help="Optional: Scatter Point Size")
    ap.add_argument("--colormap", default="Reds", help="Optional: Colormap")

    args = ap.parse_args() 

    png_suffix=args.png_suffix
    title_pre=args.title
    xcol=args.xcol
    ycol=args.ycol
    xsize=int(args.xsize)
    ysize=int(args.ysize)
    scatter=int(args.scatter)
    cmap=args.colormap
    xlabel=args.xlabel
    ylabel=args.ylabel
    if xlabel == "":
        xlabel=xcol
    if ylabel == "":
        ylabel=ycol

    csv_file=args.csv
    csv_root,csv_ext=os.path.splitext(csv_file)
    files=glob.glob(csv_root+"*"+csv_ext)

    if len(files)<1:
        print(f"No files found {csv_root}*{csv_ext}")
        sys.exit(1)

    Plot_Err=0
    for f in files:
        output=os.path.splitext(f)[0]
        print(f"Input: {os.path.basename(f)}")

        out = plot(f,xcol,ycol,xlabel,ylabel,xsize,ysize,title_pre,png_suffix,scatter,cmap)
        if out:
            print(f"Saved: {out}")
        else:
            print(f"Error: {output}.png", file=sys.stderr)
            Plot_Err=1

    sys.exit(Plot_Err)

if __name__ == "__main__":
    main()
