#!/usr/bin/env python3

#############################

import os,sys
import glob
import csv
from collections import defaultdict
import numpy as np
import argparse
import statistics


# Spalten "cc","rand","tau","v","k","nu","gamma","permult","line","O_mean","O_var","frames_ok"(,"Alpha-Relaxaion-Time","IsGlassy","DataCount","minSelfInt")

#-------------------------

def convert_csv(csv_in_file,csv_out_file):
    try:
        os.remove(csv_out_file)
    except:
        pass

    col_count=0
    Dict=defaultdict(set)
    with open(csv_in_file,'r') as f:
        data=csv.reader(f,delimiter=",")
        for row in data:
            group_data=()
            if len(row) == 12:
                group_data=(int(row[1]),float(row[9]),float(row[10]),int(row[11])) # rand,O_mean,O_var,frames_ok
                col_count=12
            if len(row) == 16:
                group_data=(int(row[1]),float(row[9]),float(row[10]),int(row[11]),float(row[12]),int(row[13]),int(row[14]),float(row[15])) # rand,O_mean,O_var,frames_ok,Alpha-Relaxaion-Time,IsGlassy,DataCount
                col_count=16
            # gruppierte Spalten
            group_cols=row[0]+",0,"+row[2]+","+row[3]+","+row[4]+","+row[5]+","+row[6]+","+row[7]+","+row[8]
            Dict[group_cols].add(group_data)

    Lines=0
    for group_cols in Dict:
        Omean_arr=[]
        Ovar_arr=[]
        framesok_arr=[]
        art_arr=[]
        datacount_arr=[]
        glassy_arr=[]
        minSelfInt_arr=[]

        for group_data in Dict[group_cols]:
            Omean_arr.append(group_data[1])
            Ovar_arr.append(group_data[2])
            framesok_arr.append(group_data[3])
            if col_count == 16:
                art_arr.append(group_data[4])
                glassy_arr.append(group_data[5])
                datacount_arr.append(group_data[6])
                minSelfInt_arr.append(group_data[7])

        Omean=np.mean(Omean_arr)
        Ovar=np.mean(Ovar_arr)
        framesok=max(framesok_arr)
        minSelfInt=np.mean(minSelfInt_arr)
        data_str=','+str(Omean)+','+str(Ovar)+','+str(framesok)

        if col_count == 16:
            art=np.mean(art_arr)
            datacount=max(datacount_arr)
            glassy=1
            for i in glassy_arr:
                if i==0:
                    glassy=0
                    break
            data_str=data_str+','+str(art)+','+str(glassy)+','+str(datacount)+','+str(minSelfInt)

        with open(csv_out_file, "a") as f:
            f.write(group_cols+data_str+'\n')
            f.close()
            Lines=Lines+1

    return Lines


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv_in", default="compute_order.csv", help="Optional: csv-in-file")
    ap.add_argument("--csv_out_prefix", default="avg_", help="Optional: csv-out-prefix")

    args = ap.parse_args()

    csv_in=args.csv_in
    csv_out_prefix=args.csv_out_prefix

    csv_out=""
    if os.path.dirname(csv_in) != "":
        csv_out=os.path.dirname(csv_in)+os.sep
    csv_out=csv_out+csv_out_prefix+os.path.basename(csv_in)
    print(f"Input: {csv_in}")
    Lines=convert_csv(csv_in,csv_out)
    print(f"Output: {csv_out} (lines: {Lines})")

if __name__ == "__main__":
    main()
