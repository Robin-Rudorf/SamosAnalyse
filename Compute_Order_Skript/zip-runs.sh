#!/bin/bash

zip_prog="7z"
zip_pack_param="a -tzip -mx=1 -bsp1 -bso2 -bse2"
zip_test_param="t -bsp1 -bso2 -bse2"

#-------------

standalone=1
if [ "$1" == "skriptstart" ];then
  standalone=0
fi

analyse_only=0
if [ "$2" == "analyse" ];then
  analyse_only=1
fi



if [ ${standalone} -eq 1 ] && [ "${TERM}" != "screen" ] && [ "${SSH_CONNECTION}" != "" ];then
  sc_name=zip_$(pwd|awk -F "/" '{print $NF}')_$(date +%Y%m%d_%H%M%S)
  screen -dmS "${sc_name}" "./${0}"
  screen -xr "${sc_name}"
  exit
fi

if [ ${standalone} -eq 1 ];then clear;fi

# Dirs

topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"
samos_dir="$(pwd|awk -F "/" '{print $NF}')"


echo Packe Ordner ${samos_dir}

which ${zip_prog} >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo Zip-Programm ${zip_prog} nicht gefunden.
  if [ ${standalone} -eq 1 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste ";fi
  echo
  exit 1
fi

zip_pack="${zip_prog} ${zip_pack_param}"
zip_test="${zip_prog} ${zip_test_param}"


if [ ${analyse_only} -eq 0 ];then
  # Vorhandener Speicherplatz
  echo Berechne freien Speicherplatz ...
  free_space=$(df --output=avail "${topdir}"|tail -n1)
  dir_size=$(du -s "${topdir}"|awk '{print $1}')
  use_size=$((${dir_size}/2))

  echo Freier Speicherplatz: $(numfmt --to=iec --from-unit=1024 ${free_space})
  echo Größe ${samos_dir}: $(numfmt --to=iec --from-unit=1024 ${dir_size})
  echo Benötigter Speicherplatz: $(numfmt --to=iec --from-unit=1024 ${use_size})
  echo

  if [ ${dir_size} -gt ${free_space} ];then
    echo Nicht genügend freier Speicherplatz vorhanden.
    if [ ${standalone} -eq 1 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste ";fi
    echo
    exit 1
  fi
fi


if [ ! -f analyse/Samos_Log.txt ];then
  echo analyse/Samos_Log.txt existiert nicht.
  if [ ${standalone} -eq 1 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste ";fi
  echo
  exit 1
fi

zip_datum=$(ls -l --time-style=+'%Y-%m-%d_%H%M%S' analyse/Samos_Log.txt|awk '{i=NF-1;print $i}')
zip_path="$(realpath ..)"
zip_name1="${zip_path}/${zip_datum}_${samos_dir}_analyse.zip"
zip_name2="${zip_path}/${zip_datum}_${samos_dir}_full.zip"
log="${zip_path}/${zip_datum}_${samos_dir}_zip"

if [ -f "${zip_name1}" ];then
  echo ${zip_name1} existiert bereits.
  if [ ${standalone} -eq 1 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste ";fi
  echo
  exit 1
fi

if [ -f "${zip_name2}" ];then
  echo ${zip_name2} existiert bereits.
  if [ ${standalone} -eq 1 ];then read -r -s -n1 -p "Beenden mit beliebiger Taste ";fi
  echo
  exit 1
fi

echo "Zip-Log  $(date)">"${log}"

ziperr=0

echo "Erzeuge ${zip_name1}"
echo>>"${log}"
echo "Erzeuge ${zip_name1}">>"${log}"
${zip_pack} "${zip_name1}" "${topdir}/analyse" 2>>"${log}"
if [ $? -ne 0 ];then ziperr=1;fi

echo
echo "Teste ${zip_name1}"
echo>>"${log}"
echo>>"${log}"
echo "Teste ${zip_name1}">>"${log}"
${zip_test} "${zip_name1}" 2>>"${log}"
if [ $? -ne 0 ];then ziperr=1;fi

if [ ${analyse_only} -eq 0 ];then
  echo
  echo "Erzeuge ${zip_name2}"
  echo>>"${log}"
  echo>>"${log}"
  echo "Erzeuge ${zip_name2}">>"${log}"
  ${zip_pack} "${zip_name2}" "${topdir}" 2>>"${log}"
  if [ $? -ne 0 ];then ziperr=1;fi

  echo
  echo "Teste ${zip_name2}"
  echo>>"${log}"
  echo>>"${log}"
  echo "Teste ${zip_name2}">>"${log}"
  ${zip_test} "${zip_name2}" 2>>"${log}"
  if [ $? -ne 0 ];then ziperr=1;fi
fi

echo
echo>>"${log}"
echo>>"${log}"
echo "Ende  $(date)">>"${log}"
if [ ${ziperr} -ne 0 ];then
  echo "Achtung! Es sind Fehler aufgetreten.">>"${log}"
  echo "Achtung! Es sind Fehler aufgetreten."
  echo "Siehe ${log}"
  rm -f "${zip_name1}" >/dev/null 2>&1
  rm -f "${zip_name2}" >/dev/null 2>&1
  mv -f "${log}" "${log}.Error.log"
  exit 1
else
  echo "Fertig.">>"${log}"
  echo "Fertig."
  mv -f "${log}" "${log}.Ok.log"
fi
exit 0
