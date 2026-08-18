from flask import Blueprint, render_template
from app.utils.decorators import solo_rol

aprendiz_bp = Blueprint('aprendiz', __name__)

@aprendiz_bp.route('/Aprendiz/dashboard')
@solo_rol('aprendiz')
def dashboard_aprendiz():
    return render_template('dashboard_aprendiz.html', active_page='dashboard')

@aprendiz_bp.route('/aprendiz/asistencia')
@solo_rol('aprendiz')
def asistencia_aprendiz():
    return render_template('asistencia_aprendiz.html', active_page='mis_asistencias')

@aprendiz_bp.route('/Aprendiz/novedades')
@solo_rol('aprendiz')
def novedades_aprendiz():
    return render_template('novedades_aprendiz.html', active_page='novedades')