#!/bin/bash

## Output-csv-Datei: pickle_data*.csv
## Felder:  cc,rand,tau,v,k,nu,gamma,permult,line,AlphaRelaxationTime,IsGlassy,DataCount
## FeldNr:   1   2   3  4 5  6   7      8      9         10                 11     12

# Mögliche Spalten: cc rand tau v k nu gamma permult line

# csv/png Sortierung (Variable kann auch none sein oder mehrere Spalten enthalten.)
split='nu'

# Diagramm X-Achse
xcol='permult'

# Diagramm-Gruppierung bzw. y-Achse (Variable kann auch none sein.) 
group='v'

# SelfInt-Limit (Maximum)
SelfIntLimit='0.5'

# Diagramm Width
x_size='11'

# Diagramm Colormap
d_cmap='viridis_r'

# Color-Diagramm Width
color_x_size='11'
color_y_size='7'

# Color-Diagramm Scatter Point Size (0 = disable Scatter) 
color_scatter='5'

# Color-Diagramm Colormap
colormap='YlOrRd'

# Diagramm Style ( line , logx ,logxy )
style='line'

#################################################################################

# Verzeichnis in dem die Pickle-Files liegen (default in *.py: analyse/pickle)
pickle_dir='analyse/pickle'
# CSV-Datei (Endung muss .csv sein!)
csv_file='art_pickle_data.csv'
# Output-Dir
out_dir='analyse/pickle_plot'

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
python3 pickle2csv_art.py --csv "${out_dir}/${csv_file}" --split "${split_pl}" --selfint_limit="${SelfIntLimit}" ||Error=1
python3 plot_pickle_art.py --csv "${out_dir}/${csv_file}" --xcol="${xcol}" --group "${group}" --xsize "${x_size}" --title "${title}" --style "${style}" --cmap "${d_cmap}" ||Error=1
python3 plot_pickle_art_col.py --csv "${out_dir}/${csv_file}" --xcol="${xcol}" --ycol "${group}" --xsize "${color_x_size}" --ysize "${color_y_size}" --scatter "${color_scatter}" --colormap "${colormap}" --title "${title}" ||Error=1

if [ ${Error} -ne 0 ];then
  echo
  echo Achtung! Es sind Fehler aufgetreten.
fi

echo Output-Dir: ${out_dir}
echo
read -r -s -n1 -p "Fertig mit beliebiger Taste "
echo
