import pymysql
import pymysql.cursors
from datetime import datetime, date, timedelta

# Configuración global
UMBRAL_RIESGO_ASISTENCIA = 80  # % mínimo de asistencia antes de alertar riesgo académico


def get_db():
    """Retorna una conexión a la base de datos aurora."""
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='',
        database='aurora_sena',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


# ==========================================
# GESTIÓN DE USUARIOS Y AUTENTICACIÓN
# ==========================================

def buscar_usuario(correo, contrasena):
    """Valida credenciales de login y devuelve los datos del usuario."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM `usuario` WHERE CORREO_SENA = %s AND CONTRASENA = %s",
                (correo, contrasena)
            )
            fila = cur.fetchone()
            if fila:
                nombre = f"{fila.get('Nombre', '')} {fila.get('Apellidos', '')}".strip()
                return {
                    'correo': fila['CORREO_SENA'],
                    'nombre': nombre,
                    'rol': fila.get('ROL'),
                    'id': fila.get('Id_Usuario'),
                    'datos': fila
                }
    except Exception as e:
        print(f"[DB ERROR] {e}")
    finally:
        if conn:
            conn.close()
    return None


def buscar_aprendiz_por_documento(documento, tipo_doc=None):
    """Busca un aprendiz por número de documento (y opcionalmente tipo de documento)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if tipo_doc:
                cur.execute("""
                    SELECT Id_Usuario, Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, ROL
                    FROM usuario
                    WHERE No_Documento = %s AND TPI_DOCUMENTO = %s AND ROL = 'Aprendiz'
                """, (documento, tipo_doc))
            else:
                cur.execute("""
                    SELECT Id_Usuario, Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, ROL
                    FROM usuario
                    WHERE No_Documento = %s AND ROL = 'Aprendiz'
                """, (documento,))
            return cur.fetchone()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return None
    finally:
        if conn:
            conn.close()


def actualizar_perfil_usuario(id_usuario, nombre_completo, correo):
    """Actualiza el nombre y correo de un usuario."""
    conn = None
    try:
        partes = nombre_completo.strip().split(' ', 1)
        nombre = partes[0]
        apellidos = partes[1] if len(partes) > 1 else ''

        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Id_Usuario FROM usuario WHERE CORREO_SENA = %s AND Id_Usuario != %s",
                (correo, id_usuario)
            )
            if cur.fetchone():
                return {"ok": False, "message": "Ese correo ya está en uso por otro usuario."}

            cur.execute(
                "UPDATE usuario SET Nombre = %s, Apellidos = %s, CORREO_SENA = %s WHERE Id_Usuario = %s",
                (nombre, apellidos, correo, id_usuario)
            )
            conn.commit()
            return {"ok": True, "message": "Perfil actualizado correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrió un error al guardar en la base de datos."}
    finally:
        if conn:
            conn.close()


# ==========================================
# GESTIÓN DE FICHAS Y APRENDICES
# ==========================================

def obtener_fichas(id_usuario=None):
    """Devuelve las fichas con su programa. Si id_usuario está presente, filtra por instructor."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            if id_usuario:
                cur.execute("""
                    SELECT f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha, p.Nombre AS Programa
                    FROM ficha f
                    JOIN programa p ON f.Id_Programa = p.Id_Programa
                    JOIN usuario_ficha_asignacion ufa 
                         ON ufa.ID_FICHA = f.ID_FICHA AND ufa.Id_Usuario = %s
                    ORDER BY f.No_FICHA
                """, (id_usuario,))
            else:
                cur.execute("""
                    SELECT f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha, p.Nombre AS Programa
                    FROM ficha f
                    JOIN programa p ON f.Id_Programa = p.Id_Programa
                    ORDER BY f.No_FICHA
                """)
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_aprendices_por_ficha(no_ficha, fecha=None):
    """Devuelve los aprendices asignados a una ficha con su estado de asistencia."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    u.Id_Usuario,
                    u.Id_Usuario AS id,
                    CONCAT(u.Nombre, ' ', u.Apellidos) AS nombre,
                    u.No_Documento AS documento,
                    u.ROL AS perfil,
                    f.No_FICHA AS ficha,
                    COALESCE(a.Estado, 'Sin registrar') AS estado
                FROM usuario u
                JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                LEFT JOIN asistencia a 
                    ON a.Id_Usuario = u.Id_Usuario 
                    AND a.Fecha_Requerida = %s
                WHERE f.No_FICHA = %s AND u.ROL = 'Aprendiz'
                GROUP BY u.Id_Usuario
                ORDER BY u.Nombre
            """, (fecha, no_ficha))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


# ==========================================
# ASISTENCIA, REPORTES Y SOPORTES
# ==========================================

def obtener_historial_asistencia(id_usuario, fecha=None, estado=None):
    """Devuelve el historial de asistencia de un aprendiz."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            sql = "SELECT Fecha_Requerida, Estado FROM asistencia WHERE Id_Usuario = %s"
            params = [id_usuario]

            if fecha:
                sql += " AND Fecha_Requerida = %s"
                params.append(fecha)

            if estado and estado != 'Todos los Estados':
                sql += " AND Estado = %s"
                params.append(estado)

            sql += " ORDER BY Fecha_Requerida DESC"
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def calcular_resumen_asistencia(id_usuario):
    """Calcula el porcentaje acumulado de asistencia y riesgo académico."""
    conn = None
    filas = []
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Estado, COUNT(*) AS total FROM asistencia WHERE Id_Usuario = %s GROUP BY Estado",
                (id_usuario,)
            )
            filas = cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    finally:
        if conn:
            conn.close()

    conteo = {fila['Estado']: fila['total'] for fila in filas}
    total_registros = sum(conteo.values())
    presentes = conteo.get('Presente', 0)

    porcentaje = round((presentes / total_registros) * 100, 1) if total_registros > 0 else 100.0
    en_riesgo = total_registros > 0 and porcentaje < UMBRAL_RIESGO_ASISTENCIA

    return {
        "porcentaje": porcentaje,
        "total_registros": total_registros,
        "presentes": presentes,
        "fallas": conteo.get('Falla', 0),
        "excusas": conteo.get('Excusa', 0),
        "retardos": conteo.get('Retardo', 0),
        "en_riesgo": en_riesgo,
        "umbral": UMBRAL_RIESGO_ASISTENCIA
    }


def obtener_asistencias_por_periodo(id_usuario, fecha_inicio, fecha_fin):
    """Obtiene las asistencias de un aprendiz dentro de un rango de fechas."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Id_Asistencia, Id_Usuario, ID_FICHA, Fecha_Requerida, HoraRegistro, HoraSalida, Estado, Soporte_Justificacion
                FROM asistencia
                WHERE Id_Usuario = %s AND Fecha_Requerida BETWEEN %s AND %s
                ORDER BY Fecha_Requerida ASC
            """, (id_usuario, fecha_inicio, fecha_fin))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_estadisticas_instructor(id_instructor, fecha_inicio, fecha_fin, id_ficha=None):
    """Obtiene estadísticas de asistencia de aprendices asignados al instructor."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            sql = """
                SELECT 
                    u.Id_Usuario AS id_aprendiz,
                    CONCAT(u.Nombre, ' ', u.Apellidos) AS aprendiz,
                    f.ID_FICHA,
                    f.No_FICHA AS ficha,
                    COUNT(a.Id_Asistencia) AS total,
                    SUM(CASE WHEN a.Estado = 'Presente' THEN 1 ELSE 0 END) AS presentes,
                    SUM(CASE WHEN a.Estado = 'Falla' THEN 1 ELSE 0 END) AS fallas,
                    SUM(CASE WHEN a.Estado = 'Retardo' THEN 1 ELSE 0 END) AS retardos,
                    SUM(CASE WHEN a.Estado = 'Excusa' THEN 1 ELSE 0 END) AS excusas,
                    ROUND((SUM(CASE WHEN a.Estado = 'Presente' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.Id_Asistencia), 0)) * 100, 2) AS porcentaje
                FROM usuario u
                INNER JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                INNER JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                LEFT JOIN asistencia a ON a.Id_Usuario = u.Id_Usuario AND a.Fecha_Requerida BETWEEN %s AND %s
                WHERE u.ROL = 'Aprendiz' AND u.Activo_SN = '1'
                  AND EXISTS (
                      SELECT 1 FROM usuario_ficha_asignacion ui
                      WHERE ui.Id_Usuario = %s AND ui.ID_FICHA = ufa.ID_FICHA
                  )
            """
            params = [fecha_inicio, fecha_fin, id_instructor]

            if id_ficha:
                sql += " AND f.ID_FICHA = %s"
                params.append(id_ficha)

            sql += " GROUP BY u.Id_Usuario, u.Nombre, u.Apellidos, f.ID_FICHA, f.No_FICHA ORDER BY f.No_FICHA, u.Nombre"

            cur.execute(sql, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_progresion_instructor(id_instructor, fecha_inicio, fecha_fin, id_ficha=None):
    """Obtiene la evolución diaria de asistencia de las fichas del instructor."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            sql = """
                SELECT a.Fecha_Requerida AS fecha, COUNT(a.Id_Asistencia) AS total,
                       SUM(CASE WHEN a.Estado = 'Presente' THEN 1 ELSE 0 END) AS presentes
                FROM asistencia a
                INNER JOIN usuario u ON u.Id_Usuario = a.Id_Usuario
                INNER JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                WHERE u.ROL = 'Aprendiz' AND u.Activo_SN = '1' AND a.Fecha_Requerida BETWEEN %s AND %s
                  AND EXISTS (
                      SELECT 1 FROM usuario_ficha_asignacion ui
                      WHERE ui.Id_Usuario = %s AND ui.ID_FICHA = ufa.ID_FICHA
                  )
            """
            params = [fecha_inicio, fecha_fin, id_instructor]

            if id_ficha:
                sql += " AND ufa.ID_FICHA = %s"
                params.append(id_ficha)

            sql += " GROUP BY a.Fecha_Requerida ORDER BY a.Fecha_Requerida ASC"

            cur.execute(sql, tuple(params))
            filas = cur.fetchall()

            resultado = []
            for fila in filas:
                total = int(fila["total"] or 0)
                presentes = int(fila["presentes"] or 0)
                porcentaje = round((presentes / total) * 100, 2) if total > 0 else 0.0
                resultado.append({
                    "fecha": str(fila["fecha"]),
                    "total": total,
                    "presentes": presentes,
                    "porcentaje": porcentaje
                })
            return resultado
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_fallas_pendientes(id_usuario):
    """Devuelve las fallas sin soporte adjunto."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Fecha_Requerida FROM asistencia
                WHERE Id_Usuario = %s AND Estado = 'Falla' AND Soporte_Justificacion IS NULL
                ORDER BY Fecha_Requerida DESC
            """, (id_usuario,))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_soportes_cargados(id_usuario, limite=10):
    """Devuelve las fallas que ya cuentan con soporte adjunto."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Fecha_Requerida, Soporte_Justificacion, Fecha_Carga_Soporte
                FROM asistencia
                WHERE Id_Usuario = %s AND Soporte_Justificacion IS NOT NULL
                ORDER BY Fecha_Carga_Soporte DESC
                LIMIT %s
            """, (id_usuario, limite))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def guardar_soporte_falla(id_usuario, fecha_requerida, ruta_archivo):
    """Vincula la ruta de un PDF cargado a una falta en la BD."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE asistencia
                SET Soporte_Justificacion = %s, Fecha_Carga_Soporte = %s
                WHERE Id_Usuario = %s AND Fecha_Requerida = %s AND Estado = 'Falla'
            """, (ruta_archivo, datetime.now(), id_usuario, fecha_requerida))
            conn.commit()
            if cur.rowcount == 0:
                return {"ok": False, "message": "No se encontró una falta pendiente para esa fecha."}
            return {"ok": True, "message": "Soporte cargado y vinculado correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrió un error al guardar el soporte."}
    finally:
        if conn:
            conn.close()


def obtener_soportes_para_revision(limite=50):
    """Devuelve las fallas con soporte cargado para revisión del instructor."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.Id_Usuario, CONCAT(u.Nombre, ' ', u.Apellidos) AS aprendiz,
                       f.No_FICHA AS ficha,
                       a.Fecha_Requerida, a.Soporte_Justificacion, a.Fecha_Carga_Soporte
                FROM asistencia a
                JOIN usuario u ON u.Id_Usuario = a.Id_Usuario
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                LEFT JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                WHERE a.Soporte_Justificacion IS NOT NULL
                ORDER BY a.Fecha_Carga_Soporte DESC
                LIMIT %s
            """, (limite,))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


# ==========================================
# SOLICITUDES DE PERMISO Y NOTIFICACIONES
# ==========================================

def crear_solicitud_salida(id_aprendiz, motivo, hora_solicitada):
    """Registra una solicitud de salida anticipada."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO permiso_salida (Id_Aprendiz, Fecha, Hora_Solicitada, Motivo, Estado)
                VALUES (%s, %s, %s, %s, 'Pendiente')
            """, (id_aprendiz, date.today(), hora_solicitada, motivo))
            conn.commit()
            return {"ok": True, "message": "Solicitud enviada correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrió un error al enviar la solicitud."}
    finally:
        if conn:
            conn.close()


def obtener_solicitudes_aprendiz(id_aprendiz):
    """Devuelve el historial de solicitudes de salida de un aprendiz."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Id_Permiso, Fecha, Hora_Solicitada, Motivo, Estado, Fecha_Solicitud, Fecha_Respuesta
                FROM permiso_salida
                WHERE Id_Aprendiz = %s
                ORDER BY Fecha_Solicitud DESC
            """, (id_aprendiz,))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_solicitudes_pendientes():
    """Devuelve las solicitudes pendientes de aprobación."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.Id_Permiso, p.Fecha, p.Hora_Solicitada, p.Motivo, p.Fecha_Solicitud,
                       CONCAT(u.Nombre, ' ', u.Apellidos) AS aprendiz
                FROM permiso_salida p
                JOIN usuario u ON u.Id_Usuario = p.Id_Aprendiz
                WHERE p.Estado = 'Pendiente'
                ORDER BY p.Fecha_Solicitud ASC
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def responder_solicitud_salida(id_permiso, id_instructor, nuevo_estado):
    """Aprueba o rechaza una solicitud de salida anticipada."""
    if nuevo_estado not in ('Aprobado', 'Rechazado'):
        return {"ok": False, "message": "Estado inválido."}

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE permiso_salida
                SET Estado = %s, Id_Instructor = %s, Fecha_Respuesta = %s
                WHERE Id_Permiso = %s AND Estado = 'Pendiente'
            """, (nuevo_estado, id_instructor, datetime.now(), id_permiso))

            if cur.rowcount == 0:
                conn.commit()
                return {"ok": False, "message": "La solicitud ya fue procesada o no existe."}

            cur.execute(
                "SELECT Id_Aprendiz, Hora_Solicitada FROM permiso_salida WHERE Id_Permiso = %s",
                (id_permiso,)
            )
            solicitud = cur.fetchone()
            conn.commit()

        if solicitud:
            mensaje = f"Tu solicitud de salida anticipada de las {solicitud['Hora_Solicitada']} fue {nuevo_estado.lower()}."
            crear_notificacion(solicitud['Id_Aprendiz'], mensaje, enlace='/aprendiz/permisos')

        return {"ok": True, "message": f"Solicitud {nuevo_estado.lower()} correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrió un error al procesar la solicitud."}
    finally:
        if conn:
            conn.close()


def crear_notificacion(id_usuario, mensaje, enlace=None):
    """Crea una notificación para un usuario."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO notificaciones (Id_Usuario, Mensaje, Enlace)
                VALUES (%s, %s, %s)
            """, (id_usuario, mensaje, enlace))
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def obtener_notificaciones(id_usuario, limite=8):
    """Obtiene las últimas notificaciones enviadas a un usuario."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Id_Notificacion, Mensaje, Enlace, Leida, Fecha_Creacion
                FROM notificaciones
                WHERE Id_Usuario = %s
                ORDER BY Fecha_Creacion DESC
                LIMIT %s
            """, (id_usuario, limite))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def contar_notificaciones_no_leidas(id_usuario):
    """Cuenta cuántas notificaciones tiene sin leer un usuario."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total FROM notificaciones WHERE Id_Usuario = %s AND Leida = 0",
                (id_usuario,)
            )
            fila = cur.fetchone()
            return fila['total'] if fila else 0
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return 0
    finally:
        if conn:
            conn.close()


def marcar_notificaciones_leidas(id_usuario):
    """Marca como leídas todas las notificaciones pendientes de un usuario."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notificaciones SET Leida = 1 WHERE Id_Usuario = %s AND Leida = 0",
                (id_usuario,)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# ==========================================
# RECORDATORIOS Y PROGRAMACIÓN DE SESIONES
# ==========================================

MINUTOS_RECORDATORIO_SESION = 15


def obtener_sesiones_hoy(id_usuario):
    """Devuelve las sesiones asociadas al aprendiz para la fecha actual."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.ID_ASIGNACION, a.HORA_INICIO, a.HORA_FINALIZACION
                FROM asignacion a
                JOIN usuario_ficha_asignacion ufa ON ufa.ID_ASIGNACION = a.ID_ASIGNACION
                JOIN trimestre t ON t.Id_Trimestre = a.Id_Trimestre
                WHERE ufa.Id_Usuario = %s
                  AND CURDATE() BETWEEN t.Fecha_Inicio AND t.Fecha_Fin
                ORDER BY a.HORA_INICIO ASC
            """, (id_usuario,))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def ya_registro_asistencia_hoy(id_usuario):
    """Verifica si el aprendiz ya marcó asistencia durante el día."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM asistencia WHERE Id_Usuario = %s AND Fecha_Requerida = CURDATE() LIMIT 1",
                (id_usuario,)
            )
            return cur.fetchone() is not None
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return False
    finally:
        if conn:
            conn.close()


def _minutos_desde_medianoche(valor_hora):
    """Normaliza columnas TIME a minutos desde medianoche."""
    if isinstance(valor_hora, timedelta):
        return valor_hora.seconds // 60
    return valor_hora.hour * 60 + valor_hora.minute


def generar_recordatorio_sesion_si_corresponde(id_usuario):
    """Envía un recordatorio de asistencia próximo al inicio de clase."""
    sesiones = obtener_sesiones_hoy(id_usuario)
    if not sesiones or ya_registro_asistencia_hoy(id_usuario):
        return

    ahora_minutos = datetime.now().hour * 60 + datetime.now().minute

    for sesion in sesiones:
        inicio_minutos = _minutos_desde_medianoche(sesion['HORA_INICIO'])
        faltan = inicio_minutos - ahora_minutos

        if 0 <= faltan <= MINUTOS_RECORDATORIO_SESION:
            enlace = f"recordatorio-sesion-{sesion['ID_ASIGNACION']}-{date.today().isoformat()}"

            conn = None
            try:
                conn = get_db()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM notificaciones WHERE Id_Usuario = %s AND Enlace = %s LIMIT 1",
                        (id_usuario, enlace)
                    )
                    ya_avisado = cur.fetchone() is not None
            except Exception as e:
                print(f"[DB ERROR] {e}")
                ya_avisado = True
            finally:
                if conn:
                    conn.close()

            if not ya_avisado:
                crear_notificacion(
                    id_usuario,
                    f"Tu sesión inicia en {faltan} minuto(s). Recuerda registrar tu asistencia.",
                    enlace
                )
            break


# ==========================================
# CIRCULARES Y NOVEDADES ACADÉMICAS
# ==========================================

def crear_circular(id_usuario, titulo, cuerpo):
    """Crea una nueva circular emitida por un instructor o coordinador."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO circular (Id_Autor, Titulo, Mensaje, Fecha_Publicacion)
                VALUES (%s, %s, %s, %s)
            """, (id_usuario, titulo, cuerpo, datetime.now()))
            conn.commit()
            return {"ok": True, "message": "Circular publicada correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrió un error al publicar la circular."}
    finally:
        if conn:
            conn.close()


def obtener_circulares_recientes(limite=20):
    """Devuelve las circulares publicadas más recientes."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.Id_Circular, c.Titulo, c.Mensaje, c.Fecha_Publicacion,
                       CONCAT(u.Nombre, ' ', u.Apellidos) AS autor_nombre,
                       u.ROL AS autor_rol
                FROM circular c
                JOIN usuario u ON u.Id_Usuario = c.Id_Autor
                ORDER BY c.Fecha_Publicacion DESC
                LIMIT %s
            """, (limite,))
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def crear_novedad(id_instructor, titulo, mensaje, id_ficha=None, tipo='Alerta'):
    """Registra una novedad enviada por un instructor a la coordinación."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO novedad (Id_Instructor, Id_Ficha, Tipo, Titulo, Mensaje, Estado)
                VALUES (%s, %s, %s, %s, %s, 'Pendiente')
            """, (id_instructor, id_ficha, tipo, titulo, mensaje))
            conn.commit()
            return {'ok': True, 'message': 'Novedad enviada al coordinador correctamente.'}
    except Exception as e:
        print(f"[ERROR NOVEDAD]: {e}")
        if conn:
            conn.rollback()
        return {'ok': False, 'message': 'No se pudo enviar la novedad.'}
    finally:
        if conn:
            conn.close()


def obtener_novedades_pendientes():
    """Obtiene las novedades reportadas pendientes de atención."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT n.Id_Novedad, n.Tipo, n.Titulo, n.Mensaje, n.Estado, n.Fecha_Creacion,
                       CONCAT(u.Nombre, ' ', u.Apellidos) AS instructor,
                       f.No_FICHA AS ficha
                FROM novedad n
                JOIN usuario u ON u.Id_Usuario = n.Id_Instructor
                LEFT JOIN ficha f ON f.ID_FICHA = n.Id_Ficha
                WHERE n.Estado = 'Pendiente'
                ORDER BY n.Fecha_Creacion DESC
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"[ERROR NOVEDAD]: {e}")
        return []
    finally:
        if conn:
            conn.close()


def marcar_novedad_resuelta(id_novedad, id_coordinador):
    """Actualiza el estado de una novedad a Resuelto."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE novedad
                SET Estado = 'Resuelto',
                    Fecha_Resolucion = NOW(),
                    Id_Coordinador_Resuelve = %s
                WHERE Id_Novedad = %s AND Estado = 'Pendiente'
            """, (id_coordinador, id_novedad))
            filas_afectadas = cur.rowcount
            conn.commit()

            if filas_afectadas == 0:
                return {'ok': False, 'message': 'La novedad ya fue resuelta o no existe.'}
            return {'ok': True, 'message': 'Novedad marcada como resuelta.'}
    except Exception as e:
        print(f"[ERROR NOVEDAD]: {e}")
        if conn:
            conn.rollback()
        return {'ok': False, 'message': 'No se pudo actualizar la novedad.'}
    finally:
        if conn:
            conn.close()