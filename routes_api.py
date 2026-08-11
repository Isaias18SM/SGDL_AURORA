from flask import Blueprint, request, jsonify
from database import get_db
from decorators import solo_rol_api, login_requerido

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/buscar-aprendiz')
@solo_rol_api('instructor')
def api_buscar_aprendiz():
    documento = request.args.get('documento', '').strip()
    tipo = request.args.get('tipo', '').strip().upper()

    if not documento or not documento.isdigit():
        return jsonify({"status": "error", "message": "Ingresa únicamente el número de documento (CC o TI)."}), 400

    if tipo not in ('CC', 'TI'):
        tipo = None

    try:
        conn = get_db()
        with conn.cursor() as cur:
            if tipo:
                cur.execute(
                    "SELECT * FROM aprendiz WHERE NUMERO_DOCUMENTO = %s AND TIPO_DOCUMENTO = %s",
                    (documento, tipo)
                )
            else:
                cur.execute(
                    "SELECT * FROM aprendiz WHERE NUMERO_DOCUMENTO = %s AND TIPO_DOCUMENTO IN ('CC', 'TI')",
                    (documento,)
                )
            fila = cur.fetchone()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500

    if not fila:
        return jsonify({"status": "not_found", "message": "No se encontró ningún aprendiz con ese número de documento."}), 404

    nombre = f"{fila.get('NOMBRES', '')} {fila.get('APELLIDOS', '')}".strip()
    return jsonify({
        "status": "success",
        "aprendiz": {
            "id": fila.get('ID_APRENDIZ'),
            "nombre": nombre,
            "tipo_documento": fila.get('TIPO_DOCUMENTO'),
            "numero_documento": fila.get('NUMERO_DOCUMENTO'),
            "correo": fila.get('CORREO_SENA'),
            "ficha": fila.get('FICHA'),
        }
    })

@api_bp.route('/api/fichas')
@solo_rol_api('instructor')
def api_fichas():
    fichas_mock = [
        {"codigo": "2557908", "programa": "Análisis y Desarrollo de Software", "jornada": "Diurna", "aprendices_activos": 35},
        {"codigo": "2557909", "programa": "Análisis y Desarrollo de Software", "jornada": "Nocturna", "aprendices_activos": 32},
    ]
    return jsonify({"status": "success", "fichas": fichas_mock})

@api_bp.route('/api/cambiar-estado', methods=['POST'])
@login_requerido
def api_cambiar_estado():
    return jsonify({"status": "success", "message": "Estado actualizado correctamente"})