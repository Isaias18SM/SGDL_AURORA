import os
from flask import Blueprint, render_template, session, request
from werkzeug.utils import secure_filename
from decorators import solo_rol
from database import (
    get_db,
    obtener_historial_asistencia,
    calcular_resumen_asistencia,
    crear_solicitud_salida,
    obtener_solicitudes_aprendiz,
    obtener_notificaciones,
    contar_notificaciones_no_leidas,
    marcar_notificaciones_leidas,
    obtener_fallas_pendientes,
    obtener_soportes_cargados,
    guardar_soporte_falla
)

aprendiz_bp = Blueprint('aprendiz', __name__)

# Carpeta donde se guardan los PDF de soporte (APR-006). Se calcula con
# ruta absoluta para que funcione sin importar desde donde se lance app.py.
CARPETA_SOPORTES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads', 'soportes'
)


def _es_pdf_valido(archivo):
    """Valida que el archivo subido sea realmente un PDF: revisa la extension
    Y la firma binaria %PDF- de los primeros bytes (un .pdf falso con otro
    contenido no pasa esta validacion, APR-006 #2)."""
    nombre = (archivo.filename or '').lower()
    if not nombre.endswith('.pdf'):
        return False
    inicio = archivo.stream.read(5)
    archivo.stream.seek(0)  # devolvemos el puntero al inicio para poder guardar el archivo despues
    return inicio == b'%PDF-'


@aprendiz_bp.context_processor
def inyectar_notificaciones():
    """Pone las notificaciones disponibles en TODAS las plantillas que use
    base_aprendiz.html, sin tener que pasarlas manualmente en cada vista.
    Se ejecuta en cada request atendido por este blueprint."""
    if 'id' in session and session.get('rol') == 'aprendiz':
        return dict(
            notif_no_leidas=contar_notificaciones_no_leidas(session['id']),
            notif_recientes=obtener_notificaciones(session['id'])
        )
    return dict(notif_no_leidas=0, notif_recientes=[])

@aprendiz_bp.route('/aprendiz/dashboard')
@solo_rol('aprendiz')
def dashboard_aprendiz():
    resumen = calcular_resumen_asistencia(session['id'])
    return render_template('dashboard_aprendiz.html', active_page='dashboard', resumen=resumen)

@aprendiz_bp.route('/aprendiz/asistencia')
@solo_rol('aprendiz')
def asistencia_aprendiz():
    fecha_filtro = request.args.get('fecha') or None
    estado_filtro = request.args.get('estado') or None

    historial = obtener_historial_asistencia(session['id'], fecha_filtro, estado_filtro)
    resumen = calcular_resumen_asistencia(session['id'])

    return render_template(
        'asistencia_aprendiz.html',
        active_page='mis_asistencias',
        historial=historial,
        resumen=resumen,
        fecha_filtro=fecha_filtro or '',
        estado_filtro=estado_filtro or 'Todos los Estados'
    )

@aprendiz_bp.route('/aprendiz/novedades', methods=['GET', 'POST'])
@solo_rol('aprendiz')
def novedades_aprendiz():
    """APR-006: el aprendiz sube el soporte (PDF) de una falta ya registrada."""
    mensaje = None
    if request.method == 'POST':
        fecha_falla = request.form.get('fecha_falla', '').strip()
        archivo = request.files.get('soporte')

        if not fecha_falla or not archivo or archivo.filename == '':
            mensaje = ('error', 'Selecciona la falta a justificar y adjunta un archivo.')
        elif not _es_pdf_valido(archivo):
            mensaje = ('error', 'El sistema rechazó el archivo: solo se aceptan documentos en formato PDF.')
        else:
            os.makedirs(CARPETA_SOPORTES, exist_ok=True)
            nombre_archivo = secure_filename(f"{session['id']}_{fecha_falla}_{archivo.filename}")
            archivo.save(os.path.join(CARPETA_SOPORTES, nombre_archivo))

            # Ruta relativa a /static, para poder armarla despues con url_for('static', filename=...)
            ruta_relativa = f"uploads/soportes/{nombre_archivo}"
            resultado = guardar_soporte_falla(session['id'], fecha_falla, ruta_relativa)
            mensaje = ('exito', resultado['message']) if resultado['ok'] else ('error', resultado['message'])

    return render_template(
        'novedades_aprendiz.html',
        active_page='novedades',
        fallas_pendientes=obtener_fallas_pendientes(session['id']),
        soportes_cargados=obtener_soportes_cargados(session['id']),
        mensaje=mensaje
    )


@aprendiz_bp.route('/aprendiz/permisos', methods=['GET', 'POST'])
@solo_rol('aprendiz')
def permisos_aprendiz():
    """APR-005: el aprendiz solicita salida anticipada y consulta el estado de sus solicitudes."""
    mensaje = None
    if request.method == 'POST':
        motivo = request.form.get('motivo', '').strip()
        hora_solicitada = request.form.get('hora_solicitada', '').strip()

        if not motivo or not hora_solicitada:
            mensaje = ('error', 'Debes indicar el motivo y la hora de salida.')
        else:
            resultado = crear_solicitud_salida(session['id'], motivo, hora_solicitada)
            mensaje = ('exito', resultado['message']) if resultado['ok'] else ('error', resultado['message'])

    solicitudes = obtener_solicitudes_aprendiz(session['id'])
    return render_template(
        'permiso_aprendiz.html',
        active_page='permisos',
        solicitudes=solicitudes,
        mensaje=mensaje
    )


@aprendiz_bp.route('/aprendiz/notificaciones/leidas', methods=['POST'])
@solo_rol('aprendiz')
def marcar_notificaciones():
    """Se llama por fetch() cuando el aprendiz abre la campanita, para
    marcar sus notificaciones como leidas y bajar el contador del badge."""
    marcar_notificaciones_leidas(session['id'])
    return ('', 204)


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