#!/bin/bash
## create_pickles.sh 
## Create pickles from samos runs
## Author: Thomas Rudorf
## thomasrudorf@gmx.de
## Date: 21.01.2025

## Dieses Skript muss sich in einem leeren Verzeichnis befinden!

# Topdir Samos-Runs
topdir_runs='../tom1'

# Pickle-Einstellungen
SelfIntLimit_pickles='0.5'
skip_pickles='500'

# Mail wenn fertig (nur relevant, wenn nicht in open_runs.config gesetzt) 
#fertig_mail=th-ru@gmx.de



###########################################################################
# Beende alle Unterprozesse bei Skript-Abbruch
trap "kill -9 -$$;exit" 1 2 3 15

clear
# data directory for input
topdir_runs="$(readlink -f "${topdir_runs}")"
# data directory for output
topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"

# Test auf screen-Session
if [ "$TERM" != "screen" ] && [ "$SSH_CONNECTION" != "" ];then
  echo Achtung!
  echo Das Skript wird nicht in einer Screen-Session ausgeführt.
  echo Dies führt zu einem Abbruch falls die SSH-Verbindung getrennt wird.
  echo
  echo Bitte das Skript mit \"./start_screen.sh\" starten
  echo um Abbrüche zu verhindern.
  echo
  read -t 60 -n1 -p "Soll das Skript trotzdem gestartet werden? (J/n) " Eingabe

  case "${Eingabe}" in
    "n"|"N")
     echo;exit
    ;;
  esac
  echo
fi


# python-utils Skripte
echo Entpacke python_utils.tar.gz
cp "${topdir_runs}/python_utils.tar.gz" "${topdir}"

tar xf python_utils.tar.gz
if [ $? -ne 0 ];then
  echo
  echo Fehler python_utils.tar.gz
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi
echo

if [ ! -f "${topdir_runs}/open_runs.config" ];then
  echo Datei open_runs.config nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

source "${topdir_runs}/open_runs.config"

skip=${skip_pickles}
SelfIntLimit=${SelfIntLimit_pickles}


# Start-Meldung
startmsg="Starte Create_Pickles"

if [ "${zip_runs}" == "1" ];then
  startmsg="${startmsg}, zip-runs.sh"
fi
echo "${startmsg}"
echo

# data directory for output
topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"

# Verzeichnisse löschen / erstellen und Variablen setzen
dir_analyse="${topdir}/analyse"
rm -r -f "${dir_analyse}" 2>/dev/null
mkdir "${dir_analyse}"

dir_pickle="${dir_analyse}/pickle"
rm -r -f "${dir_pickle}" 2>/dev/null
if [ "${create_pickle}" == "1" ];then
  mkdir "${dir_pickle}"
fi

dir_list="${topdir_runs}/list"

cpo_csv="${dir_analyse}/compute_order.csv"
samos_log="${dir_analyse}/Pickles_Log.txt"

python_utils="${topdir}/python_utils"

# Test, ob Dateien vorhanden

if [ ! -f "${dir_list}/all.txt" ];then
  echo Datei "${dir_list}/all.txt" nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

cp_err=0
if [ -f "${topdir_runs}/analyse/backup_compute_order.csv" ];then
  cp "${topdir_runs}/analyse/backup_compute_order.csv" "${cpo_csv}" ||cp_err=1
else
  cp "${topdir_runs}/analyse/compute_order.csv" "${cpo_csv}" ||cp_err=1
fi

cp "${topdir_runs}/sort_plot.sh" "${topdir}/" ||cp_err=1
cp "${topdir_runs}/sort_avg_plot.sh" "${topdir}/" ||cp_err=1

if [ ${cp_err} -ne 0 ];then
  echo
  echo Fehler beim Kopieren.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi


GesamtZeilen=0
while read -r z;do
   GesamtZeilen=$((${GesamtZeilen}+1))
done <"${dir_list}/all.txt"

# Start Analyse
echo
echo "Starte ${GesamtZeilen} Analyse-Runs auf ${CORES} CPU-Kernen ..."
echo "Verzeichnis: ${topdir}"
echo "Alles abbrechen mit Strg+C oder kill $$"
echo
echo "$(date)  Start Analyse-Runs">"${samos_log}"

# Erzeuge Child-Prozesse pro Core
for f in "${dir_list}"/Core_*.txt;do
  (
     GesamtZeilen=0
     while read -r z;do
       GesamtZeilen=$((${GesamtZeilen}+1))
     done<"${f}"

     Ausgabe=0
     if [ "$(basename "${f}")" == "Core_1.txt" ];then
       Ausgabe=1
     fi

     corelog="${dir_analyse}/$(basename "${f%.*}").log"

     Zeile=0
     while read -r z;do
       Zeile=$((${Zeile}+1))
       Param_Txt=$(echo "${z}"|sed "s|${topdir_runs}/samos_runs/||g"|sed "s|/|;|g")

       cd "${z}"
       echo "${Zeile}/${GesamtZeilen} $(date)  ${Param_Txt}">>"${corelog}"

       # Nur Ausgabe von Core1 auf Bildschirm
       if [ ${Ausgabe} -eq 1 ];then
         echo
         echo "${Zeile}/${GesamtZeilen} Core1 ${topdir}"
         echo "${Param_Txt}"
         echo "Starte Python Skripte ...">>"${corelog}"
         echo Starte Python Skripte ...
       else
         echo "Starte Python Skripte ...">>"${corelog}"
       fi

       PyErr=0
       pickle_input_file=$(basename $(find . -name "*.input"))
       pickle_log_file="${dir_pickle}/${Param_Txt}.log"
       python3 "${python_utils}/AnalyzeGlassy.py" -i "cell_000" -r "${pickle_input_file}" -c "${parfile}" -d "${z}/" -o "${dir_pickle}/" -s ${skip} -p ${Param_Txt} -u 2 --drift --getMSD --getSelfInt --ignore >"${pickle_log_file}" 2>&1
       if [ $? -ne 0 ];then
         PyErr=1
         echo "Error Python Pickle ${Param_Txt}">>"${dir_pickle}/${Param_Txt}.err"
       else
         echo "$(cat prefix.csv),${Param_Txt}.p">"${dir_pickle}/${Param_Txt}.csv"
       fi

       if [ ${PyErr} -ne 0 ];then
        echo>>"${corelog}"
        echo "Error Python-Skripts">>"${corelog}"
       fi

       echo>>"${corelog}"
       echo>>"${corelog}"

     done <"${f}"
     echo "$(date)  Fertig">>"${dir_analyse}/$(basename "${f%.*}").log"
     if [ ${Ausgabe} -eq 1 ];then
         echo
         echo "Warte auf die anderen Cores ..."
     fi
  ) &
done

wait

# Dateien zusammenfügen
while read -r z;do
  Param_Txt=$(echo "${z}"|sed "s|${topdir_runs}/samos_runs/||g"|sed "s|/|;|g")

  if [ -f "${dir_pickle}/${Param_Txt}.err" ];then
      cat "${dir_pickle}/${Param_Txt}.err">>"${samos_log}"
  fi

  if [ -f "${dir_pickle}/${Param_Txt}.csv" ];then
      cat "${dir_pickle}/${Param_Txt}.csv">>"${dir_pickle}/pickle.csv"
  fi


done <"${dir_list}/all.txt"


# Füge AlphaRelaxationTime in compute_order.csv ein
col_txt="cc,rand,tau,v,k,nu,gamma,permult,line,O_mean,O_var,frames_ok"

echo>>"${samos_log}"
echo "Berechne Alpha Relaxation Time">>"${samos_log}"
python3 "${python_utils}/pickle2csv_art.py" --dir "${dir_pickle}" --csv "${dir_analyse}/alpha_relaxation_time.csv" --selfint_limit "${SelfIntLimit}" >>"${samos_log}" 2>&1
python3 "${python_utils}/co_art_join.py" --csv1 "${cpo_csv}" --csv2 "${dir_analyse}/alpha_relaxation_time.csv" >>"${samos_log}" 2>&1
col_txt="${col_txt},alpha_relaxation_time,isglassy,datacount,minSelfInt"

echo "Cols:">"${cpo_csv}.cols.txt"
echo ${col_txt}>>"${cpo_csv}.cols.txt"

# Berechne Mittelwerte für random-input
if [ ${randomval} -gt 1 ];then
  echo>>"${samos_log}"
  echo "Berechne AVG">>"${samos_log}"
  python3 "${python_utils}/co_mean.py" --csv_in "${cpo_csv}" >>"${samos_log}" 2>&1
fi

echo>>"${samos_log}"
echo "$(date)  End Samos Runs">>"${samos_log}"
rm "${dir_analyse}"/Core_*.log

echo
echo Fertig.


## Externe Skripte starten
cd "${topdir}"

zip_runs_err=0
if [ "${zip_runs}" == "1" ];then
  touch "${dir_analyse}/Samos_Log.txt"
  echo
  echo Start zip-runs.sh
  "${topdir_runs}/zip-runs.sh" skriptstart analyse || zip_runs_err=1
  rm "${dir_analyse}/Samos_Log.txt"
fi

# Fehlerbehandlung

if [ ${zip_runs_err} -ne 0 ];then
  echo
  echo "Fehler zip-runs.sh"
fi

echo
if [ "${fertig_mail}" == "" ];then
  read -r -s -n1 -p "Fertig mit beliebiger Taste "
  echo
else
  ## Fertig-Mail
  (
    echo "$(date)  Pickle Runs fertig."
    echo
    echo "Computer: $(hostname -s)"
    echo "Run-Dir:  ${topdir}"

    if [ ${zip_runs_err} -ne 0 ];then
      echo
      echo "Fehler zip-runs.sh"
    fi

    echo
    cat ${samos_log}
  )| mail -s "$(hostname -s): Pickle Fertig." ${fertig_mail}
fi

if [ -f restore_screen.sh ];then
  rm restore_screen.sh
fi

