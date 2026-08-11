import pymysql
import pymysql.cursors

def get_db():
    """Retorna una conexión a la base de datos aurora."""
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='',
        database='aurora',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def buscar_usuario(correo, contrasena):
    tablas = [
        ('aprendiz', 'aprendiz'),
        ('instructor', 'instructor'),
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
                    nombre = f"{fila.get('NOMBRES', '')} {fila.get('APELLIDOS', '')}".strip()
                    return {
                        'correo': fila['CORREO_SENA'],
                        'nombre': nombre,
                        'rol': rol,
                        'id': fila.get(f'ID_{tabla.upper()}'),
                        'datos': fila
                    }
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")
    return None