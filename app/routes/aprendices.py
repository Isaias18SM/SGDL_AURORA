import os
import uuid
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, session, request, send_file
from werkzeug.utils import secure_filename
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.utils.decorators import solo_rol
from app.database import (
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
    guardar_soporte_falla,
    generar_recordatorio_sesion_si_corresponde,
    obtener_circulares_recientes
)

aprendiz_bp = Blueprint('aprendiz', __name__)

# Carpeta donde se guardan los PDF de soporte (APR-006).
CARPETA_SOPORTES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'soportes'
)


def _es_pdf_valido(archivo):
    """Valida la extensión y la firma binaria %PDF- de los primeros bytes."""
    nombre = (archivo.filename or '').lower()
    if not nombre.endswith('.pdf'):
        return False
    inicio = archivo.stream.read(5)
    archivo.stream.seek(0)
    return inicio == b'%PDF-'


def _generar_pdf_historial(nombre_aprendiz, historial, resumen, fecha_filtro, estado_filtro):
    """Genera el reporte PDF con el historial de asistencia filtrado."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    estilos = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Reporte de Asistencia - SGDL Aurora", estilos['Title']))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"Aprendiz: {nombre_aprendiz}", estilos['Normal']))
    elementos.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))

    filtros_texto = []
    if fecha_filtro:
        filtros_texto.append(f"Fecha: {fecha_filtro}")
    if estado_filtro and estado_filtro != 'Todos los Estados':
        filtros_texto.append(f"Estado: {estado_filtro}")
    if filtros_texto:
        elementos.append(Paragraph("Filtros aplicados: " + ", ".join(filtros_texto), estilos['Normal']))

    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph(
        f"Resumen: {resumen['presentes']} presente(s), {resumen['fallas']} falla(s), "
        f"{resumen['excusas']} excusa(s), {resumen['retardos']} retardo(s) "
        f"&mdash; {resumen['porcentaje']}% de asistencia acumulada.",
        estilos['Normal']
    ))
    elementos.append(Spacer(1, 16))

    datos_tabla = [["Fecha", "Estado"]]
    for registro in historial:
        fecha = registro['Fecha_Requerida'].strftime('%d/%m/%Y') if registro.get('Fecha_Requerida') else '-'
        datos_tabla.append([fecha, registro.get('Estado', '-')])

    tabla = Table(datos_tabla, colWidths=[8 * cm, 8 * cm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16A34A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer


@aprendiz_bp.context_processor
def inyectar_notificaciones():
    """Inyecta notificaciones globales a las plantillas asociadas."""
    if 'id' in session and session.get('rol') == 'aprendiz':
        generar_recordatorio_sesion_si_corresponde(session['id'])
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
    descargar = request.args.get('descargar') == '1'

    historial = obtener_historial_asistencia(session['id'], fecha_filtro, estado_filtro)
    resumen = calcular_resumen_asistencia(session['id'])
    mensaje = None

    if descargar:
        if not historial:
            mensaje = ('error', 'No hay registros de asistencia disponibles para el período solicitado.')
        else:
            pdf_buffer = _generar_pdf_historial(
                session.get('nombre', ''), historial, resumen, fecha_filtro, estado_filtro
            )
            nombre_archivo = f"asistencia_{session['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=nombre_archivo
            )

    return render_template(
        'asistencia_aprendiz.html',
        active_page='mis_asistencias',
        historial=historial,
        resumen=resumen,
        fecha_filtro=fecha_filtro or '',
        estado_filtro=estado_filtro or 'Todos los Estados',
        mensaje=mensaje
    )


@aprendiz_bp.route('/aprendiz/novedades', methods=['GET', 'POST'])
@solo_rol('aprendiz')
def novedades_aprendiz():
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

            ruta_relativa = f"uploads/soportes/{nombre_archivo}"
            resultado = guardar_soporte_falla(session['id'], fecha_falla, ruta_relativa)
            mensaje = ('exito', resultado['message']) if resultado['ok'] else ('error', resultado['message'])

    return render_template(
        'novedades_aprendiz.html',
        active_page='novedades',
        fallas_pendientes=obtener_fallas_pendientes(session['id']),
        soportes_cargados=obtener_soportes_cargados(session['id']),
        circulares=obtener_circulares_recientes(5),
        mensaje=mensaje
    )


@aprendiz_bp.route('/aprendiz/permisos', methods=['GET', 'POST'])
@solo_rol('aprendiz')
def permisos_aprendiz():
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

            token = fila['Token_QR'] if fila else None

            if fila and not token:
                token = uuid.uuid4().hex
                cur.execute(
                    "UPDATE usuario SET Token_QR = %s WHERE Id_Usuario = %s",
                    (token, session['id'])
                )
                conn.commit()
    finally:
        conn.close()

    return render_template('aprendiz_qr.html', active_page='mi_qr', token=token)


@aprendiz_bp.route('/escanear-qr')
def escanear_qr():
    return render_template('escanear_qr.html')