"""
app/routes/lista.py

Ruta para la vista "Lista de Asistencia". El endpoint que cambia el
estado y registra la entrada está centralizado en app/routes/api.py.
"""

from flask import Blueprint, render_template, request, session
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



