#!/usr/bin/env bash
# exit on error
set -e

# Instala la librería C de TA-Lib desde el código fuente
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
make install
cd ..

# --- LÍNEA MODIFICADA ---
# Usamos python3 -m pip para asegurar que se usa el pip del entorno virtual correcto
python3 -m pip install -r requirements.txt
