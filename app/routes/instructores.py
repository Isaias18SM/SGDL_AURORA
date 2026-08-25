from datetime import datetime
from flask import Blueprint, render_template, request, session
from app.utils.decorators import solo_rol, login_requerido
from app.database import obtener_fichas, obtener_aprendices_por_ficha, actualizar_perfil_usuario 

instructor_bp = Blueprint('instructor', __name__)



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
    fichas = obtener_fichas()

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
        fecha=fecha
    )


@instructor_bp.route('/reportes')
@solo_rol('instructor', 'coordinador')
def modulos():
    return render_template('modulos.html', active_page='reportes')


@instructor_bp.route('/novedades')
@solo_rol('instructor', 'coordinador')
def novedades():
    return render_template('novedades.html', active_page='novedades')


@instructor_bp.route('/historial')
@solo_rol('instructor', 'coordinador')
def historial():
    return render_template('historial.html', active_page='historial')


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
                # Refleja el cambio también en la sesión activa
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