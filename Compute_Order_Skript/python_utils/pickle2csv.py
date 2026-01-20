#!/usr/bin/env python3

import sys,os,glob
import pickle
import csv
import argparse

#------------------------

Split=""
#Split="[v],[nu]"

#-----------------------

parser=argparse.ArgumentParser(description="Create csv-file from pickle-files (CSV-Format: cc,rand,tau,v,k,nu,gamma,permult,line,Time,MSD,SelfInt,DataCount)",
                               usage='pickle2csv.py --dir "analyse/pickle" --csv "pickle_data.csv" --split "[cc],[rand],[tau]"')
parser.add_argument('--dir',type=str,default=os.path.join('analyse','pickle'),help='Pickle-directory')
parser.add_argument('--csv',type=str,default='pickle_data.csv',help='csv-file for output')
parser.add_argument('--split',type=str,default=None,help='Split csv-files via [cc], [rand], [tau], [v], [k], [nu], [gamma], [permult], [line]')
args=parser.parse_args()

dir_pickle=args.dir+os.sep
csv_out,csv_ext=os.path.splitext(args.csv)
Split=args.split or Split
Split=Split.strip()
if Split == "none":
    Split=""

print("Create "+csv_out+csv_ext+" ...")
if Split != '':
    print("Split via "+str(Split))

for f in glob.glob(csv_out+"*"+csv_ext):
    os.remove(f)

Zeilen=0
Error=0
with open(dir_pickle+"pickle.csv") as f:
    csv_data=csv.reader(f,delimiter=",")
    for row in csv_data:
        picklefile=dir_pickle+row[9]
        try:
            data=pickle.load(open(picklefile, "rb"))
            tplot=data['tplot']
            msd=data['msd']
            tval=data['tval']
            SelfInt=data['SelfInt']
            if len(tplot)!=len(msd) or len(tplot)!=len(tval) or len(tplot)!=len(SelfInt) or len(tplot)<2:
                sys.stderr.write(picklefile+"\n")
                sys.stderr.write("Len(tplot) , Len(msd) , Len(tval) , Len(SelfInt): "+str(len(tplot))+" , "+str(len(msd))+" , "+str(len(tval))+" , "+str(len(SelfInt))+"\n")
                sys.stderr.write("Error Data-Length\n")
                Error=1
                continue

        except:
            sys.stderr.write(picklefile+"\n")
            sys.stderr.write("Didn't get data\n")
            Error=1
            continue

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

        for i in range(len(tplot)):
            if tplot[i]!=tval[i]:
                sys.stderr.write(picklefile+"\n")
                sys.stderr.write("tplot!=tval\n")
                Error=1
                break

            csv_zeile=""
            for j in range(9):
                csv_zeile=csv_zeile+row[j]+","
            csv_zeile=csv_zeile+str(tval[i])+","
            csv_zeile=csv_zeile+str(msd[i])+","
            csv_zeile=csv_zeile+str(SelfInt[i])+","
            csv_zeile=csv_zeile+str(len(tplot))


            with open(csv_name+csv_ext, "a") as f:
                f.write(csv_zeile+'\n')
                f.close()
                Zeilen=Zeilen+1


print("CSV-Format: cc,rand,tau,v,k,nu,gamma,permult,line,Time,MSD,SelfInt,DataCount")
print("Written "+str(Zeilen)+" lines in "+csv_out+csv_ext)
FileCount=0
for f in glob.glob(csv_out+"*"+csv_ext):
    FileCount=FileCount+1
if FileCount>1:
    print("Split in "+str(FileCount)+" files")

if Zeilen<1:
    sys.stderr.write("No lines in "+csv_out+csv_ext+"\n")
    Error=1
sys.exit(Error)
