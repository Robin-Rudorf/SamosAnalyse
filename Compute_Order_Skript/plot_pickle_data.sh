#!/bin/bash

## Output-csv-Datei: pickle_data*.csv
## Felder:  cc,rand,tau,v,k,nu,gamma,permult,line,time,MSD,SelfInt,DataCount
## FeldNr:   1   2   3  4 5  6   7      8      9     10 11      12        13

# Mögliche Spalten: cc rand tau v k nu gamma permult line

# csv/png Sortierung (Variable kann auch none sein oder mehrere Spalten enthalten.)
split='line permult'

# Diagramm-Gruppierung (Variable kann auch none sein.)
group=tau

# Diagramm Width
x_size=11

# Diagramm Style ( line , logx ,logxy )
style_MSD='logxy'
style_SelfInt='logx'

# Colormap (Variable kann auch none sein.)
colormap='viridis_r'

#################################################################################

# Verzeichnis in dem die Pickle-Files liegen (default in *.py: analyse/pickle)
pickle_dir="analyse/pickle"
# CSV-Datei (Endung muss .csv sein!)
csv_file="pickle_data.csv"
# Output-Dir
out_dir="analyse/pickle_plot"

if [ ! -d "${pickle_dir}" ];then
  echo "${pickle_dir} existiert nicht."
  echo
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit 1
fi

if [ ! -d "${out_dir}" ];then
  mkdir ${out_dir} 
  if [ $? -ne 0 ];then
    echo "Error mkdir ${out_dir}"
    echo
    read -r -s -n1 -p "Beenden mit beliebiger Taste "
    echo
    exit 1
  fi
fi

#Title-Prefix
title="$(pwd | awk -F "/" '{ print $NF }')"

# Split

split_pl=""
for sp in ${split};do
  split_pl="${split_pl}[${sp}] "
done

Error=0
python3 python_utils/pickle2csv.py --csv "${out_dir}/${csv_file}" --dir ${pickle_dir} --split "${split_pl}" ||Error=1
python3 python_utils/plot_pickle_data.py --csv "${out_dir}/${csv_file}" --group "${group}" --xsize "${x_size}" --title "${title}" --style_msd "${style_MSD}" --style_selfint ${style_SelfInt} --cmap ${colormap} ||Error=1

if [ ${Error} -ne 0 ];then
  echo
  echo Achtung! Es sind Fehler aufgetreten.
fi

echo Output-Dir: ${out_dir}
echo
read -r -s -n1 -p "Fertig mit beliebiger Taste "
echo
