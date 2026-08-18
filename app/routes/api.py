from flask import Blueprint, request, jsonify
from app.database import get_db
from app.utils.decorators import solo_rol_api, login_requerido

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
                SELECT f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha,
                       COUNT(ufa.Id_Usuario) AS aprendices_activos
                FROM ficha f
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                LEFT JOIN usuario u ON u.Id_Usuario = ufa.Id_Usuario AND u.ROL = 'Aprendiz' AND u.Activo_SN = '1'
                GROUP BY f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha
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
@login_requerido
def api_cambiar_estado():
    return jsonify({"status": "success", "message": "Estado actualizado correctamente"})