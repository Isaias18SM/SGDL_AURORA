from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for

from app.utils.decorators import solo_rol, login_requerido
from app.database import (
    obtener_fichas,
    obtener_aprendices_por_ficha,
    actualizar_perfil_usuario,
    obtener_solicitudes_pendientes,
    responder_solicitud_salida,
    crear_circular,
    obtener_circulares_recientes,
    obtener_soportes_para_revision,
    crear_novedad
)

instructor_bp = Blueprint('instructor', __name__)

ESTADOS_VALIDOS = ['Presente', 'Falla', 'Retardo', 'Excusa']
TIPOS_NOVEDAD_VALIDOS = ['Alerta', 'Excusa', 'Inasistencia', 'Otro']


@instructor_bp.route('/dashboard')
@solo_rol('instructor', 'coordinador')
def dashboard():
    hora_actual = datetime.now().hour
    if 5 <= hora_actual < 12:
        saludo = "Buenos días"
    elif 12 <= hora_actual < 19:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    ahora = datetime.now()
    fecha_hoy = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}"

    return render_template('dashboard.html', active_page='dashboard', saludo=saludo, fecha_hoy=fecha_hoy)


@instructor_bp.route('/lista-asistencia', methods=['GET', 'POST'])
@solo_rol('instructor', 'coordinador')
def lista_asistencia():
    # Si el usuario es instructor, filtra por sus fichas asignadas
    usuario_id = session.get('id') if session.get('rol') == 'instructor' else None
    fichas = obtener_fichas(usuario_id)

    ficha_seleccionada = request.args.get('ficha', '').strip()
    if not ficha_seleccionada and fichas:
        ficha_seleccionada = fichas[0]['No_FICHA']

    fecha = request.args.get('fecha') or datetime.now().strftime('%Y-%m-%d')

    aprendices = obtener_aprendices_por_ficha(ficha_seleccionada, fecha) if ficha_seleccionada else []

    return render_template(
        'lista.html',
        active_page='lista',
        aprendices=aprendices,
        fichas=fichas,
        ficha_seleccionada=ficha_seleccionada,
        fecha=fecha,
        estados_validos=ESTADOS_VALIDOS
    )


@instructor_bp.route('/reportes')
@solo_rol('instructor', 'coordinador')
def modulos():
    return render_template('modulos.html', active_page='reportes')


@instructor_bp.route('/novedades', methods=['GET', 'POST'])
@solo_rol('instructor', 'coordinador')
def novedades():
    mensaje = None

    if request.method == 'POST':
        accion = request.form.get('accion')

        # --- Publicar circular ---
        if accion == 'circular':
            titulo = request.form.get('titulo', '').strip()
            cuerpo = request.form.get('mensaje', '').strip()

            if not titulo or not cuerpo:
                mensaje = ('error', 'Debes indicar el título y el mensaje de la circular.')
            else:
                resultado = crear_circular(session['id'], titulo, cuerpo)
                mensaje = ('exito', resultado['message']) if resultado['ok'] else ('error', resultado['message'])

        # --- Enviar novedad al coordinador (SOLO instructor) ---
        elif accion == 'novedad':
            if session.get('rol') != 'instructor':
                mensaje = ('error', 'Solo los instructores pueden enviar novedades al coordinador.')
            else:
                titulo = request.form.get('novedad_titulo', '').strip()
                cuerpo = request.form.get('novedad_mensaje', '').strip()
                tipo = request.form.get('novedad_tipo', 'Alerta').strip()
                ficha_raw = request.form.get('novedad_ficha', '').strip()
                id_ficha = int(ficha_raw) if ficha_raw.isdigit() else None

                if tipo not in TIPOS_NOVEDAD_VALIDOS:
                    tipo = 'Alerta'

                if not titulo or not cuerpo:
                    mensaje = ('error', 'Debes indicar el título y el mensaje de la novedad.')
                else:
                    resultado = crear_novedad(
                        id_instructor=session['id'],
                        titulo=titulo,
                        mensaje=cuerpo,
                        id_ficha=id_ficha,
                        tipo=tipo
                    )
                    mensaje = ('exito', resultado['message']) if resultado['ok'] else ('error', resultado['message'])

    # Fichas del instructor, usadas en el selector del formulario de novedad
    usuario_id = session.get('id') if session.get('rol') == 'instructor' else None
    fichas = obtener_fichas(usuario_id) if session.get('rol') == 'instructor' else []

    return render_template(
        'novedades.html',
        active_page='novedades',
        circulares=obtener_circulares_recientes(20),
        soportes=obtener_soportes_para_revision(),
        fichas=fichas,
        tipos_novedad=TIPOS_NOVEDAD_VALIDOS,
        mensaje=mensaje
    )


@instructor_bp.route('/historial')
@solo_rol('instructor', 'coordinador')
def historial():
    return render_template('historial.html', active_page='historial')


@instructor_bp.route('/instructor/permisos')
@solo_rol('instructor', 'coordinador')
def permisos_instructor():
    """APR-005: el instructor revisa y aprueba/rechaza solicitudes de salida anticipada."""
    solicitudes = obtener_solicitudes_pendientes()
    return render_template('permisos_instructor.html', active_page='permisos', solicitudes=solicitudes)


@instructor_bp.route('/instructor/permisos/<int:id_permiso>/responder', methods=['POST'])
@solo_rol('instructor', 'coordinador')
def responder_permiso(id_permiso):
    nuevo_estado = request.form.get('estado', '').strip()
    responder_solicitud_salida(id_permiso, session.get('id'), nuevo_estado)
    return redirect(url_for('instructor.permisos_instructor'))


@instructor_bp.route('/configuracion', methods=['GET', 'POST'])
@login_requerido
def configuracion():
    mensaje = None
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()

        if not nombre or not email or '@' not in email:
            mensaje = ('error', 'Verifica que el nombre y el correo sean válidos.')
        else:
            resultado = actualizar_perfil_usuario(session.get('id'), nombre, email)
            if resultado['ok']:
                session['nombre'] = nombre
                session['correo'] = email
                mensaje = ('exito', resultado['message'])
            else:
                mensaje = ('error', resultado['message'])

    user_info = {
        "nombre": session.get('nombre', 'Usuario'),
        "email": session.get('correo', ''),
        "rol": session.get('rol', '')
    }
    return render_template('configuracion.html', active_page='config', user=user_info, mensaje=mensaje)