#!/usr/bin/env python3

#############################

import os,sys
import csv
import argparse
import numpy as np

# Spalten1 "cc","rand","tau","v","k","nu","gamma","permult","line","O_mean","O_var","frames_ok"
# Spalten2 "cc","rand","tau","v","k","nu","gamma","permult","line","Alpha-Relaxaion-Time","IsGlassy","DataCount,minSelfInt"

#-------------------------
def conv_csv(csv1,csv2):
    Lines=0

    try:
        os.remove(csv2)
    except:
        pass

    with open(csv1,'r') as f1:
        data=csv.reader(f1,delimiter=",")
        for row in data:
            row_new=row[0]
            for i in range(1,len(row)):
                if i==7:
                    row_new=row_new+","+str(round(2*float(row[i])/np.sqrt(3.0),2))
                else:
                    row_new=row_new+","+row[i]

            with open(csv2, "a") as f2:
                f2.write(row_new+'\n')
                f2.close()
                Lines=Lines+1
        f1.close()
    return Lines


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv1", default="compute_order.csv", help="Optional: csv1-file")
    ap.add_argument("--csv2", default="compute_order_p0.csv", help="Optional: csv2-file")

    args = ap.parse_args()

    csv1=args.csv1
    csv2=args.csv2

    print(f"Input:  {os.path.basename(csv1)}")
    Lines=conv_csv(csv1,csv2)
    print(f"Output-lines: {Lines}")
    print(f"Output: {os.path.basename(csv2)}")
if __name__ == "__main__":
    main()
