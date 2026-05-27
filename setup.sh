#!/bin/bash
# =============================================================
# Script de instalacion para Amazon Linux 2023
# Ejecutar como: bash setup.sh
#
# Flujo:
#   Flask corre en puerto 8080
#   Nginx escucha en puerto 80 y redirige a 8080
#   El autotest conecta a http://<ip>/ (puerto 80)
# =============================================================

set -e

# ------------------------------------------------------------------
# VARIABLES DE ENTORNO — editar antes de ejecutar
# ------------------------------------------------------------------
export DB_HOST="TU_ENDPOINT_RDS"          # ej: sicei-db.xxxxxxx.us-east-1.rds.amazonaws.com
export DB_PORT="3306"
export DB_NAME="sicei"
export DB_USER="admin"
export DB_PASSWORD="TU_PASSWORD_RDS"

export AWS_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="TU_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="TU_SECRET_KEY"
export AWS_SESSION_TOKEN="TU_SESSION_TOKEN"

export S3_BUCKET="TU_NOMBRE_BUCKET_S3"
export SNS_TOPIC_ARN="arn:aws:sns:us-east-1:XXXXXXXXXX:sicei-notificaciones"
export DYNAMODB_TABLE="sesiones-alumnos"
# ------------------------------------------------------------------

echo ">>> Actualizando paquetes..."
sudo yum update -y

echo ">>> Instalando Python 3, pip, Nginx y dependencias del sistema..."
sudo yum install -y python3 python3-pip nginx python3-devel gcc

echo ">>> Instalando dependencias de Python..."
pip3 install -r requirements.txt

# ------------------------------------------------------------------
# Configuracion de Nginx como proxy inverso
# ------------------------------------------------------------------
echo ">>> Configurando Nginx..."
sudo tee /etc/nginx/conf.d/sicei.conf > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX

# Desactivar el bloque default de Nginx que tambien usa el puerto 80
sudo sed -i 's/^[[:space:]]*listen[[:space:]]*80[[:space:]]*default_server/# &/' /etc/nginx/nginx.conf
sudo sed -i 's/^[[:space:]]*listen[[:space:]]*\[::\]:80[[:space:]]*default_server/# &/' /etc/nginx/nginx.conf

echo ">>> Iniciando y habilitando Nginx..."
sudo systemctl enable nginx
sudo systemctl restart nginx

# ------------------------------------------------------------------
# Matar cualquier instancia anterior de la app y volver a lanzar
# ------------------------------------------------------------------
echo ">>> Deteniendo instancia anterior de la app (si existe)..."
pkill -f "python3 app.py" || true

echo ">>> Iniciando la aplicacion Flask en puerto 8080..."
nohup env \
  DB_HOST="$DB_HOST" \
  DB_PORT="$DB_PORT" \
  DB_NAME="$DB_NAME" \
  DB_USER="$DB_USER" \
  DB_PASSWORD="$DB_PASSWORD" \
  AWS_REGION="$AWS_REGION" \
  AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  S3_BUCKET="$S3_BUCKET" \
  SNS_TOPIC_ARN="$SNS_TOPIC_ARN" \
  DYNAMODB_TABLE="$DYNAMODB_TABLE" \
  python3 app.py > app.log 2>&1 &

sleep 3

echo ""
echo "=============================================="
echo "  Flask corriendo en:  http://localhost:8080"
echo "  Nginx escuchando en: http://0.0.0.0:80"
echo ""
echo "  Prueba local:"
echo "    curl http://localhost/alumnos"
echo ""
echo "  Revisa logs si algo falla:"
echo "    tail -f app.log"
echo "=============================================="
