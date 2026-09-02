from flask import Blueprint, render_template, request, redirect, url_for, session
from app.database import buscar_usuario
from app.utils.decorators import login_requerido

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'correo' in session:
        return redirect(url_for('auth.dashboard_segun_rol'))

    error = None
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        contrasena = request.form.get('contrasena', '')
        usuario = buscar_usuario(correo, contrasena)

        if usuario:
            session['correo'] = usuario['correo']
            session['nombre'] = usuario['nombre']
            session['rol'] = usuario['rol'].lower().strip()
            session['id'] = usuario['id']
            return redirect(url_for('auth.dashboard_segun_rol'))
        else:
            error = 'Correo o contraseña incorrectos. Verifica tus datos.'

    return render_template('login.html', error=error)


@auth_bp.route('/ir-dashboard')
@login_requerido
def dashboard_segun_rol():
    rol = session.get('rol', '').lower().strip()

    if rol == 'aprendiz':
        return redirect(
            url_for('aprendiz.dashboard_aprendiz')
        )

    elif rol == 'instructor':
        return redirect(
            url_for('instructor.dashboard')
        )

    elif rol == 'coordinador':
        return redirect(
            url_for('coordinador.lista_coordinador')
        )

    else:
        session.clear()
        return redirect(
            url_for('auth.login')
        )


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/recuperar-contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    mensaje = None
    error = None
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        if not correo or '@' not in correo:
            error = 'Ingresa un correo institucional válido.'
        else:
            mensaje = f'Si el correo "{correo}" está registrado, recibirás un enlace de recuperación en unos minutos.'

    return render_template('recuperar_contrasena.html', mensaje=mensaje, error=error)