import os
import uuid
import secrets
import time
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import boto3

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuracion de Base de Datos (RDS MySQL)
# ---------------------------------------------------------------------------
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_PORT     = os.environ.get("DB_PORT", "3306")
DB_NAME     = os.environ.get("DB_NAME", "sicei")
DB_USER     = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Configuracion de AWS
# ---------------------------------------------------------------------------
AWS_REGION        = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY    = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN", "")

S3_BUCKET      = os.environ.get("S3_BUCKET", "")
SNS_TOPIC_ARN  = os.environ.get("SNS_TOPIC_ARN", "")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "sesiones-alumnos")


def get_aws_client(service):
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"]     = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_KEY
        if AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = AWS_SESSION_TOKEN
    return boto3.client(service, **kwargs)


# ---------------------------------------------------------------------------
# Modelos ORM
# ---------------------------------------------------------------------------

class Alumno(db.Model):
    __tablename__ = "alumnos"

    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombres       = db.Column(db.String(255), nullable=False)
    apellidos     = db.Column(db.String(255), nullable=False)
    matricula     = db.Column(db.String(100), nullable=False)
    promedio      = db.Column(db.Float, nullable=False)
    fotoPerfilUrl = db.Column(db.String(512), nullable=True)
    password      = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id":            self.id,
            "nombres":       self.nombres,
            "apellidos":     self.apellidos,
            "matricula":     self.matricula,
            "promedio":      self.promedio,
            "fotoPerfilUrl": self.fotoPerfilUrl,
            "password":      self.password,
        }


class Profesor(db.Model):
    __tablename__ = "profesores"

    id             = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numeroEmpleado = db.Column(db.String(100), nullable=False)
    nombres        = db.Column(db.String(255), nullable=False)
    apellidos      = db.Column(db.String(255), nullable=False)
    horasClase     = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id":             self.id,
            "numeroEmpleado": self.numeroEmpleado,
            "nombres":        self.nombres,
            "apellidos":      self.apellidos,
            "horasClase":     self.horasClase,
        }


with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error_response(message, status_code=400):
    return jsonify({"error": message}), status_code


def validate_alumno(data, require_all=True):
    if require_all:
        for campo in ["nombres", "apellidos", "matricula", "promedio"]:
            if campo not in data or data[campo] is None:
                return None, f"El campo '{campo}' es requerido."

    cleaned = {}

    if "nombres" in data:
        if not isinstance(data["nombres"], str) or not data["nombres"].strip():
            return None, "El campo 'nombres' debe ser una cadena de texto no vacia."
        cleaned["nombres"] = data["nombres"].strip()

    if "apellidos" in data:
        if not isinstance(data["apellidos"], str) or not data["apellidos"].strip():
            return None, "El campo 'apellidos' debe ser una cadena de texto no vacia."
        cleaned["apellidos"] = data["apellidos"].strip()

    if "matricula" in data:
        if not isinstance(data["matricula"], str) or not data["matricula"].strip():
            return None, "El campo 'matricula' debe ser una cadena de texto no vacia."
        cleaned["matricula"] = data["matricula"].strip()

    if "promedio" in data:
        try:
            promedio = float(data["promedio"])
        except (TypeError, ValueError):
            return None, "El campo 'promedio' debe ser un numero decimal."
        if promedio < 0 or promedio > 10:
            return None, "El campo 'promedio' debe estar entre 0 y 10."
        cleaned["promedio"] = promedio

    if "password" in data:
        if data["password"] is not None:
            if not isinstance(data["password"], str) or not data["password"].strip():
                return None, "El campo 'password' debe ser una cadena de texto no vacia."
            cleaned["password"] = data["password"]

    if "fotoPerfilUrl" in data:
        cleaned["fotoPerfilUrl"] = data["fotoPerfilUrl"]

    return cleaned, None


def validate_profesor(data, require_all=True):
    if require_all:
        for campo in ["numeroEmpleado", "nombres", "apellidos", "horasClase"]:
            if campo not in data or data[campo] is None:
                return None, f"El campo '{campo}' es requerido."

    cleaned = {}

    if "numeroEmpleado" in data:
        val = data["numeroEmpleado"]
        if val is None or str(val).strip() == "":
            return None, "El campo 'numeroEmpleado' no puede estar vacio."
        cleaned["numeroEmpleado"] = str(val)

    if "nombres" in data:
        if not isinstance(data["nombres"], str) or not data["nombres"].strip():
            return None, "El campo 'nombres' debe ser una cadena de texto no vacia."
        cleaned["nombres"] = data["nombres"].strip()

    if "apellidos" in data:
        if not isinstance(data["apellidos"], str) or not data["apellidos"].strip():
            return None, "El campo 'apellidos' debe ser una cadena de texto no vacia."
        cleaned["apellidos"] = data["apellidos"].strip()

    if "horasClase" in data:
        try:
            horas = int(data["horasClase"])
        except (TypeError, ValueError):
            return None, "El campo 'horasClase' debe ser un numero entero."
        if horas < 0:
            return None, "El campo 'horasClase' debe ser un numero positivo."
        cleaned["horasClase"] = horas

    return cleaned, None


# ---------------------------------------------------------------------------
# Alumnos -- GET /alumnos  y  POST /alumnos
# DELETE /alumnos -> Flask devuelve 405 automaticamente
# ---------------------------------------------------------------------------

@app.route("/alumnos", methods=["GET", "POST"])
def alumnos_collection():
    if request.method == "GET":
        return jsonify([a.to_dict() for a in Alumno.query.all()]), 200

    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON valido.", 400)

        cleaned, err = validate_alumno(data, require_all=True)
        if err:
            return error_response(err, 400)

        nuevo = Alumno(
            nombres=cleaned["nombres"],
            apellidos=cleaned["apellidos"],
            matricula=cleaned["matricula"],
            promedio=cleaned["promedio"],
            password=cleaned.get("password"),
            fotoPerfilUrl=cleaned.get("fotoPerfilUrl"),
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify(nuevo.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


@app.route("/alumnos/<int:id>", methods=["GET", "PUT", "DELETE"])
def alumnos_item(id):
    alumno = db.session.get(Alumno, id)

    if request.method == "GET":
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)
        return jsonify(alumno.to_dict()), 200

    if request.method == "DELETE":
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)
        result = alumno.to_dict()
        db.session.delete(alumno)
        db.session.commit()
        return jsonify(result), 200

    try:
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)

        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON valido.", 400)

        cleaned, err = validate_alumno(data, require_all=False)
        if err:
            return error_response(err, 400)

        for key, value in cleaned.items():
            setattr(alumno, key, value)

        db.session.commit()
        return jsonify(alumno.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /alumnos/{id}/fotoPerfil -- Subir foto de perfil a S3
# ---------------------------------------------------------------------------

@app.route("/alumnos/<int:id>/fotoPerfil", methods=["POST"])
def alumno_foto_perfil(id):
    alumno = db.session.get(Alumno, id)
    if alumno is None:
        return error_response(f"Alumno con id {id} no encontrado.", 404)

    if "foto" not in request.files:
        return error_response("Se requiere un archivo con el campo 'foto'.", 400)

    file = request.files["foto"]
    if file.filename == "":
        return error_response("No se selecciono ningun archivo.", 400)

    try:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
        key = f"alumnos/{id}/fotoPerfil.{ext}"

        s3 = get_aws_client("s3")
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file.content_type or "image/jpeg",
            },
        )

        url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
        alumno.fotoPerfilUrl = url
        db.session.commit()

        return jsonify(alumno.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /alumnos/{id}/email -- Enviar notificacion por SNS
# ---------------------------------------------------------------------------

@app.route("/alumnos/<int:id>/email", methods=["POST"])
def alumno_email(id):
    alumno = db.session.get(Alumno, id)
    if alumno is None:
        return error_response(f"Alumno con id {id} no encontrado.", 404)

    try:
        sns = get_aws_client("sns")
        message = (
            f"Informacion del alumno:\n"
            f"Nombre:    {alumno.nombres} {alumno.apellidos}\n"
            f"Matricula: {alumno.matricula}\n"
            f"Promedio:  {alumno.promedio}\n"
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=f"Calificaciones -- {alumno.nombres} {alumno.apellidos}",
        )
        return jsonify({"message": "Notificacion enviada correctamente."}), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /alumnos/{id}/session/login
# ---------------------------------------------------------------------------

@app.route("/alumnos/<int:id>/session/login", methods=["POST"])
def alumno_session_login(id):
    alumno = db.session.get(Alumno, id)
    if alumno is None:
        return error_response(f"Alumno con id {id} no encontrado.", 404)

    data = request.get_json(force=True, silent=True)
    if data is None or "password" not in data:
        return error_response("Se requiere el campo 'password'.", 400)

    if alumno.password is None or data["password"] != alumno.password:
        return error_response("Contrasena incorrecta.", 400)

    try:
        session_string = secrets.token_hex(64)   # 128 caracteres hexadecimales
        session_id     = str(uuid.uuid4())
        fecha          = int(time.time())

        dynamodb = get_aws_client("dynamodb")
        dynamodb.put_item(
            TableName=DYNAMODB_TABLE,
            Item={
                "id":            {"S": session_id},
                "fecha":         {"N": str(fecha)},
                "alumnoId":      {"N": str(id)},
                "active":        {"BOOL": True},
                "sessionString": {"S": session_string},
            },
        )

        return jsonify({
            "id":            session_id,
            "fecha":         fecha,
            "alumnoId":      id,
            "active":        True,
            "sessionString": session_string,
        }), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /alumnos/{id}/session/verify
# ---------------------------------------------------------------------------

@app.route("/alumnos/<int:id>/session/verify", methods=["POST"])
def alumno_session_verify(id):
    data = request.get_json(force=True, silent=True)
    if data is None or "sessionString" not in data:
        return error_response("Se requiere el campo 'sessionString'.", 400)

    session_string = data["sessionString"]

    try:
        dynamodb = get_aws_client("dynamodb")
        response = dynamodb.scan(
            TableName=DYNAMODB_TABLE,
            FilterExpression="alumnoId = :aid AND sessionString = :ss",
            ExpressionAttributeValues={
                ":aid": {"N": str(id)},
                ":ss":  {"S": session_string},
            },
        )
        items = response.get("Items", [])
        if not items:
            return error_response("Sesion no encontrada.", 400)

        item = items[0]
        if not item.get("active", {}).get("BOOL", False):
            return error_response("La sesion no esta activa.", 400)

        return jsonify({"message": "Sesion valida.", "active": True}), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# POST /alumnos/{id}/session/logout
# ---------------------------------------------------------------------------

@app.route("/alumnos/<int:id>/session/logout", methods=["POST"])
def alumno_session_logout(id):
    data = request.get_json(force=True, silent=True)
    if data is None or "sessionString" not in data:
        return error_response("Se requiere el campo 'sessionString'.", 400)

    session_string = data["sessionString"]

    try:
        dynamodb = get_aws_client("dynamodb")
        response = dynamodb.scan(
            TableName=DYNAMODB_TABLE,
            FilterExpression="alumnoId = :aid AND sessionString = :ss",
            ExpressionAttributeValues={
                ":aid": {"N": str(id)},
                ":ss":  {"S": session_string},
            },
        )
        items = response.get("Items", [])
        if not items:
            return error_response("Sesion no encontrada.", 400)

        session_id = items[0]["id"]["S"]
        dynamodb.update_item(
            TableName=DYNAMODB_TABLE,
            Key={"id": {"S": session_id}},
            UpdateExpression="SET #a = :false",
            ExpressionAttributeNames={"#a": "active"},
            ExpressionAttributeValues={":false": {"BOOL": False}},
        )

        return jsonify({"message": "Sesion cerrada correctamente.", "active": False}), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Profesores -- GET /profesores  y  POST /profesores
# DELETE /profesores -> Flask devuelve 405 automaticamente
# ---------------------------------------------------------------------------

@app.route("/profesores", methods=["GET", "POST"])
def profesores_collection():
    if request.method == "GET":
        return jsonify([p.to_dict() for p in Profesor.query.all()]), 200

    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON valido.", 400)

        cleaned, err = validate_profesor(data, require_all=True)
        if err:
            return error_response(err, 400)

        nuevo = Profesor(
            numeroEmpleado=cleaned["numeroEmpleado"],
            nombres=cleaned["nombres"],
            apellidos=cleaned["apellidos"],
            horasClase=cleaned["horasClase"],
        )
        db.session.add(nuevo)
        db.session.commit()
        return jsonify(nuevo.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


@app.route("/profesores/<int:id>", methods=["GET", "PUT", "DELETE"])
def profesores_item(id):
    profesor = db.session.get(Profesor, id)

    if request.method == "GET":
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)
        return jsonify(profesor.to_dict()), 200

    if request.method == "DELETE":
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)
        result = profesor.to_dict()
        db.session.delete(profesor)
        db.session.commit()
        return jsonify(result), 200

    try:
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)

        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON valido.", 400)

        cleaned, err = validate_profesor(data, require_all=False)
        if err:
            return error_response(err, 400)

        for key, value in cleaned.items():
            setattr(profesor, key, value)

        db.session.commit()
        return jsonify(profesor.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Run -- puerto 8080 (Nginx en :80 redirige aqui)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
