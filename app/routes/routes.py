from flask import Blueprint, render_template
from utils import validar_datos
from models import consultar_registros

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    registros = consultar_registros()
    return render_template('index.html', registros=registros)