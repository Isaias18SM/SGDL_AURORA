import pymysql
import pymysql.cursors


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


def obtener_fichas():
    """Devuelve todas las fichas con su programa."""
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
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
                    u.Id_Usuario,
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


UMBRAL_RIESGO_ASISTENCIA = 80  # % minimo de asistencia antes de alertar riesgo academico


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