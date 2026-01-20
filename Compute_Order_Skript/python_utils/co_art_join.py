#!/usr/bin/env python3

#############################

import os,sys
import glob
import csv
import argparse
import shutil

# Spalten1 "cc","rand","tau","v","k","nu","gamma","permult","line","O_mean","O_var","frames_ok"
# Spalten2 "cc","rand","tau","v","k","nu","gamma","permult","line","Alpha-Relaxaion-Time","IsGlassy","DataCount,minSelfInt"

#-------------------------
def join_csv(csv1,csv2):
    Dict=dict()
    Lines=0
    ErrLines=0

    try:
        with open(csv1,'r') as f:
            data=csv.reader(f,delimiter=",")
            for row in data:
                if len(row) != 12:
                    print(f"Error {csv1} cols found: {len(row)} ; cols need: 12")
                    sys.exit(1)
                    return

                values=[row[9],row[10],row[11],str(0.0),str(1),str(0),str(1)] # O_mean,O_var,Alpha-Relaxaion-Time,IsGlassy,DataCount,minSelfInt
                fix_cols=row[0]
                for i in range(1,9):
                    fix_cols=fix_cols+","+row[i]
                Dict[fix_cols]=values
            f.close()
    except:
        print(f"Error open {csv1}")
        sys.exit(1)
        return

    try:
        with open(csv2,'r') as f:
            data=csv.reader(f,delimiter=",")
            for row in data:
                if len(row) != 13:
                    print(f"Error {csv2} cols found: {len(row)} ; cols need: 13")
                    sys.exit(1)
                    return

                fix_cols=row[0]
                for i in range(1,9):
                    fix_cols=fix_cols+","+row[i]

                if Dict.get(fix_cols,None) is None:
                    ErrLines=ErrLines+1
                else:
                    Dict[fix_cols][3]=row[9]  # Alpha-Relaxaion-Time
                    Dict[fix_cols][4]=row[10] # IsGlassy
                    Dict[fix_cols][5]=row[11] # DataCount_ART
                    Dict[fix_cols][6]=row[12] # minSelfInt
            f.close()
    except:
        print(f"Error open {csv2}")
        sys.exit(1)
        return

    try:
        os.remove(csv1)
    except:
        print(f"Error delete {csv1}")
        sys.exit(1)
        return

    for row in Dict:
        daten=row
        for i in range(7):
            daten=daten+","+Dict[row][i]

        with open(csv1, "a") as f:
            f.write(daten+'\n')
            f.close()
            Lines=Lines+1

    return Lines,ErrLines


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv1", default="compute_order.csv", help="Optional: csv1-file")
    ap.add_argument("--csv2", default="art.csv", help="Optional: csv2-file")

    args = ap.parse_args()

    csv1=args.csv1
    csv2=args.csv2

    csv_backup=""
    if os.path.dirname(csv1) != "":
        csv_backup=os.path.dirname(csv1)+os.sep
    csv_backup=csv_backup+"backup_"+os.path.basename(csv1)

    if os.path.exists(csv_backup):
        print(f"Error {csv_backup} exists")
        sys.exit(1)

    try:
        shutil.copyfile(csv1,csv_backup)
    except:
        print(f"Error copy {csv1} to {csv_backup}")
        sys.exit(1)

    print(f"Input1: {os.path.basename(csv1)}")
    print(f"Input2: {os.path.basename(csv2)}")
    Lines,ErrLines=join_csv(csv1,csv2)
    if ErrLines>0:
        print(f"{ErrLines} lines from {os.path.basename(csv2)} was not written")
    print(f"Output-lines: {Lines}")
    print(f"Output: {os.path.basename(csv1)}")
    print(f"Backup: {os.path.basename(csv_backup)}")
    print("CSV-Format: cc,rand,tau,v,k,nu,gamma,permult,line,O_mean,O_var,frames_ok,AlphaRelaxationTime,IsGlassy,DataCount,minSelfInt")

if __name__ == "__main__":
    main()
