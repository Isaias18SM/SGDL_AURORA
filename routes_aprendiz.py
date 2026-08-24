from flask import Blueprint, render_template, session
from decorators import solo_rol
from database import get_db

aprendiz_bp = Blueprint('aprendiz', __name__)

@aprendiz_bp.route('/aprendiz/dashboard')
@solo_rol('aprendiz')
def dashboard_aprendiz():
    return render_template('dashboard_aprendiz.html', active_page='dashboard')

@aprendiz_bp.route('/aprendiz/asistencia')
@solo_rol('aprendiz')
def asistencia_aprendiz():
    return render_template('asistencia_aprendiz.html', active_page='mis_asistencias')

@aprendiz_bp.route('/aprendiz/novedades')
@solo_rol('aprendiz')
def novedades_aprendiz():
    return render_template('novedades_aprendiz.html', active_page='novedades')


@aprendiz_bp.route('/aprendiz/mi-qr')
@solo_rol('aprendiz')
def mi_qr():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Token_QR FROM usuario WHERE Id_Usuario = %s", (session['id'],))
            fila = cur.fetchone()
    finally:
        conn.close()

    token = fila['Token_QR'] if fila else None
    return render_template('aprendiz_qr.html', active_page='mi_qr', token=token)


@aprendiz_bp.route('/escanear-qr')
def escanear_qr():
    # Página pública tipo "kiosco": no requiere sesión porque quien
    # se identifica es el QR (token), no el usuario del navegador.
    return render_template('escanear_qr.html')