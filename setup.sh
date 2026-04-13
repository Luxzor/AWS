#!/bin/bash
# =============================================================
# Script de instalación para Amazon Linux 2023 (t2.micro/nano)
# Ejecutar como: bash setup.sh
# =============================================================

set -e

echo ">>> Actualizando paquetes..."
sudo yum update -y

echo ">>> Instalando Python 3, pip y git..."
sudo yum install -y python3 python3-pip git

echo ">>> Clonando el repositorio..."
# Cambia esta URL por la URL real de tu repositorio git
# git clone https://github.com/TU_USUARIO/TU_REPO.git app
# cd app

echo ">>> Instalando dependencias de Python..."
pip3 install -r requirements.txt

echo ">>> Abriendo el puerto 5000 en el firewall local (si aplica)..."
# En AWS, el puerto se abre desde el Security Group en la consola.

echo ">>> Iniciando la aplicación en background..."
nohup python3 app.py > app.log 2>&1 &

echo ""
echo "=============================================="
echo "  Aplicación corriendo en el puerto 5000"
echo "  Verifica con: curl http://localhost:5000/alumnos"
echo "=============================================="
