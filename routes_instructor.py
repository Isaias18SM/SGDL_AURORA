from datetime import datetime
from flask import Blueprint, render_template, request, session
from decorators import solo_rol, login_requerido

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
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    ahora = datetime.now()
    fecha_hoy = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}"

    return render_template('dashboard.html', active_page='dashboard', saludo=saludo, fecha_hoy=fecha_hoy)

@instructor_bp.route('/fichas')
@solo_rol('instructor', 'coordinador')
def fichas():
    return render_template('fichas.html', active_page='fichas')

@instructor_bp.route('/lista-asistencia', methods=['GET', 'POST'])
@solo_rol('instructor', 'coordinador')
def lista_asistencia():
    aprendices_mock = [
        {"id": 1, "nombre": "Ana Gomez", "documento": "2250597075", "perfil": "Aprendiz", "estado": "Presente", "ficha": "2557908"},
        {"id": 2, "nombre": "Luis Rodriguez", "documento": "224204312", "perfil": "Aprendiz", "estado": "Falla", "ficha": "2557908"},
        {"id": 3, "nombre": "María Turranez", "documento": "25502511106", "perfil": "Aprendiz", "estado": "Excusa", "ficha": "2557908"},
        {"id": 4, "nombre": "Carlos Mendoza", "documento": "224204313", "perfil": "Aprendiz", "estado": "Retardo", "ficha": "2557909"},
        {"id": 5, "nombre": "Laura Pérez", "documento": "255027512", "perfil": "Aprendiz", "estado": "Presente", "ficha": "2557909"},
    ]

    ficha_seleccionada = request.args.get('ficha', '').strip()
    if ficha_seleccionada:
        aprendices = [a for a in aprendices_mock if a['ficha'] == ficha_seleccionada]
    else:
        aprendices = aprendices_mock
        ficha_seleccionada = aprendices_mock[0]['ficha'] if aprendices_mock else None

    return render_template('lista.html', active_page='lista', aprendices=aprendices, ficha_seleccionada=ficha_seleccionada)

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
    user_info = {
        "nombre": session.get('nombre', 'Usuario'),
        "email": session.get('correo', ''),
        "rol": session.get('rol', '')
    }
    return render_template('configuracion.html', active_page='config', user=user_info)