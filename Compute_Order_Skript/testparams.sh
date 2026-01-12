#!/bin/bash
## Parameter-Test for open_runs.config
## Author: Thomas Rudorf
## thomasrudorf@gmx.de
## Date: 31.12.2025

clear
if [ ! -f open_runs.config ];then
  echo Datei open_runs.config nicht gefunden.
  echo
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

source open_runs.config

which bc >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo bc NOT FOUND!
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

which samos >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo samos NOT FOUND!
fi

which 7z >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo 7z NOT FOUND!
fi

topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"
echo "Data directory: ${topdir}"


# Tau-Variable erstellen
if [ "" == "${tauval}" ];then
  while [ "$(echo "${tau_start} <= ${tau_end}"|bc -l)" == "1" ];do
    taustr=$(echo print\(${tau_start}\)|python3)
    tauval="${tauval} ${taustr}"
    tau_start=$(echo "${tau_start}+${tau_increment}"|bc -l)
  done
fi

Runs=1
x=0;for i in ${cellcountval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
Runs=$(( ${Runs} * ${randomval}))
x=0;for i in ${tauval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${gamval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${nuval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${kval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${permult};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${lineval};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))
x=0;for i in ${v0val};do x=$(( ${x} + 1));done
Runs=$(( ${Runs} * ${x}))

if [ "${del_samos_data}" == "1" ];then
  echo "Delete Samos Data:       '1'"
else
  echo "Delete Samos Data:       '0'"
fi

if [ "${create_timeseries}" == "1" ];then
  echo "Create Timeseries:       '1'"
else
  echo "Create Timeseries:       '0'"
fi

if [ "${create_pickle}" == "1" ];then
  echo "Create Pickle-Files:     '1'"
else
  echo "Create Pickle-Files:     '0'"
fi

if [ "${plot_time_series}" == "1" ]  && [ "${create_timeseries}" == "1" ];then
  echo "Run plot_time_series.py: '1'"
else
  echo "Run plot_time_series.py: '0'"
fi

if [ "${zip_runs}" == "1" ];then
  if [ "${del_samos_data}" == "1" ];then
    echo "Run zip-runs.sh          '1' (analyse only)"
  else
    echo "Run zip-runs.sh          '1'"
  fi
else
  echo "Run zip-runs.sh          '0'"
fi

if [ "${sort_plot}" == "1" ];then
  echo "Run sort_plot.sh:        '1'"
  echo "Sortierung:              '${sort_plot_csv_sort}'"
  echo "Gruppierung:             '${sort_plot_group}'"
  echo "X-Wert:                  '${sort_plot_xwert}'"
else
  echo "Run sort_plot.sh:        '0'"
fi

echo
echo "Parameter-File:        '${parfile}'"
echo "Cores:                 '${CORES}'"

if [ "${infile}" != "" ];then
  cellcountval=1
  randomval=1
fi

if [ "${infile}" != "" ];then
  echo "Infile:                '${infile}'"
  echo "Infile_Bound:          '${infile_bound}'"
else
  echo "Cell Count:            '${cellcountval}'"
  echo "Random Cells:          '${randomval}'"
fi

echo "Alignment (Tau):       '$(echo ${tauval})'"
echo "Gamma:                 '${gamval}'"
echo "Noise Level:           '${nuval}'"
echo "VP Federstärke (k):    '${kval}'"
echo "Permult:               '${permult}'"
echo "Line tension:          '${lineval}'"
echo "Driving velocity (v0): '${v0val}'"
echo "Transl.-Abzug:         '${modval}'"
echo "Runtime:               '${trun}'"
echo "Skip for Pickles:      '${skip}' ($((${skip}*${freq})))"
echo "Skip for C-Order:      '${skip_cpo}' ($((${skip_cpo}*${freq})))"
echo "Frequenz:              '${freq}'"
echo
if [ "${fertig_mail}" != "" ];then
  echo "Mail wenn fertig: ${fertig_mail}"
else
  echo "Mail wenn fertig: no mail"
fi
echo "Configured Runs: ${Runs}"
echo
read -r -s -n1 -p "Fertig mit beliebiger Taste "
echo




