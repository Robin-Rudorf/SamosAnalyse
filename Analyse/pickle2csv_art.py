#!/usr/bin/env python3

import sys,os,glob
import pickle
import csv
import argparse

#------------------------

Split=""
#Split="[v]"

#-----------------------

parser=argparse.ArgumentParser(description="Create csv-file from pickle-files (CSV-Format: cc,rand,tau,v,k,nu,gamma,permult,line,AlphaRelaxationTime,IsGlassy,DataCount)",
                               usage='pickle2csv_art.py --dir "analyse/pickle" --csv "art_pickle_data.csv" --split "[cc],[rand]"')
parser.add_argument('--dir',type=str,default=os.path.join('analyse','pickle'),help='Pickle-directory')
parser.add_argument('--csv',type=str,default='art_pickle_data.csv',help='csv-file for output')
parser.add_argument('--split',type=str,default=None,help='Split csv-files via [cc], [rand], [tau], [v], [k], [nu], [gamma], [permult], [line]')
parser.add_argument('--selfint_limit',type=float,default=0.5,help='SelfInt-Limit (Maximum) for Alpha-relaxation-time')

args=parser.parse_args()

dir_pickle=args.dir+os.sep
csv_out,csv_ext=os.path.splitext(args.csv)

Split=args.split or Split
Split=Split.strip()
if Split == "none":
    Split=""

SelfIntLimit=args.selfint_limit

print("Create "+csv_out+csv_ext+" ...")
if Split != '':
    print("Split via "+str(Split))
print("SelfIntLimit: "+str(SelfIntLimit))

for f in glob.glob(csv_out+"*"+csv_ext):
    os.remove(f)

Zeilen=0
noglassy=0
Error=0
time_max=0

# Max Time für AlphaRelaxationTime ermitteln
with open(dir_pickle+"pickle.csv") as f:
    csv_data=csv.reader(f,delimiter=",")
    for row in csv_data:
        picklefile=dir_pickle+row[9]
        try:
            data=pickle.load(open(picklefile, "rb"))
            tplot=data['tplot']
            if len(tplot)<2:
                continue
            if max(tplot)>time_max:
                time_max=max(tplot)
        except:
            continue
# --------------------

with open(dir_pickle+"pickle.csv") as f:
    csv_data=csv.reader(f,delimiter=",")
    for row in csv_data:
        picklefile=dir_pickle+row[9]
        try:
            data=pickle.load(open(picklefile, "rb"))
            tplot=data['tplot']
            SelfInt=data['SelfInt']
            if len(tplot)!=len(SelfInt) or len(tplot)<2:
                sys.stderr.write(picklefile+"\n")
                sys.stderr.write("Len(tplot), Len(SelfInt): "+str(len(tplot))+" , "+str(len(SelfInt))+"\n")
                sys.stderr.write("Error Data-Length\n")
                Error=1
                continue

        except:
            sys.stderr.write(picklefile+"\n")
            sys.stderr.write("Didn't get data\n")
            Error=1
            continue

        # AlphaRelaxationTime
        taualpha=time_max
        isglassy=1
        # Ermittle niedrigsten Index von SelfInt wo SeltInt < SelfIntLimit und
        # speichere den dazugehörigen Time-Wert in taualpha
        hmm=[index for index,value in enumerate(SelfInt) if value<SelfIntLimit]
        if len(hmm)>0:
            idx=min(hmm)
            taualpha=tplot[idx]
            isglassy=0
            noglassy=noglassy+1

        csv_name=csv_out
        if "[cc]" in Split:
            csv_name=csv_name+";cc_"+row[0]
        if "[rand]" in Split:
            csv_name=csv_name+";rand_"+row[1]
        if "[tau]" in Split:
            csv_name=csv_name+";tau_"+row[2]
        if "[v]" in Split:
            csv_name=csv_name+";v_"+row[3]
        if "[k]" in Split:
            csv_name=csv_name+";k_"+row[4]
        if "[nu]" in Split:
            csv_name=csv_name+";nu_"+row[5]
        if "[gamma]" in Split:
            csv_name=csv_name+";gamma_"+row[6]
        if "[permult]" in Split:
            csv_name=csv_name+";permult_"+row[7]
        if "[line]" in Split:
            csv_name=csv_name+";line_"+row[8]

        csv_zeile=""
        for j in range(9):
            csv_zeile=csv_zeile+row[j]+","
        csv_zeile=csv_zeile+str(taualpha)+","
        csv_zeile=csv_zeile+str(isglassy)+","
        csv_zeile=csv_zeile+str(len(tplot))

        with open(csv_name+csv_ext, "a") as f:
            f.write(csv_zeile+'\n')
            f.close()
            Zeilen=Zeilen+1


print("Written "+str(Zeilen)+" lines in "+csv_out+csv_ext)
print("Not-Glassy-Lines: "+str(noglassy))
print("CSV-Format: cc,rand,tau,v,k,nu,gamma,permult,line,AlphaRelaxationTime,IsGlassy,DataCount")

FileCount=0
for f in glob.glob(csv_out+"*"+csv_ext):
    FileCount=FileCount+1
if FileCount>1:
    print("Split in "+str(FileCount)+" files")

if Zeilen<1:
    sys.stderr.write("No lines in "+csv_out+csv_ext+"\n")
    Error=1
sys.exit(Error)
