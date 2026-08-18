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