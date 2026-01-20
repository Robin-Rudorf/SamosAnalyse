#!/bin/bash

## csv-Datei: compute_order.csv
## Felder:  cc,rand,tau,v,k,nu,gamma,permult,line,O_mean,O_var,frames_ok
## FeldNr:   1   2   3  4 5  6   7      8      9     10    11      12

# Mögliche Spalten: cc rand tau v k nu gamma permult line
# csv/png Sortierung (Variable kann auch none sein oder mehrere Spalten enthalten.)
csv_sort='none'
# Diagramm-Gruppierung bzw. y-Achse (Variable kann auch none sein.)
group='permult'
# Diagramm X-Wert
xwert='tau'

# Diagramm Colormap (Variable kann auch none sein.)
d_cmap='viridis_r'
# Markersize
markersize='6'
# Diagramm Width
x_size='11'

# Color-Diagramm Width
color_x_size='11'
color_y_size='7'

# Color-Diagramm Scatter Point Size (0 = disable Scatter)
color_scatter='5'

# Color-Diagramm Colormap
colormap='YlOrRd'

# Verzeichnis in dem die CSV-Datei liegt
csv_dir='analyse'
# CSV-Datei (Endung muss .csv sein!)
csv_file='compute_order.csv'


#################################################################################
# FeldNr Funktion für awk
FieldNr() {
  local field_nr=0
  case "${1}" in
    cc)      field_nr=1;;
    rand)    field_nr=2;;
    tau)     field_nr=3;;
    v)       field_nr=4;; 
    k)       field_nr=5;;
    nu)      field_nr=6;;
    gamma)   field_nr=7;;
    permult) field_nr=8;;
    line)    field_nr=9;;
    *) ;;
  esac

  if [ ${field_nr} == 0 ];then
    echo 0
    return 1
  fi

  field_nr="\$${field_nr}"
  echo ${field_nr}
  return 0
}
##############################

if ! test -d ${csv_dir}
then
 echo ${csv_dir} not found.
 exit 1
fi

if [ "$3" != "" ];then
 xwert=$1
 group=$2
 csv_sort="$3"
fi

if [ "${csv_sort}" == "none" ];then csv_sort="";fi

#Basis-Verzeichnis-Name
Dir_Name="$(pwd | awk -F "/" '{ print $NF }')"

#Basis-CSV-Name
csv_basename=$(basename ${csv_file} .csv)

cd "${csv_dir}"

if ! test -f ${csv_file}
then
 echo ${csv_file} not found.
 exit 1
fi

rm ${csv_basename}_plot_*.csv >/dev/null 2>&1


while read -r f
do
  if [ -z "${f}" ];then continue;fi

  fn=${csv_basename}_plot

  if [ "${csv_sort}" != "" ]
  then
    for sort in ${csv_sort}
    do
      sort_nr=$(FieldNr ${sort})
      if [ "${sort_nr}" == "0" ];then
        echo Fehler Deklaration csv_sort.
        exit 1
      fi

      sort_var=$(echo ${f}|awk -F "," '{print '${sort_nr}'}')
      fn=${fn}_${sort}${sort_var}
    done
  else
    fn=${fn}_
  fi

  echo "${f}">>${fn}.csv
done<${csv_file}


plot_err=0
for filename in ${csv_basename}_plot_*.csv
do
  sort_name=$(basename ${filename} .csv|awk -F "${csv_basename}_plot_" '{print $2}')
  if [ "${sort_name}" == "" ];then
    output_prefix="${Dir_Name}_"
  else
    output_prefix="${Dir_Name}_${sort_name}_"
  fi

  python3 ../python_utils/plot_runs.py --csv ${filename} --output "${output_prefix}O_mean.png" --title "${Dir_Name} ${sort_name}" --x ${xwert} --y O_mean --group ${group} --xsize ${x_size} --cmap ${d_cmap} --ms ${markersize}|| plot_err=1
  python3 ../python_utils/color_plot_runs.py --csv ${filename} --output "${output_prefix}O_mean_col.png" --title "${Dir_Name} ${sort_name}" --xcol ${xwert} --wcol O_mean --ycol ${group} --xsize ${color_x_size} --ysize ${color_y_size} --colormap ${colormap} --scatter ${color_scatter} || plot_err=1

  if [ -f alpha_relaxation_time.csv ];then
    python3 ../python_utils/plot_runs.py --csv ${filename} --output "${output_prefix}ART.png" --title "${Dir_Name} ${sort_name}" --x ${xwert} --y art --group ${group} --xsize ${x_size} --cmap ${d_cmap} --ms ${markersize}|| plot_err=1
    python3 ../python_utils/color_plot_runs.py --csv ${filename} --output "${output_prefix}ART_col.png" --title "${Dir_Name} ${sort_name}" --xcol ${xwert} --wcol art --ycol ${group} --xsize ${color_x_size} --ysize ${color_y_size} --colormap ${colormap} --scatter ${color_scatter} --log 1|| plot_err=1
  fi

done

exit ${plot_err}
