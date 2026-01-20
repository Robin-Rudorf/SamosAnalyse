#!/bin/bash

zip_prog="7z"
zip_pack_param="a -tzip -mx=5 -bsp1 -bso0 -bse2"
zip_test_param="t -bsp1 -bso0 -bse2"

clear

# Dirs

topdir="$(readlink -f "$0")"
topdir="$(dirname "${topdir}")"
samos_dir="$(pwd|awk -F "/" '{print $NF}')"


echo Packe Ordner ${samos_dir}/analyse

which ${zip_prog} >/dev/null 2>&1
if [ $? -ne 0 ];then
  echo Zip-Programm ${zip_prog} nicht gefunden.
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit 1
fi

if [ ! -d "${topdir}/analyse" ];then
  echo Ordner analyse nicht gefunden.
  read -r -s -n1 -p "Beenden mit beliebiger Taste "
  echo
  exit 1
fi

zip_pack="${zip_prog} ${zip_pack_param}"
zip_test="${zip_prog} ${zip_test_param}"
zip_datum=$(date +'%Y-%m-%d_%H%M%S')
zip_path="$(realpath ..)"
zip_name="${zip_path}/${zip_datum}_${samos_dir}_analyse.zip"

ziperr=0

echo
echo "Erzeuge ${zip_name}"
rm -f "${zip_name}" >/dev/null 2>&1
${zip_pack} "${zip_name}" "${topdir}/analyse" ||ziperr=1
echo
echo "Teste ${zip_name}"
${zip_test} "${zip_name}" ||ziperr=1
echo

if [ ${ziperr} -ne 0 ];then
  echo "Achtung! Es sind Fehler aufgetreten."
  rm -f "${zip_name}" >/dev/null 2>&1
else
  echo "Fertig."
fi
echo
read -r -s -n1 -p "Fertig mit beliebiger Taste "
echo
exit 0
