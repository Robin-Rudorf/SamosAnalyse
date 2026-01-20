#!/bin/bash
## open_runs.sh 
## The following are all the runs performed for open boundaries.
## WARNING! This script will generate a lot of output data.
## need open_runs.config for configuration

## Author: Thomas Rudorf
## thomasrudorf@gmx.de
## Date: 18.01.2025

## csv-Datei-Format (compute-order):  cc,rand,tau,v,k,nu,gamma,permult,line,O_mean,O_var,frames_ok

# Test, ob Dateien und Programme vorhanden
if [ ! -f open_runs.config ];then
  echo Datei open_runs.config nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

which samos >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo Programm samos nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

which bc >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo Programm bc nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi


source open_runs.config

###########################################################################
# Beende alle Unterprozesse bei Skript-Abbruch
trap "kill -9 -$$;exit" 1 2 3 15

clear

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

# Start-Meldung
startmsg="Starte Samos-Runs"
if [ "${sort_plot}" == "1" ];then
  startmsg="${startmsg}, sort_plot.sh"
fi
if [ "${plot_time_series}" == "1" ]  && [ "${create_timeseries}" == "1" ];then
  startmsg="${startmsg}, plot_time_series.py"
fi
if [ "${zip_runs}" == "1" ];then
  startmsg="${startmsg}, zip-runs.sh"
fi
echo "${startmsg}"

if [ "${del_samos_data}" == "1" ];then
  echo Lösche Samos-Daten = 1
else
  echo Lösche Samos-Daten = 0
fi

if [ "${create_timeseries}" == "1" ];then
  echo Erstelle Timeseries-Files = 1
else
  echo Erstelle Timeseries-Files = 0
fi

if [ "${create_pickle}" == "1" ];then
  echo Erstelle Pickle-Files = 1
else
  echo Erstelle Pickle-Files = 0
fi

echo

# python-utils Skripte
echo Entpacke python_utils.tar.gz
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

# data directory for output
topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"

# Beenden, falls Skript schon in diesem Ordner gestartet wurde
if [ -d "${topdir}/samos_runs" ];then
  echo Verzeichnis samos_runs existiert bereits.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

# Verzeichnisse löschen / erstellen und Variablen setzen
dir_analyse="${topdir}/analyse"
rm -r -f "${dir_analyse}" 2>/dev/null
mkdir "${dir_analyse}"

dir_timeseries="${dir_analyse}/time_series"
rm -r -f "${dir_timeseries}" 2>/dev/null
if [ "${create_timeseries}" == "1" ];then
  mkdir "${dir_timeseries}"
fi

dir_pickle="${dir_analyse}/pickle"
rm -r -f "${dir_pickle}" 2>/dev/null
if [ "${create_pickle}" == "1" ];then
  mkdir "${dir_pickle}"
fi

dir_list="${topdir}/list"
rm -r -f "${dir_list}" 2>/dev/null
mkdir "${dir_list}"

dir_input="${topdir}/input"
rm -r -f "${dir_input}" 2>/dev/null
mkdir "${dir_input}"

cpo_csv="${dir_analyse}/compute_order.csv"
samos_err="${dir_analyse}/Samos_Errors.txt"
samos_log="${dir_analyse}/Samos_Log.txt"

python_utils="${topdir}/python_utils"

# Test, ob Dateien vorhanden
if [ ! -f "${topdir}/${parfile}" ];then
  echo Datei ${parfile} nicht gefunden.
  echo
  read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

if [ ! -z ${infile} ];then
  if [ ! -f "${topdir}/${infile}" ];then
    echo Datei ${infile} nicht gefunden.
    echo
    read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
    echo
    exit
  fi

  if [ ! -f "${topdir}/${infile_bound}" ];then
    echo Datei ${infile_bound} nicht gefunden.
    echo
    read -t 60 -r -s -n1 -p "Beenden mit beliebiger Taste "
    echo
    exit
  fi
fi

# Config-Files sichern
cp "${topdir}/${parfile}" "${dir_analyse}/"
cp "${topdir}/open_runs.config" "${dir_analyse}/"

echo Erstelle Verzeichnisse ...

# Tau-Variable erstellen
if [ "" == "${tauval}" ];then
  while [ "$(echo "${tau_start} <= ${tau_end}"|bc -l)" == "1" ];do
    taustr=$(echo print\(${tau_start}\)|python3)
    tauval="${tauval} ${taustr}"
    tau_start=$(echo "${tau_start}+${tau_increment}"|bc -l)
  done
  echo Tau: ${tauval}
fi

# Wenn infile angegeben: Benutze angegebene Infiles
if [ ! -z ${infile} ];then
  cellcountval='0'
  randomval=1
  cp "${topdir}/${infile}" "${dir_input}/0.1.input"
  cp "${topdir}/${infile_bound}" "${dir_input}/0.1.boundary"
fi


# Run-Verzeichnisse erstellen und Konfig-Datei kopieren incl. Ersetzungen
random=0
while [ ${random} -lt ${randomval} ]
do
  random=$((random+1))

  for cellcount in ${cellcountval}
  do
    if [ ! -f "${dir_input}/0.1.input" ];then
      sleep 0.1 # for random via time
      python3 "${python_utils}/generate_avm_ic.py" ${cellcount} -o "${dir_input}/${cellcount}.${random}"
    fi
    infile="${cellcount}.${random}.input"
    infile_bound="${cellcount}.${random}.boundary"

    for tau in ${tauval}
    do
      for v in ${v0val}
      do
        for k in ${kval}
        do
          for nu in ${nuval}
          do
            for gamma in ${gamval}
            do
              for pm in ${permult}
              do
                for line in ${lineval}
                do
                  confdir="${topdir}/samos_runs/cc_${cellcount}/rand_${random}/tau_${tau}/v0_${v}/k_${k}/nu_${nu}/gamma_${gamma}/permult_${pm}/line_${line}"
                  mkdir -p "${confdir}"

                  lambda=$(echo "-2*${pm}*${gamma}" | bc -l)
                  # Use our position and boundary input files
                  cp "${dir_input}/${infile}" "${confdir}/${infile}"
                  cp "${dir_input}/${infile_bound}" "${confdir}/${infile_bound}"
                  newparfile="${confdir}/${parfile}"
                  cp "${topdir}/${parfile}" "${newparfile}"

                  # sed patterns for the input variables.
                  sed -i "s|@TAU@|${tau}|g" "${newparfile}"
                  sed -i "s|@V0@|${v}|g" "${newparfile}"
                  sed -i "s|@K@|${k}|g" "${newparfile}"
                  sed -i "s|@NU@|${nu}|g" "${newparfile}"
                  sed -i "s|@GAMMA@|${gamma}|g" "${newparfile}"
                  sed -i "s|@LAMBDA@|${lambda}|g" "${newparfile}"
                  sed -i "s|@LINE@|${line}|g" "${newparfile}"
                  sed -i "s|@INFILE@|${infile}|g" "${newparfile}"
                  sed -i "s|@INFILE_BOUND@|${infile_bound}|g" "${newparfile}"
                  sed -i "s|@TRUN@|${trun}|g" "${newparfile}"
                  sed -i "s|@FREQ@|${freq}|g" "${newparfile}"

                  # Schreibe erstellte Verzeichnisse in Liste
                  echo "${confdir}">>"${dir_list}/all.txt"
                  # Prefix-File for compute-order.py
                  echo "${cellcount},${random},${tau},${v},${k},${nu},${gamma},${pm},${line}">"${confdir}/prefix.csv"
                  touch "${confdir}/samos.err"
                done
              done
            done
          done
        done
      done
    done
  done
done


# Aufteilung auf die Kerne
GesamtZeilen=0
CoreNr=1
while read -r z;do
   if [ ${CoreNr} -gt ${CORES} ];then CoreNr=1;fi
   echo "${z}">>"${dir_list}/Core_${CoreNr}.txt"
   CoreNr=$((${CoreNr}+1))
   GesamtZeilen=$((${GesamtZeilen}+1))
done <"${dir_list}/all.txt"

# Start Samos
echo
echo "Starte ${GesamtZeilen} Samos-Runs auf ${CORES} CPU-Kernen ..."
echo "Verzeichnis: ${topdir}"
echo "Alles abbrechen mit Strg+C oder kill $$"
echo
echo "$(date)  Start Samos Runs">"${samos_log}"
echo>>"${samos_log}"
echo "$(date)  Start Samos Runs">"${samos_err}"
echo "Errors:">>"${samos_err}"
echo>>"${samos_err}"

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
       Param_Txt=$(echo "${z}"|sed "s|${topdir}/samos_runs/||g"|sed "s|/|;|g")

       cd "${z}"
       echo "${Zeile}/${GesamtZeilen} $(date)  ${Param_Txt}">>"${corelog}"
       echo "$(date)  ${Param_Txt}">samos.log

       # Nur Ausgabe von Core1 auf Bildschirm
       if [ ${Ausgabe} -eq 1 ];then
         echo
         echo "${Zeile}/${GesamtZeilen} Core1 ${topdir}"
         echo "Samos ${Param_Txt}"
         (samos "${parfile}" 2>&1||echo "Samos ${Param_Txt}">>samos.err)|tee -a samos.log "${corelog}"
         echo "Starte Python Skripte ...">>"${corelog}"
         echo Starte Python Skripte ...
       else
         ((samos "${parfile}" 2>&1||echo "Samos ${Param_Txt}">>samos.err)|tee -a samos.log "${corelog}") >/dev/null 2>&1
         echo "Starte Python Skripte ...">>"${corelog}"
       fi
       echo>>samos.log

       PyErr=0

       python3 "${python_utils}/compute_order.py" "${z}" ${skip_cpo} ${modval} $(cat prefix.csv) cpo.csv >>samos.log 2>&1
       if [ $? -ne 0 ];then
         PyErr=1
         echo "Python ComputeOrder ${Param_Txt}">>samos.err
       fi
       echo>>samos.log

       if [ "${create_timeseries}" == "1" ];then
         python3 "${python_utils}/save_time_series.py" --rundir "${z}" --outfile "${dir_timeseries}/${Param_Txt}.csv" >>samos.log 2>&1
         if [ $? -ne 0 ];then
           PyErr=1
           echo "Python TimeSeries ${Param_Txt}">>samos.err
         fi
         echo>>samos.log
       fi

       if [ "${create_pickle}" == "1" ];then
         pickle_input_file=$(basename $(find . -name "*.input"))
         pickle_log_file="${dir_pickle}/${Param_Txt}.log"
         echo "Start AnalyzeGlassy.py">>samos.log
         python3 "${python_utils}/AnalyzeGlassy.py" -i "cell_000" -r "${pickle_input_file}" -c "${parfile}" -d "${z}/" -o "${dir_pickle}/" -s ${skip} -p ${Param_Txt} -u 2 --drift --getMSD --getSelfInt --ignore >"${pickle_log_file}" 2>&1
         if [ $? -ne 0 ];then
           PyErr=1
           echo "Error AnalyzeGlassy.py">>samos.log
           echo "View ${pickle_log_file}">>samos.log
           echo "Python Pickle ${Param_Txt}">>samos.err
         else
           echo "$(cat prefix.csv),${Param_Txt}.p">pickle.csv
         fi
       fi

       if [ ${PyErr} -ne 0 ];then
        echo>>"${corelog}"
        echo "Error Python-Skripts">>"${corelog}"
       fi

       echo>>"${corelog}"
       echo>>"${corelog}"
       echo>>samos.log
       echo>>samos.log

       if [ "${del_samos_data}" == "1" ];then
         rm *.vtp
         rm *.dat
         rm *.fc
       fi
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
  cat "${z}/samos.log">>"${samos_log}"
  cat "${z}/samos.err">>"${samos_err}"

  if [ -f "${z}/cpo.csv" ];then
    cat "${z}/cpo.csv">>"${cpo_csv}"
  fi

  if [ "${create_pickle}" == "1" ];then
    if [ -f "${z}/pickle.csv" ];then
      cat "${z}/pickle.csv">>"${dir_pickle}/pickle.csv"
    fi
  fi

done <"${dir_list}/all.txt"


# Füge AlphaRelaxationTime in compute_order.csv ein
col_txt="cc,rand,tau,v,k,nu,gamma,permult,line,O_mean,O_var,frames_ok"

if [ "${create_pickle}" == "1" ];then
  echo>>"${samos_log}"
  echo "Berechne Alpha Relaxation Time">>"${samos_log}"
  python3 "${python_utils}/pickle2csv_art.py" --dir "${dir_pickle}" --csv "${dir_analyse}/alpha_relaxation_time.csv" --selfint_limit "${SelfIntLimit}" >>"${samos_log}" 2>&1
  python3 "${python_utils}/co_art_join.py" --csv1 "${cpo_csv}" --csv2 "${dir_analyse}/alpha_relaxation_time.csv" >>"${samos_log}" 2>&1
  col_txt="${col_txt},alpha_relaxation_time,isglassy,datacount,minSelfInt"
fi

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
echo>>"${samos_err}"
echo "$(date)  End Samos Runs">>"${samos_err}"
rm "${dir_analyse}"/Core_*.log

echo
echo Fertig.


## Externe Skripte starten
cd "${topdir}"

sort_plot_err=0
if [ "${sort_plot}" == "1" ];then
  echo
  echo Start sort_plot.sh
  ./sort_plot.sh ${sort_plot_xwert} ${sort_plot_group} "${sort_plot_csv_sort}" || sort_plot_err=1
fi

plot_time_series_err=0
if [ "${plot_time_series}" == "1" ] && [ "${create_timeseries}" == "1" ];then
  echo
  echo Start plot_time_series.py
  python3 ./plot_time_series.py || plot_time_series_err=1
fi

zip_runs_err=0
if [ "${zip_runs}" == "1" ];then
  echo
  echo Start zip-runs.sh

  if [ "${del_samos_data}" == "1" ];then
    ./zip-runs.sh skriptstart analyse || zip_runs_err=1
  else
    ./zip-runs.sh skriptstart || zip_runs_err=1
  fi
fi


# Fehlerbehandlung
ErrZeilen=0
while read -r z;do
  if [ $(echo ${z}|grep -c Samos) -eq 0 ];then continue;fi
  ErrZeilen=$((${ErrZeilen}+1))
done<"${samos_err}"
if [ ${ErrZeilen} -ne 2 ];then
  echo
  echo "Es sind $((${ErrZeilen}-2)) Samos-Fehler aufgetreten."
  echo "Siehe    ${samos_err}"
  echo "Details: ${samos_log}"
fi

if [ ${sort_plot_err} -ne 0 ];then
  echo
  echo "Fehler sort_plot.sh"
fi

if [ ${plot_time_series_err} -ne 0 ];then
  echo
  echo "Fehler plot_time_series.py"
fi

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
    echo "$(date)  Samos Runs fertig."
    echo
    echo "Computer: $(hostname -s)"
    echo "Run-Dir:  ${topdir}"

    if [ ${sort_plot_err} -ne 0 ];then
      echo
      echo "Fehler sort_plot.sh"
    fi

    if [ ${plot_time_series_err} -ne 0 ];then
      echo
      echo "Fehler plot_time_series.py"
    fi

    if [ ${zip_runs_err} -ne 0 ];then
      echo
      echo "Fehler zip-runs.sh"
    fi

    if [ ${ErrZeilen} -ne 2 ];then
      echo
      echo "Es sind $((${ErrZeilen}-2)) Samos-Fehler aufgetreten."
    fi

    echo
    cat ${samos_err}
    echo
    echo "Details: ${samos_log}"
  )| mail -s "$(hostname -s): Samos Fertig." ${fertig_mail}
fi

if [ -f restore_screen.sh ];then
  rm restore_screen.sh
fi