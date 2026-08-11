from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from functools import wraps
from datetime import datetime
import csv
import io
import pymysql


# Especifica que static está dentro de la carpeta 'app'
app = Flask(__name__, static_folder='app/static')
app.secret_key = 'aurora_sena_secret_2026'

# ══════════════════════════════════════════════════════════════════════════════
# DATOS MOCK — PORTAL COORDINADOR
# Viven en memoria mientras el servidor está corriendo (se reinician al
# reiniciar la app). En producción, reemplazar por tablas reales
# `instructor`, `ficha` y `aprendiz` en la base de datos.
# ══════════════════════════════════════════════════════════════════════════════
INSTRUCTORES_MOCK = [
    {"id": 1, "nombre": "Carlos Ramírez",       "correo": "c.ramirez@sena.edu.co",  "especialidad": "Desarrollo de Software"},
    {"id": 2, "nombre": "María Fernanda López", "correo": "mf.lopez@sena.edu.co",   "especialidad": "Contabilidad y Finanzas"},
    {"id": 3, "nombre": "Jorge Iván Torres",    "correo": "ji.torres@sena.edu.co",  "especialidad": "Redes y Telecomunicaciones"},
]

FICHAS_MOCK = [
    {"codigo": "2557908", "programa": "Análisis y Desarrollo de Software",           "jornada": "Diurna",   "aprendices_activos": 35, "instructor_id": 1},
    {"codigo": "2557909", "programa": "Análisis y Desarrollo de Software",           "jornada": "Nocturna", "aprendices_activos": 32, "instructor_id": None},
    {"codigo": "2612345", "programa": "Contabilización de Operaciones Comerciales",  "jornada": "Mixta",    "aprendices_activos": 28, "instructor_id": 2},
    {"codigo": "2698741", "programa": "Redes de Computadores y Seguridad",           "jornada": "Diurna",   "aprendices_activos": 30, "instructor_id": None},
]

# Datos mock de aprendices, compartidos entre el portal Instructor y el
# portal Coordinador (el coordinador puede agregar aprendices nuevos aquí).
APRENDICES_MOCK = [
    {"id": 1, "nombre": "Ana Gomez",       "documento": "2250597075",  "perfil": "Aprendiz", "estado": "Presente", "ficha": "2557908"},
    {"id": 2, "nombre": "Luis Rodriguez",  "documento": "224204312",   "perfil": "Aprendiz", "estado": "Falla",    "ficha": "2557908"},
    {"id": 3, "nombre": "María Turranez",  "documento": "25502511106", "perfil": "Aprendiz", "estado": "Excusa",   "ficha": "2557908"},
    {"id": 4, "nombre": "Carlos Mendoza",  "documento": "224204313",   "perfil": "Aprendiz", "estado": "Retardo",  "ficha": "2557909"},
    {"id": 5, "nombre": "Laura Pérez",     "documento": "255027512",   "perfil": "Aprendiz", "estado": "Presente", "ficha": "2557909"},
]

# ══════════════════════════════════════════════════════════════════════════════
# CONEXIÓN A BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
def get_db():
    """Retorna una conexión a la base de datos aurora."""
    return pymysql.connect(
        host='127.0.0.1',
        user='root',          # Cambia si tu usuario MySQL es diferente
        password='',          # Cambia si tienes contraseña en MySQL
        database='aurora',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def buscar_usuario(correo, contrasena):
    """
    Busca el correo y contraseña en las tres tablas (aprendiz, instructor,
    coordinador). Devuelve un dict con los datos del usuario y su rol,
    o None si no se encontró.
    """
    tablas = [
        ('aprendiz',    'aprendiz'),
        ('instructor',  'instructor'),
        ('coordinador', 'coordinador'),
    ]
    try:
        conn = get_db()
        with conn.cursor() as cur:
            for tabla, rol in tablas:
                cur.execute(
                    f"SELECT * FROM `{tabla}` WHERE CORREO_SENA = %s AND CONTRASENA = %s",
                    (correo, contrasena)
                )
                fila = cur.fetchone()
                if fila:
                    # Construir nombre completo
                    nombre = f"{fila.get('NOMBRES', '')} {fila.get('APELLIDOS', '')}".strip()
                    return {
                        'correo': fila['CORREO_SENA'],
                        'nombre': nombre,
                        'rol':    rol,
                        'id':     fila.get(f'ID_{tabla.upper()}'),
                        'datos':  fila
                    }
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# DECORADORES
# ══════════════════════════════════════════════════════════════════════════════
def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'correo' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def solo_rol(*roles):
    """Protege una ruta para que solo la accedan ciertos roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'correo' not in session:
                return redirect(url_for('login'))
            if session.get('rol') not in roles:
                return redirect(url_for('dashboard_segun_rol'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def solo_rol_api(*roles):
    """
    Igual que solo_rol, pero pensado para endpoints JSON/AJAX: en vez de
    redirigir, responde con un error JSON y el código HTTP correspondiente.
    Se usa para proteger la Búsqueda Avanzada, que solo debe ser visible
    y utilizable por el rol Instructor.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'correo' not in session:
                return jsonify({"status": "error", "message": "Debes iniciar sesión."}), 401
            if session.get('rol') not in roles:
                return jsonify({"status": "error", "message": "Acceso restringido solo para Instructores."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya tiene sesión activa, redirigir al dashboard correspondiente
    if 'correo' in session:
        return redirect(url_for('dashboard_segun_rol'))

    error = None
    if request.method == 'POST':
        correo    = request.form.get('correo', '').strip().lower()
        contrasena = request.form.get('contrasena', '')

        usuario = buscar_usuario(correo, contrasena)

        if usuario:
            session['correo'] = usuario['correo']
            session['nombre'] = usuario['nombre']
            session['rol']    = usuario['rol']
            session['id']     = usuario['id']
            return redirect(url_for('dashboard_segun_rol'))
        else:
            error = 'Correo o contraseña incorrectos. Verifica tus datos.'

    return render_template('login.html', error=error)


@app.route('/ir-dashboard')
@login_requerido
def dashboard_segun_rol():
    """Redirige al dashboard correcto según el rol en sesión."""
    rol = session.get('rol')
    if rol == 'aprendiz':
        return redirect(url_for('dashboard_aprendiz'))
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/recuperar-contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    """
    Página de recuperación de contraseña. El aprendiz/usuario ingresa su
    correo institucional y (en un entorno productivo) recibiría un enlace
    de recuperación por correo. Aquí se deja el flujo listo para conectar
    un servicio de envío de correos real (p. ej. Flask-Mail / SMTP).
    """
    mensaje = None
    error = None

    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()

        if not correo or '@' not in correo:
            error = 'Ingresa un correo institucional válido.'
        else:
            # TODO: integrar el envío real del enlace de recuperación
            # (ej. Flask-Mail) usando un token temporal firmado.
            # Por seguridad, se muestra siempre el mismo mensaje exista o
            # no el correo en la base de datos.
            mensaje = f'Si el correo "{correo}" está registrado, recibirás un enlace de recuperación en unos minutos.'

    return render_template('recuperar_contrasena.html', mensaje=mensaje, error=error)


# ══════════════════════════════════════════════════════════════════════════════
# PORTAL INSTRUCTOR / COORDINADOR
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/dashboard')
@solo_rol('instructor', 'coordinador')
def dashboard():
    """
    Pantalla de bienvenida del Instructor/Coordinador.
    Ya no muestra métricas ni estadísticas: es una vista de bienvenida a
    pantalla completa con saludo dinámico según la hora del día.
    """
    hora_actual = datetime.now().hour
    if 5 <= hora_actual < 12:
        saludo = "Buenos días"
    elif 12 <= hora_actual < 19:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    ahora = datetime.now()
    fecha_hoy = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}"

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        saludo=saludo,
        fecha_hoy=fecha_hoy
    )


@app.route('/fichas')
@solo_rol('instructor')
def fichas():
    return render_template('fichas.html', active_page='fichas')


@app.route('/lista-asistencia', methods=['GET', 'POST'])
@solo_rol('instructor')
def lista_asistencia():
    # Datos mock mientras no hay asistencia real cargada.
    # Cada aprendiz queda asociado a una ficha para que el botón
    # "Consultar Fichas" pueda filtrar correctamente al seleccionar una.
    ficha_seleccionada = request.args.get('ficha', '').strip()

    if ficha_seleccionada:
        aprendices = [a for a in APRENDICES_MOCK if a['ficha'] == ficha_seleccionada]
    else:
        # Sin filtro explícito, se muestra la ficha activa por defecto
        aprendices = APRENDICES_MOCK
        ficha_seleccionada = APRENDICES_MOCK[0]['ficha'] if APRENDICES_MOCK else None

    return render_template(
        'lista.html',
        active_page='lista',
        aprendices=aprendices,
        ficha_seleccionada=ficha_seleccionada
    )


@app.route('/reportes')
@solo_rol('instructor')
def modulos():
    return render_template('modulos.html', active_page='reportes')


@app.route('/novedades')
@solo_rol('instructor')
def novedades():
    return render_template('novedades.html', active_page='novedades')


@app.route('/historial')
@solo_rol('instructor')
def historial():
    return render_template('historial.html', active_page='historial')


@app.route('/configuracion', methods=['GET', 'POST'])
@login_requerido
def configuracion():
    user_info = {
        "nombre": session.get('nombre', 'Usuario'),
        "email":  session.get('correo', ''),
        "rol":    session.get('rol', '')
    }
    return render_template('configuracion.html', active_page='config', user=user_info)


@app.route('/api/buscar-aprendiz')
@solo_rol_api('instructor')
def api_buscar_aprendiz():
    """
    Búsqueda Avanzada de Aprendices — SOLO por número de documento
    (Cédula de Ciudadanía "CC" o Tarjeta de Identidad "TI").
    Ruta accesible únicamente para el rol Instructor (ver solo_rol_api).

    NOTA: se asume que la tabla `aprendiz` tiene las columnas
    TIPO_DOCUMENTO ('CC'/'TI') y NUMERO_DOCUMENTO. Ajusta esos nombres
    de columna si tu esquema real de base de datos es distinto.
    """
    documento = request.args.get('documento', '').strip()
    tipo = request.args.get('tipo', '').strip().upper()

    if not documento or not documento.isdigit():
        return jsonify({
            "status": "error",
            "message": "Ingresa únicamente el número de documento (CC o TI)."
        }), 400

    if tipo not in ('CC', 'TI'):
        tipo = None  # Si no se especifica, se busca en ambos tipos válidos

    try:
        conn = get_db()
        with conn.cursor() as cur:
            if tipo:
                cur.execute(
                    "SELECT * FROM aprendiz WHERE NUMERO_DOCUMENTO = %s AND TIPO_DOCUMENTO = %s",
                    (documento, tipo)
                )
            else:
                cur.execute(
                    "SELECT * FROM aprendiz WHERE NUMERO_DOCUMENTO = %s AND TIPO_DOCUMENTO IN ('CC', 'TI')",
                    (documento,)
                )
            fila = cur.fetchone()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return jsonify({"status": "error", "message": "Error al consultar la base de datos."}), 500

    if not fila:
        return jsonify({
            "status": "not_found",
            "message": "No se encontró ningún aprendiz con ese número de documento."
        }), 404

    nombre = f"{fila.get('NOMBRES', '')} {fila.get('APELLIDOS', '')}".strip()
    return jsonify({
        "status": "success",
        "aprendiz": {
            "id":                fila.get('ID_APRENDIZ'),
            "nombre":            nombre,
            "tipo_documento":    fila.get('TIPO_DOCUMENTO'),
            "numero_documento":  fila.get('NUMERO_DOCUMENTO'),
            "correo":            fila.get('CORREO_SENA'),
            "ficha":             fila.get('FICHA'),
        }
    })


@app.route('/api/fichas')
@solo_rol_api('instructor')
def api_fichas():
    """
    Devuelve el listado de fichas para que el instructor elija una y
    consulte los aprendices registrados en ese grupo (botón "Consultar
    Fichas" en la barra superior). Ruta accesible solo para Instructores.

    NOTA: por ahora se usan datos de ejemplo, igual que en fichas() y
    lista_asistencia(). En producción, reemplaza este bloque por una
    consulta real, p. ej.:
        SELECT CODIGO_FICHA, PROGRAMA, JORNADA, ID_INSTRUCTOR
        FROM ficha WHERE ID_INSTRUCTOR = %s
    """
    fichas_mock = [
        {"codigo": f["codigo"], "programa": f["programa"], "jornada": f["jornada"], "aprendices_activos": f["aprendices_activos"]}
        for f in FICHAS_MOCK
    ]
    return jsonify({"status": "success", "fichas": fichas_mock})


@app.route('/api/cambiar-estado', methods=['POST'])
@login_requerido
def api_cambiar_estado():
    data = request.get_json()
    return jsonify({"status": "success", "message": "Estado actualizado correctamente"})


# ══════════════════════════════════════════════════════════════════════════════
# PORTAL COORDINADOR
# Interfaz propia del Coordinador: en vez de "Fichas" administra
# Instructores (y su asignación a fichas), y en vez de tomar asistencia
# puede registrar aprendices (manual o carga masiva por CSV). El resto de
# secciones (lista, reportes, novedades, historial) tienen su propia
# plantilla y ruta, independientes del portal Instructor.
# ══════════════════════════════════════════════════════════════════════════════
def _ficha_por_codigo(codigo):
    return next((f for f in FICHAS_MOCK if f['codigo'] == codigo), None)


def _instructor_por_id(instructor_id):
    return next((i for i in INSTRUCTORES_MOCK if i['id'] == instructor_id), None)


@app.route('/coordinador/instructores')
@solo_rol('coordinador')
def coordinador_instructores():
    fichas_libres = [f for f in FICHAS_MOCK if not f['instructor_id']]

    instructores = []
    for ins in INSTRUCTORES_MOCK:
        fichas_asignadas = [f for f in FICHAS_MOCK if f['instructor_id'] == ins['id']]
        instructores.append({**ins, 'fichas': fichas_asignadas})

    return render_template(
        'instructores.html',
        active_page='instructores',
        instructores=instructores,
        fichas_libres=fichas_libres
    )


@app.route('/coordinador/instructores/asignar', methods=['POST'])
@solo_rol('coordinador')
def coordinador_asignar_ficha():
    instructor_id = request.form.get('instructor_id', type=int)
    ficha_codigo = request.form.get('ficha_codigo', '').strip()

    ficha = _ficha_por_codigo(ficha_codigo)
    instructor = _instructor_por_id(instructor_id)

    if not ficha or not instructor:
        flash('No se pudo realizar la asignación. Verifica los datos e intenta de nuevo.', 'error')
    elif ficha['instructor_id']:
        flash(f"La ficha {ficha['codigo']} ya tiene un instructor asignado.", 'error')
    else:
        ficha['instructor_id'] = instructor['id']
        flash(f"Ficha {ficha['codigo']} asignada correctamente a {instructor['nombre']}.", 'success')

    return redirect(url_for('coordinador_instructores'))


@app.route('/coordinador/instructores/desasignar', methods=['POST'])
@solo_rol('coordinador')
def coordinador_desasignar_ficha():
    ficha_codigo = request.form.get('ficha_codigo', '').strip()
    ficha = _ficha_por_codigo(ficha_codigo)

    if ficha:
        ficha['instructor_id'] = None
        flash(f"Se liberó la ficha {ficha['codigo']}. Ya puede asignarse a otro instructor.", 'success')
    else:
        flash('No se encontró la ficha indicada.', 'error')

    return redirect(url_for('coordinador_instructores'))


@app.route('/coordinador/aprendices')
@solo_rol('coordinador')
def coordinador_aprendices():
    return render_template(
        'aprendices.html',
        active_page='aprendices',
        fichas=FICHAS_MOCK,
        aprendices=APRENDICES_MOCK
    )


@app.route('/coordinador/aprendices/manual', methods=['POST'])
@solo_rol('coordinador')
def coordinador_aprendiz_manual():
    nombres      = request.form.get('nombres', '').strip()
    apellidos    = request.form.get('apellidos', '').strip()
    numero_doc   = request.form.get('numero_documento', '').strip()
    ficha        = request.form.get('ficha', '').strip()

    if not nombres or not apellidos or not numero_doc or not ficha:
        flash('Completa nombres, apellidos, número de documento y ficha para registrar al aprendiz.', 'error')
        return redirect(url_for('coordinador_aprendices'))

    nuevo_id = max((a['id'] for a in APRENDICES_MOCK), default=0) + 1
    APRENDICES_MOCK.append({
        "id": nuevo_id,
        "nombre": f"{nombres} {apellidos}",
        "documento": numero_doc,
        "perfil": "Aprendiz",
        "estado": "Presente",
        "ficha": ficha,
    })
    flash(f"Aprendiz {nombres} {apellidos} registrado correctamente en la ficha {ficha}.", 'success')
    return redirect(url_for('coordinador_aprendices'))


@app.route('/coordinador/aprendices/masivo', methods=['POST'])
@solo_rol('coordinador')
def coordinador_aprendices_masivo():
    """
    Carga masiva de aprendices desde un archivo CSV.
    Columnas esperadas: nombres, apellidos, tipo_documento, numero_documento,
    correo, ficha. Si una fila no trae "ficha", se usa la ficha destino
    seleccionada en el formulario para todas las filas sin ese dato.
    """
    archivo = request.files.get('archivo_csv')
    ficha_destino = request.form.get('ficha_masivo', '').strip()

    if not archivo or archivo.filename == '':
        flash('Selecciona un archivo CSV para la carga masiva.', 'error')
        return redirect(url_for('coordinador_aprendices'))

    if not archivo.filename.lower().endswith('.csv'):
        flash('El archivo debe tener formato .csv', 'error')
        return redirect(url_for('coordinador_aprendices'))

    try:
        contenido = archivo.read().decode('utf-8-sig')
        lector = csv.DictReader(io.StringIO(contenido))

        # Normaliza los nombres de columna (minúsculas, sin espacios extra)
        if lector.fieldnames:
            lector.fieldnames = [c.strip().lower() for c in lector.fieldnames]

        siguiente_id = max((a['id'] for a in APRENDICES_MOCK), default=0)
        creados = 0
        omitidos = 0

        for fila in lector:
            nombres    = (fila.get('nombres') or '').strip()
            apellidos  = (fila.get('apellidos') or '').strip()
            numero_doc = (fila.get('numero_documento') or '').strip()
            ficha      = (fila.get('ficha') or '').strip() or ficha_destino

            if not nombres or not apellidos or not numero_doc or not ficha:
                omitidos += 1
                continue

            siguiente_id += 1
            APRENDICES_MOCK.append({
                "id": siguiente_id,
                "nombre": f"{nombres} {apellidos}",
                "documento": numero_doc,
                "perfil": "Aprendiz",
                "estado": "Presente",
                "ficha": ficha,
            })
            creados += 1

        if creados:
            mensaje = f"Se cargaron {creados} aprendiz(ces) correctamente."
            if omitidos:
                mensaje += f" ({omitidos} fila(s) con datos incompletos fueron omitidas)."
            flash(mensaje, 'success')
        else:
            flash('No se pudo registrar ningún aprendiz. Verifica que el archivo tenga las columnas correctas y datos completos.', 'error')

    except Exception as e:
        print(f"[CSV ERROR] {e}")
        flash('Ocurrió un error al procesar el archivo. Verifica que sea un CSV válido.', 'error')

    return redirect(url_for('aprendices'))


@app.route('/coordinador/lista-asistencia')
@solo_rol('coordinador')
def coordinador_lista_asistencia():
    ficha_filtro = request.args.get('ficha', '').strip()

    if ficha_filtro:
        aprendices = [a for a in APRENDICES_MOCK if a['ficha'] == ficha_filtro]
    else:
        aprendices = APRENDICES_MOCK

    return render_template(
        'lista_coordinador.html',
        active_page='lista',
        aprendices=aprendices,
        fichas=FICHAS_MOCK,
        ficha_filtro=ficha_filtro
    )


@app.route('/coordinador/reportes')
@solo_rol('coordinador')
def coordinador_reportes():
    return render_template(
        'reportes_coordinador.html',
        active_page='reportes',
        fichas=FICHAS_MOCK,
        instructores=INSTRUCTORES_MOCK
    )


@app.route('/coordinador/novedades')
@solo_rol('coordinador')
def coordinador_novedades():
    return render_template('novedades_coordinador.html', active_page='novedades')


@app.route('/coordinador/historial')
@solo_rol('coordinador')
def coordinador_historial():
    # NOTA: el archivo real en templates/ se llama 'historia_coordinador.html'
    # (sin la "l" de "historial") — se ajustó aquí para que coincida.
    return render_template(
        'historia_coordinador.html',
        active_page='historial',
        fichas=FICHAS_MOCK,
        instructores=INSTRUCTORES_MOCK
    )


# ══════════════════════════════════════════════════════════════════════════════
# PORTAL APRENDIZ
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/aprendiz/dashboard')
@solo_rol('aprendiz')
def dashboard_aprendiz():
    return render_template('dashboard_aprendiz.html', active_page='dashboard')


@app.route('/aprendiz/asistencia')
@solo_rol('aprendiz')
def asistencia_aprendiz():
    return render_template('asistencia_aprendiz.html', active_page='mis_asistencias')


@app.route('/aprendiz/novedades')
@solo_rol('aprendiz')
def novedades_aprendiz():
    return render_template('novedades_aprendiz.html', active_page='novedades')


if __name__ == '__main__':
    app.run(debug=True, port=5000)