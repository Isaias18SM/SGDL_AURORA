from flask import Blueprint, request, jsonify,session
from app.database import get_db
from app.utils.decorators import solo_rol_api, login_requerido
from datetime import date
import calendar
from app.database import obtener_historial_asistencia
from app.services.asistencia_estadistica_service import (calcular_estadistica, generar_progresion)
from app.database import (obtener_asistencias_por_periodo, obtener_estadisticas_instructor, obtener_progresion_instructor)


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

#API para la logica de las estadisticas

@api_bp.route('/api/aprendiz/estadisticas')
@solo_rol_api('aprendiz')
def estadisticas_aprendiz():

    id_usuario = session.get('id')

    periodo = request.args.get(
        'periodo',
        'mes'
    ).lower()

    try:

        anio = int(
            request.args.get(
                'anio',
                date.today().year
            )
        )

        mes = int(
            request.args.get(
                'mes',
                date.today().month
            )
        )

        trimestre = int(
            request.args.get(
                'trimestre',
                ((mes - 1) // 3) + 1
            )
        )

    except ValueError:

        return jsonify({
            "status": "error",
            "message": "Los parámetros de fecha no son válidos."
        }), 400

    # ==========================
    # MES
    # ==========================

    if periodo == 'mes':

        if not 1 <= mes <= 12:

            return jsonify({
                "status": "error",
                "message": "Mes inválido."
            }), 400

        fecha_inicio = date(
            anio,
            mes,
            1
        )

        ultimo_dia = calendar.monthrange(
            anio,
            mes
        )[1]

        fecha_fin = date(
            anio,
            mes,
            ultimo_dia
        )

    # ==========================
    # TRIMESTRE
    # ==========================

    elif periodo == 'trimestre':

        if not 1 <= trimestre <= 4:

            return jsonify({
                "status": "error",
                "message": "Trimestre inválido."
            }), 400

        mes_inicio = (
            (trimestre - 1) * 3
        ) + 1

        mes_fin = mes_inicio + 2

        fecha_inicio = date(
            anio,
            mes_inicio,
            1
        )

        fecha_fin = date(
            anio,
            mes_fin,
            calendar.monthrange(
                anio,
                mes_fin
            )[1]
        )

    # ==========================
    # AÑO
    # ==========================

    elif periodo == 'anio':

        fecha_inicio = date(
            anio,
            1,
            1
        )

        fecha_fin = date(
            anio,
            12,
            31
        )

    else:

        return jsonify({
            "status": "error",
            "message": "Periodo inválido."
        }), 400

    # ==========================
    # CONSULTA REAL A BD
    # ==========================

    asistencias = obtener_asistencias_por_periodo(
        id_usuario,
        fecha_inicio,
        fecha_fin
    )

    estadistica = calcular_estadistica(
        asistencias
    )

    progresion = generar_progresion(
        asistencias
    )

    return jsonify({
        "status": "success",
        "periodo": periodo,
        "anio": anio,
        "mes": mes if periodo == "mes" else None,
        "trimestre": trimestre if periodo == "trimestre" else None,
        "fecha_inicio": str(fecha_inicio),
        "fecha_fin": str(fecha_fin),
        "estadistica": estadistica,
        "progresion": progresion
    })
    
@api_bp.route('/api/instructor/estadisticas')
@solo_rol_api('instructor')
def estadisticas_instructor():

    id_instructor = session.get('id')

    periodo = request.args.get(
        'periodo',
        'mes'
    ).lower()

    try:

        anio = int(
            request.args.get(
                'anio',
                date.today().year
            )
        )

        mes = int(
            request.args.get(
                'mes',
                date.today().month
            )
        )

        trimestre = int(
            request.args.get(
                'trimestre',
                ((mes - 1) // 3) + 1
            )
        )

        id_ficha = request.args.get(
            'ficha',
            ''
        ).strip()

        if id_ficha:
            id_ficha = int(id_ficha)
        else:
            id_ficha = None

    except ValueError:

        return jsonify({
            "status": "error",
            "message": "Los parámetros enviados no son válidos."
        }), 400

    # ==========================
    # MES
    # ==========================

    if periodo == 'mes':

        if not 1 <= mes <= 12:

            return jsonify({
                "status": "error",
                "message": "Mes inválido."
            }), 400

        fecha_inicio = date(
            anio,
            mes,
            1
        )

        fecha_fin = date(
            anio,
            mes,
            calendar.monthrange(
                anio,
                mes
            )[1]
        )

    # ==========================
    # TRIMESTRE
    # ==========================

    elif periodo == 'trimestre':

        if not 1 <= trimestre <= 4:

            return jsonify({
                "status": "error",
                "message": "Trimestre inválido."
            }), 400

        mes_inicio = (
            (trimestre - 1) * 3
        ) + 1

        mes_fin = mes_inicio + 2

        fecha_inicio = date(
            anio,
            mes_inicio,
            1
        )

        fecha_fin = date(
            anio,
            mes_fin,
            calendar.monthrange(
                anio,
                mes_fin
            )[1]
        )

    # ==========================
    # AÑO
    # ==========================

    elif periodo == 'anio':

        fecha_inicio = date(
            anio,
            1,
            1
        )

        fecha_fin = date(
            anio,
            12,
            31

        )

    else:

        return jsonify({
            "status": "error",
            "message": "Periodo inválido."
        }), 400

    # ==========================
    # ESTADÍSTICAS
    # ==========================

    aprendices = obtener_estadisticas_instructor(
        id_instructor,
        fecha_inicio,
        fecha_fin,
        id_ficha
    )

    progresion = obtener_progresion_instructor(
        id_instructor,
        fecha_inicio,
        fecha_fin,
        id_ficha
    )

    # ==========================
    # RESUMEN GENERAL
    # ==========================

    total = sum(
        int(a["total"] or 0)
        for a in aprendices
    )

    presentes = sum(
        int(a["presentes"] or 0)
        for a in aprendices
    )

    fallas = sum(
        int(a["fallas"] or 0)
        for a in aprendices
    )

    retardos = sum(
        int(a["retardos"] or 0)
        for a in aprendices
    )

    excusas = sum(
        int(a["excusas"] or 0)
        for a in aprendices
    )

    porcentaje = round(
        (presentes / total) * 100,
        2
    ) if total > 0 else 0

    return jsonify({
        "status": "success",

        "periodo": periodo,

        "anio": anio,

        "fecha_inicio": str(fecha_inicio),

        "fecha_fin": str(fecha_fin),

        "resumen": {
            "total": total,
            "presentes": presentes,
            "fallas": fallas,
            "retardos": retardos,
            "excusas": excusas,
            "porcentaje": porcentaje
        },

        "aprendices": [
            {
                "id": a["id_aprendiz"],
                "nombre": a["aprendiz"],
                "ficha": a["ficha"],
                "total": int(a["total"] or 0),
                "presentes": int(a["presentes"] or 0),
                "fallas": int(a["fallas"] or 0),
                "retardos": int(a["retardos"] or 0),
                "excusas": int(a["excusas"] or 0),
                "porcentaje": float(
                    a["porcentaje"] or 0
                )
            }
            for a in aprendices
        ],

        "progresion": progresion
    })