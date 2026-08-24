"""
app/routes/lista.py

Ruta para la vista "Lista de Asistencia" y el endpoint que cambia el
estado de un aprendiz (Presente / Falla / Retardo / Excusa) desde el
menú de acciones. Usa pymysql directamente a través de app/database.py
(NO usa SQLAlchemy, ya que el proyecto no lo tiene configurado).
"""

from flask import Blueprint, render_template, request, jsonify, session
from datetime import date
from app.database import get_db, obtener_aprendices_por_ficha

lista_bp = Blueprint('lista', __name__)

ESTADOS_VALIDOS = ['Presente', 'Falla', 'Retardo', 'Excusa']


@lista_bp.route('/lista', methods=['GET'])
def lista_asistencia():
    """
    Muestra la lista de asistencia de la ficha activa (guardada en
    sesión) para el día de hoy.
    """
    ficha_seleccionada = session.get('ficha_activa') or request.args.get('ficha')
    hoy = date.today()

    aprendices = []
    if ficha_seleccionada:
        aprendices = obtener_aprendices_por_ficha(ficha_seleccionada, hoy)

    return render_template(
        'lista.html',
        aprendices=aprendices,
        ficha_seleccionada=ficha_seleccionada,
        estados_validos=ESTADOS_VALIDOS
    )


@lista_bp.route('/api/cambiar-estado', methods=['POST'])
def cambiar_estado():
    """
    Recibe { id, estado } vía JSON y guarda/actualiza el registro de
    asistencia del día para ese usuario.
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify(status='error', message='No se recibió información válida.'), 400

    id_usuario = data.get('id')
    nuevo_estado = data.get('estado')

    if id_usuario is None or not nuevo_estado:
        return jsonify(status='error', message='Faltan datos (id o estado).'), 400

    if nuevo_estado not in ESTADOS_VALIDOS:
        return jsonify(status='error', message=f'Estado "{nuevo_estado}" no es válido.'), 400

    hoy = date.today()
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # Requiere una llave única (Id_Usuario, Fecha_Requerida) en la
            # tabla `asistencia` para que ON DUPLICATE KEY funcione.
            # Ver nota más abajo si aún no la tienes.
            cur.execute(
                """
                INSERT INTO asistencia (Id_Usuario, Fecha_Requerida, HoraRegistro, Estado)
                VALUES (%s, %s, NOW(), %s)
                ON DUPLICATE KEY UPDATE Estado = VALUES(Estado), HoraRegistro = NOW()
                """,
                (id_usuario, hoy, nuevo_estado)
            )
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[DB ERROR] {e}")
        return jsonify(status='error', message='Error al guardar en la base de datos.'), 500
    finally:
        if conn:
            conn.close()

    return jsonify(status='success', id=id_usuario, estado=nuevo_estado)