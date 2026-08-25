from datetime import date
from flask import Blueprint, request, jsonify, session
from database import get_db
from decorators import solo_rol_api, login_requerido

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/buscar-aprendiz')
@solo_rol_api('instructor', 'coordinador')
def api_buscar_aprendiz():
    documento = request.args.get('documento', '').strip()
    tipo = request.args.get('tipo', '').strip().upper()

    if not documento or not documento.isdigit():
        return jsonify({"status": "error", "message": "Ingresa únicamente el número de documento (CC o TI)."}), 400

    if tipo not in ('CC', 'TI'):
        tipo = None

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            sql = """
                SELECT u.*, f.No_FICHA
                FROM usuario u
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                LEFT JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                WHERE u.No_Documento = %s
                  AND u.ROL = %s
            """
            params = [documento, 'Aprendiz']

            if tipo:
                sql += " AND u.TPI_DOCUMENTO = %s"
                params.append(tipo)

            cur.execute(sql, tuple(params))
            fila = cur.fetchone()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500
    finally:
        if conn:
            conn.close()

    if not fila:
        return jsonify({"status": "not_found", "message": "No se encontró ningún aprendiz con ese número de documento."}), 404

    nombre = f"{fila.get('Nombre', '')} {fila.get('Apellidos', '')}".strip()
    return jsonify({
        "status": "success",
        "aprendiz": {
            "id": fila.get('Id_Usuario'),
            "nombre": nombre,
            "tipo_documento": fila.get('TPI_DOCUMENTO'),
            "numero_documento": fila.get('No_Documento'),
            "correo": fila.get('CORREO_SENA'),
            "ficha": fila.get('No_FICHA'),
        }
    })


@api_bp.route('/api/fichas')
@solo_rol_api('instructor', 'coordinador')
def api_fichas():
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.ID_FICHA,
                       f.No_FICHA        AS codigo,
                       f.Jornada         AS jornada,
                       f.TipoDeFicha     AS tipo_ficha,
                       p.Nombre          AS programa,
                       COUNT(ufa.Id_Usuario) AS aprendices_activos
                FROM ficha f
                JOIN programa p ON p.Id_Programa = f.Id_Programa
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                LEFT JOIN usuario u ON u.Id_Usuario = ufa.Id_Usuario AND u.ROL = 'Aprendiz' AND u.Activo_SN = '1'
                GROUP BY f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha, p.Nombre
                ORDER BY f.No_FICHA
            """)
            fichas = cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"status": "success", "fichas": fichas})


@api_bp.route('/api/cambiar-estado', methods=['POST'])
@solo_rol_api('instructor', 'coordinador')
def api_cambiar_estado():
    """Permite al instructor/coordinador marcar manualmente el estado
    (Presente, Falla, Retardo, Excusa) de un aprendiz para el día de hoy."""
    data = request.get_json(silent=True) or {}
    id_usuario = data.get('id')
    estado = (data.get('estado') or '').strip()

    estados_validos = ('Presente', 'Falla', 'Retardo', 'Excusa')
    if not id_usuario or estado not in estados_validos:
        return jsonify({"status": "error", "message": "Datos inválidos."}), 400

    hoy = date.today()

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # IMPORTANTE: esto requiere que la tabla `asistencia` tenga una
            # llave UNIQUE sobre (Id_Usuario, Fecha_Requerida). Si no la
            # tiene, cada clic insertará una fila nueva en vez de actualizar
            # la existente. Ver nota más abajo para el ALTER TABLE necesario.
            cur.execute(
                """
                INSERT INTO asistencia (Id_Usuario, Fecha_Requerida, Estado)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE Estado = VALUES(Estado)
                """,
                (id_usuario, hoy, estado)
            )
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": "Error al guardar en la base de datos."}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"status": "success", "message": "Estado actualizado correctamente"})


@api_bp.route('/api/registrar-entrada', methods=['POST'])
@solo_rol_api('aprendiz')
def api_registrar_entrada():
    id_usuario = session.get('id')
    data = request.get_json(silent=True) or {}
    tipo = (data.get('tipo') or '').strip().upper()

    if tipo not in ('ENTRADA', 'SALIDA'):
        return jsonify({"status": "error", "message": "Tipo de registro inválido."}), 400

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("CALL sp_registrar_asistencia(%s, %s)", (id_usuario, tipo))
            resultado = cur.fetchone()
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500
    finally:
        if conn:
            conn.close()

    estado = resultado.get('estado') if resultado else None

    if estado == 'OK_ENTRADA':
        return jsonify({"status": "success", "message": "Entrada registrada exitosamente", "hora": str(resultado.get('hora'))})

    if estado == 'OK_SALIDA':
        return jsonify({"status": "success", "message": "Salida registrada exitosamente", "hora": str(resultado.get('hora'))})

    if estado == 'DUPLICADO_ENTRADA':
        return jsonify({"status": "duplicado", "message": "Ya registraste tu entrada el día de hoy."}), 409

    if estado == 'DUPLICADO_SALIDA':
        return jsonify({"status": "duplicado", "message": "Ya registraste tu salida el día de hoy."}), 409

    if estado == 'SIN_ENTRADA':
        return jsonify({"status": "error", "message": "Debes registrar tu entrada antes de registrar la salida."}), 409

    return jsonify({"status": "error", "message": "No se pudo procesar el registro."}), 500


@api_bp.route('/api/marcar-qr', methods=['POST'])
def api_marcar_qr():
    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    tipo = (data.get('tipo') or '').strip().upper()

    if not token:
        return jsonify({"status": "error", "message": "Código QR inválido."}), 400
    if tipo not in ('ENTRADA', 'SALIDA'):
        return jsonify({"status": "error", "message": "Tipo de registro inválido."}), 400

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("CALL sp_registrar_asistencia_qr(%s, %s)", (token, tipo))
            resultado = cur.fetchone()
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500
    finally:
        if conn:
            conn.close()

    estado = resultado.get('estado') if resultado else None
    nombre = resultado.get('nombre') if resultado else None

    if estado == 'TOKEN_INVALIDO':
        return jsonify({"status": "error", "message": "Código QR no reconocido."}), 404

    if estado == 'OK_ENTRADA':
        return jsonify({"status": "success", "message": f"Entrada registrada: {nombre}", "hora": str(resultado.get('hora'))})

    if estado == 'OK_SALIDA':
        return jsonify({"status": "success", "message": f"Salida registrada: {nombre}", "hora": str(resultado.get('hora'))})

    if estado == 'DUPLICADO_ENTRADA':
        return jsonify({"status": "duplicado", "message": f"{nombre} ya registró entrada hoy."}), 409

    if estado == 'DUPLICADO_SALIDA':
        return jsonify({"status": "duplicado", "message": f"{nombre} ya registró salida hoy."}), 409

    if estado == 'SIN_ENTRADA':
        return jsonify({"status": "error", "message": f"{nombre} debe registrar entrada primero."}), 409

    return jsonify({"status": "error", "message": "No se pudo procesar el registro."}), 500