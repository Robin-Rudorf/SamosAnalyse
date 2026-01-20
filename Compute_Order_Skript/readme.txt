Skripte
#######

Aufruf der Skripte: ./Skriptname

Berechtigungen setzen:
chmod 0755 *.sh
chmod 0755 *.py


open_runs.sh
 - Starter für die Samos-Runs
 - Parameter müssen in open_runs.config angepasst werden
 - sollte in einer screen-Session gestartet werden (Start mit ./start_screen.sh)

open_runs.config
 - Parameter-Datei für open_runs.sh

start_screen.sh
 - startet das Skript open_runs.sh in einer screen-Session

start_screen_nice.sh
 - für Server, auf denen mehrere User arbeiten
 - startet das Skript open_runs.sh in einer screen-Session mit maximaler niceness

restore_screen.sh
 - wird von start_screen.sh erstellt
 - Wiederherstellung der screen-Session nach Verbindungsabbruch

testparams.sh
 - Zeigt die konfigurierten Parameter in open_runs.config an

sort_plot.sh
 - splittet die Datei analyse/compute_order.csv und erzeugt die Diagramme
   im Ordner analyse
 - Parameter in der Datei müssen angepasst werden 

plot_time_series.py
 - Erzeugt die Time-Series-Diagramme im Ordner analyse/time_series

plot_pickle_data.sh
 - erzeugt MSD und SelfInt CSVs und PNGs aus den Pickle-Files
 - muss vor Start angepasst werden

zip-runs.sh
 - Erzeugt zip-Dateien des aktuellen Ordners im übergeordneten Verzeichnis

zip-analyse.sh
 - Erzeugt zip-Datei des aktuellen analyse-Ordners im übergeordneten Verzeichnis

open_boundary_generic.conf
 - Samos Konfigurationsdatei (Vorlage)
 - @-Werte werden durch open_runs.sh ersetzt

python_utils.tar.gz
 - Enthält die benötigten Python-Skripte


Diese Skripte sollten nicht manuell aufgerufen werden bzw. müssen vorher angepasst werden:

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

python_utils/color_plot_runs.py
 - wird von sort_plot.sh aufgerufen
 - erzeugt Color-Balken-Diagramme im Ordner analyse

python_utils/pickle2csv_art.py
 - wird von open_runs.sh aufgerufen
 - erzeugt alpha_relaxation_time.csv wenn Pickles vorhanden

python_utils/co_art_join.py
 - wird von open_runs.sh aufgerufen
 - fügt Werte aus alpha_relaxation_time.csv in compute_order.csv ein

python_utils/co_mean.py
 - wird von open_runs.sh aufgerufen
 - erzeugt avg_compute_order.csv (mittelwerte) wenn rand>1

python_utils/pickle2csv.py
 - wird von pickle_create_csv_and_plot_data.sh aufgerufen
 - erzeugt MSD und SelfInt CSVs

python_utils/plot_pickle_data.py
 - wird von pickle_create_csv_and_plot_data.sh aufgerufen
 - erzeugt MSD und SelfInt PNGs aus den entsprechenden CSVs

python_utils/color_plot.py
 - erzeugt Color-Balken-Diagramme
 - manueller Aufruf


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
 - Fortschritts-Anzeige für die einzelnen Cores (werden gelöscht wenn Runs fertig sind)

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
