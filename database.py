import pymysql
import pymysql.cursors
from datetime import datetime, date, timedelta


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
                    'rol': fila.get('ROL'),          # Coordinador / Instructor / Aprendiz
                    'id': fila.get('Id_Usuario'),
                    'datos': fila
                }
    except Exception as e:
        print(f"[DB ERROR] {e}")
    finally:
        if conn:
            conn.close()
    return None


def obtener_fichas(id_usuario=None):
    """Devuelve las fichas con su programa. Si se pasa id_usuario, solo las
    fichas asignadas a ese usuario (instructor); si no, todas (coordinador)."""
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
    """Devuelve los aprendices reales de una ficha, con su estado de asistencia en 'fecha'.
    Requiere que la tabla `asistencia` tenga las columnas Id_Usuario y Estado
    (ver el ALTER TABLE en fix_asistencia.sql)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
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


def obtener_historial_asistencia(id_usuario, fecha=None, estado=None):
    """Devuelve el historial de asistencia de un aprendiz, con filtros opcionales de fecha y estado."""
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


UMBRAL_RIESGO_ASISTENCIA = 80  # % minimo de asistencia antes de alertar riesgo academico


def calcular_resumen_asistencia(id_usuario):
    """Calcula presentes/fallas/excusas/retardos, el % de asistencia acumulado y si el
    aprendiz esta en riesgo academico por inasistencia excesiva (criterio APR-003 #14)."""
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
    en_riesgo = porcentaje < UMBRAL_RIESGO_ASISTENCIA

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
    """Actualiza el nombre y correo de un usuario (instructor/coordinador)."""
    conn = None
    try:
        # La tabla separa Nombre y Apellidos, así que dividimos el texto ingresado
        partes = nombre_completo.strip().split(' ', 1)
        nombre = partes[0]
        apellidos = partes[1] if len(partes) > 1 else ''

        conn = get_db()
        with conn.cursor() as cur:
            # Evita guardar el correo si ya lo tiene otro usuario
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


def crear_solicitud_salida(id_aprendiz, motivo, hora_solicitada):
    """Registra una nueva solicitud de salida anticipada en estado Pendiente (APR-005 #1)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO permiso_salida (Id_Aprendiz, Fecha, Hora_Solicitada, Motivo, Estado)
                   VALUES (%s, %s, %s, %s, 'Pendiente')""",
                (id_aprendiz, date.today(), hora_solicitada, motivo)
            )
            conn.commit()
            return {"ok": True, "message": "Solicitud de salida anticipada enviada."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrio un error al enviar la solicitud."}
    finally:
        if conn:
            conn.close()


def obtener_solicitudes_aprendiz(id_aprendiz):
    """Devuelve el historial de solicitudes de salida de un aprendiz, mas recientes primero."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT Id_Permiso, Fecha, Hora_Solicitada, Motivo, Estado, Fecha_Solicitud, Fecha_Respuesta
                   FROM permiso_salida
                   WHERE Id_Aprendiz = %s
                   ORDER BY Fecha_Solicitud DESC""",
                (id_aprendiz,)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_solicitudes_pendientes():
    """Devuelve todas las solicitudes de salida pendientes de aprobacion, con el nombre del aprendiz.
    (No se filtra por instructor: el proyecto aun no tiene una asignacion instructor-ficha
    en el codigo, igual que en lista_asistencia(); todos los instructores ven todas las fichas)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT p.Id_Permiso, p.Fecha, p.Hora_Solicitada, p.Motivo, p.Fecha_Solicitud,
                          CONCAT(u.Nombre, ' ', u.Apellidos) AS aprendiz
                   FROM permiso_salida p
                   JOIN usuario u ON u.Id_Usuario = p.Id_Aprendiz
                   WHERE p.Estado = 'Pendiente'
                   ORDER BY p.Fecha_Solicitud ASC"""
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def responder_solicitud_salida(id_permiso, id_instructor, nuevo_estado):
    """Aprueba o rechaza una solicitud de salida anticipada (APR-005 #2).
    nuevo_estado debe ser 'Aprobado' o 'Rechazado'. Ademas de actualizar el
    estado, crea una notificacion para el aprendiz dueño de la solicitud."""
    if nuevo_estado not in ('Aprobado', 'Rechazado'):
        return {"ok": False, "message": "Estado invalido."}

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE permiso_salida
                   SET Estado = %s, Id_Instructor = %s, Fecha_Respuesta = %s
                   WHERE Id_Permiso = %s AND Estado = 'Pendiente'""",
                (nuevo_estado, id_instructor, datetime.now(), id_permiso)
            )

            if cur.rowcount == 0:
                conn.commit()
                return {"ok": False, "message": "La solicitud ya fue procesada o no existe."}

            # Recuperamos el aprendiz dueño de la solicitud para poder notificarlo
            cur.execute(
                "SELECT Id_Aprendiz, Hora_Solicitada FROM permiso_salida WHERE Id_Permiso = %s",
                (id_permiso,)
            )
            solicitud = cur.fetchone()
            conn.commit()

        # La notificacion se crea en su propia conexion/transaccion (crear_notificacion
        # abre y cierra su propia conexion), asi que un fallo aqui no revierte la
        # aprobacion/rechazo que ya quedo guardada arriba.
        if solicitud:
            mensaje = (
                f"Tu solicitud de salida anticipada de las {solicitud['Hora_Solicitada']} "
                f"fue {nuevo_estado.lower()}."
            )
            crear_notificacion(solicitud['Id_Aprendiz'], mensaje, enlace='/aprendiz/permisos')

        return {"ok": True, "message": f"Solicitud {nuevo_estado.lower()} correctamente."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrio un error al procesar la solicitud."}
    finally:
        if conn:
            conn.close()


def crear_notificacion(id_usuario, mensaje, enlace=None):
    """Crea una notificacion en el buzon de un usuario (usada por APR-005 #2
    para avisarle al aprendiz que su permiso fue aprobado o rechazado)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO notificaciones (Id_Usuario, Mensaje, Enlace)
                   VALUES (%s, %s, %s)""",
                (id_usuario, mensaje, enlace)
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


def obtener_notificaciones(id_usuario, limite=8):
    """Devuelve las notificaciones mas recientes de un usuario (para la campanita)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT Id_Notificacion, Mensaje, Enlace, Leida, Fecha_Creacion
                   FROM notificaciones
                   WHERE Id_Usuario = %s
                   ORDER BY Fecha_Creacion DESC
                   LIMIT %s""",
                (id_usuario, limite)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def contar_notificaciones_no_leidas(id_usuario):
    """Cuenta las notificaciones sin leer de un usuario, para el badge de la campanita."""
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
    """Marca como leidas todas las notificaciones pendientes de un usuario."""
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


MINUTOS_RECORDATORIO_SESION = 15  # APR-009: ventana de aviso antes del inicio de la sesion


def obtener_sesiones_hoy(id_usuario):
    """APR-009: devuelve las sesiones (asignaciones) programadas para HOY para
    este aprendiz, segun su ficha/asignacion dentro del trimestre vigente.
    Lista vacia si no tiene ninguna programada para hoy (criterio #2)."""
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
    """APR-009: True si el aprendiz ya tiene un registro de asistencia (de
    cualquier estado) para hoy, para no mandarle el recordatorio si ya
    marco su asistencia."""
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
    """Normaliza una columna TIME de MySQL a minutos desde medianoche.
    pymysql devuelve columnas TIME como timedelta; lo cubrimos junto con
    time/datetime por si el driver cambia de comportamiento."""
    if isinstance(valor_hora, timedelta):
        return valor_hora.seconds // 60
    return valor_hora.hour * 60 + valor_hora.minute


def generar_recordatorio_sesion_si_corresponde(id_usuario):
    """APR-009: si el aprendiz tiene una sesion programada para hoy y faltan
    <= MINUTOS_RECORDATORIO_SESION minutos para que inicie, le crea UNA
    notificacion en su buzon recordandole registrar su asistencia (criterio #1).
    No hace nada si: no tiene sesiones hoy (criterio #2), ya registro
    asistencia hoy, o ya se le mando el recordatorio para esa sesion."""
    sesiones = obtener_sesiones_hoy(id_usuario)
    if not sesiones:
        return  # criterio #2: sin sesiones programadas, no se genera recordatorio

    if ya_registro_asistencia_hoy(id_usuario):
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
                ya_avisado = True  # ante la duda, no duplicamos el aviso
            finally:
                if conn:
                    conn.close()

            if not ya_avisado:
                crear_notificacion(
                    id_usuario,
                    f"Tu sesión inicia en {faltan} minuto(s). Recuerda registrar tu asistencia.",
                    enlace
                )
            break  # ya evaluamos la sesion mas proxima; no seguimos con las demas


def obtener_fallas_pendientes(id_usuario):
    """Devuelve las fechas de las fallas del aprendiz que todavia no tienen
    un soporte cargado (para llenar el select del formulario, APR-006)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT Fecha_Requerida FROM asistencia
                   WHERE Id_Usuario = %s AND Estado = 'Falla' AND Soporte_Justificacion IS NULL
                   ORDER BY Fecha_Requerida DESC""",
                (id_usuario,)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def obtener_soportes_cargados(id_usuario, limite=10):
    """Devuelve las fallas del aprendiz que ya tienen un soporte de
    justificacion cargado, mas recientes primero (APR-006)."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT Fecha_Requerida, Soporte_Justificacion, Fecha_Carga_Soporte
                   FROM asistencia
                   WHERE Id_Usuario = %s AND Soporte_Justificacion IS NOT NULL
                   ORDER BY Fecha_Carga_Soporte DESC
                   LIMIT %s""",
                (id_usuario, limite)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()


def guardar_soporte_falla(id_usuario, fecha_requerida, ruta_archivo):
    """Vincula la ruta del PDF cargado al registro de falta correspondiente
    (APR-006 #1). Solo actualiza si esa fecha en verdad es una Falla del
    aprendiz, para que no se pueda "justificar" una fecha que no le pertenece."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE asistencia
                   SET Soporte_Justificacion = %s, Fecha_Carga_Soporte = %s
                   WHERE Id_Usuario = %s AND Fecha_Requerida = %s AND Estado = 'Falla'""",
                (ruta_archivo, datetime.now(), id_usuario, fecha_requerida)
            )
            conn.commit()
            if cur.rowcount == 0:
                return {"ok": False, "message": "No se encontro una falta pendiente para esa fecha."}
            return {"ok": True, "message": "Soporte cargado y vinculado correctamente a tu falta."}
    except Exception as e:
        print(f"[DB ERROR] {e}")
        if conn:
            conn.rollback()
        return {"ok": False, "message": "Ocurrio un error al guardar el soporte."}
    finally:
        if conn:
            conn.close()
def crear_circular(id_usuario, titulo, cuerpo):
    """Crea una nueva circular/novedad publicada por un instructor o coordinador."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO circular (Id_Usuario, Titulo, Cuerpo, Fecha_Creacion)
                   VALUES (%s, %s, %s, %s)""",
                (id_usuario, titulo, cuerpo, datetime.now())
            )
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


def crear_circular(id_usuario, titulo, cuerpo):
    """Crea una nueva circular/novedad publicada por un instructor o coordinador."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO circular (Id_Autor, Titulo, Mensaje, Fecha_Publicacion)
                   VALUES (%s, %s, %s, %s)""",
                (id_usuario, titulo, cuerpo, datetime.now())
            )
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
    """Devuelve las circulares más recientes, con el nombre y rol de quien las publicó."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT c.Id_Circular, c.Titulo, c.Mensaje, c.Fecha_Publicacion,
                          CONCAT(u.Nombre, ' ', u.Apellidos) AS autor_nombre,
                          u.ROL AS autor_rol
                   FROM circular c
                   JOIN usuario u ON u.Id_Usuario = c.Id_Autor
                   ORDER BY c.Fecha_Publicacion DESC
                   LIMIT %s""",
                (limite,)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()

def obtener_soportes_para_revision(limite=50):
    """Devuelve las fallas con soporte PDF ya cargado por los aprendices,
    para que el instructor pueda revisarlas."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT a.Id_Usuario, CONCAT(u.Nombre, ' ', u.Apellidos) AS aprendiz,
                          f.No_FICHA AS ficha,
                          a.Fecha_Requerida, a.Soporte_Justificacion, a.Fecha_Carga_Soporte
                   FROM asistencia a
                   JOIN usuario u ON u.Id_Usuario = a.Id_Usuario
                   LEFT JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                   LEFT JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                   WHERE a.Soporte_Justificacion IS NOT NULL
                   ORDER BY a.Fecha_Carga_Soporte DESC
                   LIMIT %s""",
                (limite,)
            )
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
    finally:
        if conn:
            conn.close()