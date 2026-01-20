#!/usr/bin/env bash
# Start open_runs.sh in a screen-session with maximum nice
# Author: Thomas Rudorf
# thomasrudorf@gmx.de
# Date 27.12.2025

bashscript=open_runs.sh

if [ "${TERM}" == "screen" ];then
  echo Sie befinden sich bereits in einer screen-Session.
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit
fi

if [ -f restore_screen.sh ];then
  run_screens="$(screen -ls)"
  old_sc_name="$(grep -F "#sc_name=" restore_screen.sh|sed 's|#sc_name=||g')"
  sc_count=$(echo ${run_screens}|grep -c -F "${old_sc_name}")

  if [ ${sc_count} -ne 0 ];then
    echo Es existiert noch eine laufende screen-Session,
    echo die aus dem aktuellen Ordner gestartet wurde.
    echo Es wird keine neue screen-Session gestartet.
    read -r -s -n1 -p "Beenden mit beliebiger Taste "
    echo
    exit
  fi
fi

sc_name=samos_$(pwd|awk -F "/" '{print $NF}')_$(date +%Y%m%d_%H%M%S)
echo "#!/bin/bash">restore_screen.sh
echo "#sc_name=${sc_name}">>restore_screen.sh
echo "screen -xr \"${sc_name}\"">>restore_screen.sh
echo 'if [ $? -ne 0 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste "'>>restore_screen.sh
echo 'echo;fi'>>restore_screen.sh

chmod 0755 restore_screen.sh
screen -dmS "${sc_name}" nice -n 19 ./${bashscript}
sleep 1
screen -xr "${sc_name}"
