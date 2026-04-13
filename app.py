from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
alumnos = []
profesores = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error_response(message, status_code=400):
    return jsonify({"error": message}), status_code


def validate_alumno(data, require_all=True):
    """
    Valida los campos de Alumno.
    require_all=True  → POST (todos los campos obligatorios)
    require_all=False → PUT  (solo valida lo que viene)
    Retorna (cleaned_data, error_msg). error_msg es None si es válido.
    """
    if require_all:
        for campo in ["id", "nombres", "apellidos", "matricula", "promedio"]:
            if campo not in data or data[campo] is None:
                return None, f"El campo '{campo}' es requerido."

    cleaned = {}

    # id  (solo en POST)
    if "id" in data and require_all:
        try:
            cleaned["id"] = int(data["id"])
        except (TypeError, ValueError):
            return None, "El campo 'id' debe ser un número entero."

    # nombres
    if "nombres" in data:
        if not isinstance(data["nombres"], str) or not data["nombres"].strip():
            return None, "El campo 'nombres' debe ser una cadena de texto no vacía."
        cleaned["nombres"] = data["nombres"].strip()

    # apellidos
    if "apellidos" in data:
        if not isinstance(data["apellidos"], str) or not data["apellidos"].strip():
            return None, "El campo 'apellidos' debe ser una cadena de texto no vacía."
        cleaned["apellidos"] = data["apellidos"].strip()

    # matricula  — debe ser string no vacío (int es inválido)
    if "matricula" in data:
        if not isinstance(data["matricula"], str) or not data["matricula"].strip():
            return None, "El campo 'matricula' debe ser una cadena de texto no vacía."
        cleaned["matricula"] = data["matricula"].strip()

    # promedio  — float, entre 0 y 10
    if "promedio" in data:
        try:
            promedio = float(data["promedio"])
        except (TypeError, ValueError):
            return None, "El campo 'promedio' debe ser un número decimal."
        if promedio < 0 or promedio > 10:
            return None, "El campo 'promedio' debe estar entre 0 y 10."
        cleaned["promedio"] = promedio

    return cleaned, None


def validate_profesor(data, require_all=True):
    """
    Valida los campos de Profesor.
    """
    if require_all:
        for campo in ["id", "numeroEmpleado", "nombres", "apellidos", "horasClase"]:
            if campo not in data or data[campo] is None:
                return None, f"El campo '{campo}' es requerido."

    cleaned = {}

    # id  (solo en POST)
    if "id" in data and require_all:
        try:
            cleaned["id"] = int(data["id"])
        except (TypeError, ValueError):
            return None, "El campo 'id' debe ser un número entero."

    # numeroEmpleado  — acepta int o string positivo/no vacío
    if "numeroEmpleado" in data:
        val = data["numeroEmpleado"]
        if val is None or str(val).strip() == "":
            return None, "El campo 'numeroEmpleado' no puede estar vacío."
        cleaned["numeroEmpleado"] = val  # conserva el tipo original

    # nombres
    if "nombres" in data:
        if not isinstance(data["nombres"], str) or not data["nombres"].strip():
            return None, "El campo 'nombres' debe ser una cadena de texto no vacía."
        cleaned["nombres"] = data["nombres"].strip()

    # apellidos
    if "apellidos" in data:
        if not isinstance(data["apellidos"], str) or not data["apellidos"].strip():
            return None, "El campo 'apellidos' debe ser una cadena de texto no vacía."
        cleaned["apellidos"] = data["apellidos"].strip()

    # horasClase  — entero >= 0 (rechaza floats negativos como -1.26)
    if "horasClase" in data:
        try:
            horas = int(data["horasClase"])
        except (TypeError, ValueError):
            return None, "El campo 'horasClase' debe ser un número entero."
        if horas < 0:
            return None, "El campo 'horasClase' debe ser un número positivo."
        cleaned["horasClase"] = horas

    return cleaned, None


# ---------------------------------------------------------------------------
# Alumnos  — GET /alumnos y POST /alumnos
# DELETE /alumnos  →  Flask devuelve 405 automáticamente
# ---------------------------------------------------------------------------

@app.route("/alumnos", methods=["GET", "POST"])
def alumnos_collection():
    if request.method == "GET":
        return jsonify(alumnos), 200

    # POST
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON válido.", 400)

        cleaned, err = validate_alumno(data, require_all=True)
        if err:
            return error_response(err, 400)

        nuevo = {
            "id":        cleaned["id"],
            "nombres":   cleaned["nombres"],
            "apellidos": cleaned["apellidos"],
            "matricula": cleaned["matricula"],
            "promedio":  cleaned["promedio"],
        }
        alumnos.append(nuevo)
        return jsonify(nuevo), 201

    except Exception as e:
        return error_response(str(e), 500)


@app.route("/alumnos/<int:id>", methods=["GET", "PUT", "DELETE"])
def alumnos_item(id):
    alumno = next((a for a in alumnos if a["id"] == id), None)

    if request.method == "GET":
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)
        return jsonify(alumno), 200

    if request.method == "DELETE":
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)
        alumnos.remove(alumno)
        return jsonify(alumno), 200

    # PUT
    try:
        if alumno is None:
            return error_response(f"Alumno con id {id} no encontrado.", 404)

        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON válido.", 400)

        cleaned, err = validate_alumno(data, require_all=False)
        if err:
            return error_response(err, 400)

        alumno.update(cleaned)
        return jsonify(alumno), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Profesores  — GET /profesores y POST /profesores
# DELETE /profesores  →  Flask devuelve 405 automáticamente
# ---------------------------------------------------------------------------

@app.route("/profesores", methods=["GET", "POST"])
def profesores_collection():
    if request.method == "GET":
        return jsonify(profesores), 200

    # POST
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON válido.", 400)

        cleaned, err = validate_profesor(data, require_all=True)
        if err:
            return error_response(err, 400)

        nuevo = {
            "id":             cleaned["id"],
            "numeroEmpleado": cleaned["numeroEmpleado"],
            "nombres":        cleaned["nombres"],
            "apellidos":      cleaned["apellidos"],
            "horasClase":     cleaned["horasClase"],
        }
        profesores.append(nuevo)
        return jsonify(nuevo), 201

    except Exception as e:
        return error_response(str(e), 500)


@app.route("/profesores/<int:id>", methods=["GET", "PUT", "DELETE"])
def profesores_item(id):
    profesor = next((p for p in profesores if p["id"] == id), None)

    if request.method == "GET":
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)
        return jsonify(profesor), 200

    if request.method == "DELETE":
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)
        profesores.remove(profesor)
        return jsonify(profesor), 200

    # PUT
    try:
        if profesor is None:
            return error_response(f"Profesor con id {id} no encontrado.", 404)

        data = request.get_json(force=True, silent=True)
        if data is None:
            return error_response("El cuerpo debe ser JSON válido.", 400)

        cleaned, err = validate_profesor(data, require_all=False)
        if err:
            return error_response(err, 400)

        profesor.update(cleaned)
        return jsonify(profesor), 200

    except Exception as e:
        return error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Run  — puerto 8080 (requerido por el autotest)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
