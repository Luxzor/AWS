# Guía de Despliegue en AWS — Primera Entrega

## Resumen de la arquitectura

```
Internet → VPC Pública → Subnet Pública → EC2 (Amazon Linux) → Flask :5000
```

---

## Paso 1: Crear la VPC

1. En la consola AWS → **VPC** → **Create VPC**
2. Selecciona **VPC only**
3. Nombre: `sicei-vpc`
4. IPv4 CIDR: `10.0.0.0/16`
5. Click **Create VPC**

### Activar DNS Hostnames (requerido por el proyecto)
- Selecciona tu VPC → **Actions** → **Edit VPC settings**
- Activa **Enable DNS hostnames** ✅
- Activa **Enable DNS resolution** ✅
- Guarda los cambios

---

## Paso 2: Crear Subnet Pública

1. **VPC → Subnets → Create subnet**
2. VPC: `sicei-vpc`
3. Nombre: `sicei-subnet-publica`
4. Availability Zone: cualquiera (ej. `us-east-1a`)
5. IPv4 CIDR: `10.0.1.0/24`
6. Click **Create subnet**

### Habilitar asignación automática de IP pública
- Selecciona la subnet → **Actions** → **Edit subnet settings**
- Activa **Enable auto-assign public IPv4 address** ✅

---

## Paso 3: Crear Internet Gateway

1. **VPC → Internet Gateways → Create internet gateway**
2. Nombre: `sicei-igw`
3. Click **Create**
4. Selecciona el IGW creado → **Actions → Attach to VPC** → selecciona `sicei-vpc`

---

## Paso 4: Configurar la Route Table

1. **VPC → Route Tables → Create route table**
2. Nombre: `sicei-rt-publica`
3. VPC: `sicei-vpc`
4. Click **Create**

### Agregar ruta a Internet
- Selecciona la route table → **Routes → Edit routes → Add route**
  - Destination: `0.0.0.0/0`
  - Target: el Internet Gateway `sicei-igw`
- Guarda los cambios

### Asociar con la subnet pública
- **Subnet associations → Edit subnet associations**
- Selecciona `sicei-subnet-publica` ✅

---

## Paso 5: Crear el Security Group

1. **EC2 → Security Groups → Create security group**
2. Nombre: `sicei-sg`
3. VPC: `sicei-vpc`
4. **Inbound rules:**

| Type       | Protocol | Port | Source    |
|------------|----------|------|-----------|
| SSH        | TCP      | 22   | 0.0.0.0/0 |
| Custom TCP | TCP      | 5000 | 0.0.0.0/0 |

5. Click **Create security group**

---

## Paso 6: Lanzar la instancia EC2

1. **EC2 → Instances → Launch instance**
2. Nombre: `sicei-server`
3. AMI: **Amazon Linux 2023** (gratis)
4. Instance type: **t2.micro** o **t2.nano**
5. Key pair: crea uno nuevo o usa uno existente (guarda el `.pem`)
6. **Network settings:**
   - VPC: `sicei-vpc`
   - Subnet: `sicei-subnet-publica`
   - Auto-assign public IP: **Enable**
   - Security group: `sicei-sg`
7. Click **Launch instance**

---

## Paso 7: Conectarse a la instancia

```bash
# En tu terminal local:
chmod 400 tu-keypair.pem
ssh -i tu-keypair.pem ec2-user@<IP-PÚBLICA-DE-TU-EC2>
```

---

## Paso 8: Instalar y correr la aplicación

```bash
# 1. Actualizar paquetes
sudo yum update -y

# 2. Instalar Python 3, pip y git
sudo yum install -y python3 python3-pip git

# 3. Clonar tu repositorio
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO

# 4. Instalar Flask
pip3 install flask

# 5. Correr la aplicación (en background)
nohup python3 app.py > app.log 2>&1 &

# 6. Verificar que está corriendo
curl http://localhost:5000/alumnos
# Debe responder: []
```

---

## Paso 9: Verificar el acceso público

En tu navegador o desde otra terminal:
```
GET http://<DNS-PÚBLICO-DE-EC2>:5000/alumnos
```

El DNS público se ve en la consola EC2, ejemplo:
```
http://ec2-3-215-9-223.compute-1.amazonaws.com:5000/alumnos
```

Debe responder: `200 application/json []`

---

## Paso 10: Crear la AMI

1. **EC2 → Instances** → selecciona tu instancia
2. **Actions → Image and templates → Create image**
3. Nombre: `sicei-ami`
4. Click **Create image**

---

## Comandos útiles en el servidor

```bash
# Ver logs de la app
tail -f app.log

# Ver si la app está corriendo
ps aux | grep python3

# Detener la app
kill $(pgrep -f app.py)

# Reiniciar la app
nohup python3 app.py > app.log 2>&1 &

# Ver el puerto en uso
ss -tlnp | grep 5000
```

---

## Endpoints de la API

| Método | URL                 | Descripción              | Código exitoso |
|--------|---------------------|--------------------------|----------------|
| GET    | /alumnos            | Lista todos los alumnos  | 200            |
| GET    | /alumnos/{id}       | Obtiene un alumno        | 200            |
| POST   | /alumnos            | Crea un alumno           | 201            |
| PUT    | /alumnos/{id}       | Actualiza un alumno      | 200            |
| DELETE | /alumnos/{id}       | Elimina un alumno        | 200            |
| GET    | /profesores         | Lista todos los profesores | 200          |
| GET    | /profesores/{id}    | Obtiene un profesor      | 200            |
| POST   | /profesores         | Crea un profesor         | 201            |
| PUT    | /profesores/{id}    | Actualiza un profesor    | 200            |
| DELETE | /profesores/{id}    | Elimina un profesor      | 200            |

---

## Ejemplos de JSON

### POST /alumnos
```json
{
  "nombres": "Juan Carlos",
  "apellidos": "García López",
  "matricula": "A12345",
  "promedio": 8.5
}
```

### POST /profesores
```json
{
  "numeroEmpleado": "EMP001",
  "nombres": "María",
  "apellidos": "Martínez",
  "horasClase": 20
}
```
