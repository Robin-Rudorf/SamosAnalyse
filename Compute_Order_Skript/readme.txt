Skripte
#######

Aufruf der Skripte: ./Skriptname

open_runs.sh
 - muss mit "chmod 0777 open_runs.sh" auf ausführbar gesetzt werden
 - Starter für die Samos-Runs
 - Parameter müssen in open_runs.config angepasst werden
 - sollte in einer screen-Session gestartet werden (Start mit ./start_screen.sh)

open_runs.config
 - Parameter-Datei für open_runs.sh

start_screen.sh
 - muss mit "chmod 0777 start_screen.sh" auf ausführbar gesetzt werden
 - startet das Skript open_runs.sh in einer screen-Session

start_screen_nice.sh
 - muss mit "chmod 0777 start_screen.sh" auf ausführbar gesetzt werden
 - für Server, auf denen mehrere User arbeiten
 - startet das Skript open_runs.sh in einer screen-Session mit maximaler niceness

restore_screen.sh
 - wird von start_screen.sh erstellt
 - Wiederherstellung der screen-Session nach Verbindungsabbruch

testparams.sh
 - muss mit "chmod 0777 testparams.sh" auf ausführbar gesetzt werden
 - Zeigt die konfigurierten Parameter in open_runs.config an

sort_plot.sh
 - muss mit "chmod 0777 sort_plot.sh" auf ausführbar gesetzt werden
 - splittet die Datei analyse/compute_order.csv und erzeugt die Diagramme
   im Ordner analyse
 - Parameter in der Datei müssen angepasst werden 

plot_time_series.py
 - muss mit "chmod 0777 plot_time_series.py" auf ausführbar gesetzt werden
 - Erzeugt die Time-Series-Diagramme im Ordner analyse/time_series

zip-runs.sh
 - muss mit "chmod 0777 zip-runs.sh" auf ausführbar gesetzt werden
 - Erzeugt zip-Dateien des aktuellen Ordners im übergeordneten Verzeichnis

zip-analyse.sh
 - muss mit "chmod 0777 zip-analyse.sh" auf ausführbar gesetzt werden
 - Erzeugt zip-Datei des aktuellen analyse-Ordners im übergeordneten Verzeichnis

pickle_csv_plot.sh
 - Erstellt Plots mittels der Pickle-Files

open_boundary_generic.conf
 - Samos Konfigurationsdatei (Vorlage)
 - @-Werte werden durch open_runs.sh ersetzt

python_utils.tar.gz
 - Enthält die benötigten Python-Skripte

Diese Skripte sollten nicht manuell aufgerufen werden:

python_utils/compute_order.py
 - wird von open_runs.sh aufgerufen
 - erzeugt analyse/compute_order.csv

python_utils/generate_avm_ic.py
 - wird von open_runs.sh aufgerufen
 - erzeugt Samos-Imput-Dateien

python_utils/save_time_series.py
 - wird von open_runs.sh aufgerufen
 - erzeugt csv-Dateien im Ordner analyse/time_series

python_utils/plot_runs.py
 - wird von sort_plot.sh aufgerufen
 - erzeugt Diagramm-Dateien im Ordner analyse


Verzeichnisse
#############

Alle Verzeichnisse werden beim Start von open_runs_cp_v3.sh erstellt.
Achtung beim Start von open_runs_cp_v3.sh werden sämtliche Ordner gelöscht und neu erstellt.

analyse
 - Enthält Log-Dateien und csv-Dateien

input
 - Enthält die Input-Dateien (Vorlagen) für die Samos-Runs

list
 - Enthält die Verzeichnis-Listen für die Samos-Runs

samos_runs
 - Enthält die Samos-Dateien


Log-Dateien
###########

Core_X.log
 - Fortschritts-Anzeige für die einzelnen Cores

Samos_Errors.txt
 - Enthält nur die Fehler der aufgerufenen Programme
 - für detailierte Fehlermedungen bitte in Samos_Log.txt nachschauen

Samos_Log.txt
 - kompletter Log der Runs

[Datum]_[Ordner]_zip im übergeordneten Verzeichnis
 - Log-Datei für zip-runs.sh
 - wird in [Datum]_[Ordner]_zip.Ok.log bzw. [Datum]_[Ordner]_zip.Error.log
   umbenannt, wenn zip-runs.sh fertig ist


Diverses
########

Offene screen-Sessions anzeigen:
screen -ls

Verbinden mit einer laufenden screen-Session:
screen -xr [Session-Name]

Alle screen-Sessions beenden:
pkill screen

Fortschritt für die anderen Cores anzeigen z.B. für Core 2:
tail -f analyse/Core_2.log

Erneuter Start der Runs nach Abbruch:
 -  Verzeichnis "samos_runs" löschen
