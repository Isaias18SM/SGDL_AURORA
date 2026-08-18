import csv
import io

from flask import Blueprint, render_template, request, redirect, url_for, flash
from decorators import solo_rol
from database import get_db

coordinador = Blueprint('coordinador', __name__)


def _obtener_fichas():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ID_FICHA, No_FICHA FROM ficha ORDER BY No_FICHA")
            return cur.fetchall()
    finally:
        conn.close()


def _obtener_aprendices():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.Nombre, u.Apellidos, u.No_Documento, f.No_FICHA
                FROM usuario u
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.Id_Usuario = u.Id_Usuario
                LEFT JOIN ficha f ON f.ID_FICHA = ufa.ID_FICHA
                WHERE u.ROL = 'Aprendiz'
            """)
            filas = cur.fetchall()
            return [
                {
                    "nombre": f"{r['Nombre']} {r['Apellidos']}".strip(),
                    "documento": r['No_Documento'],
                    "ficha": r['No_FICHA'] or '—'
                }
                for r in filas
            ]
    finally:
        conn.close()


@coordinador.route('/lista-coordinador')
@solo_rol('coordinador')
def lista_coordinador():
    return render_template('lista_coordinador.html', active_page='lista')


@coordinador.route('/reportes-coordinador')
@solo_rol('coordinador')
def reportes_coordinador():
    return render_template('reportes_coordinador.html', active_page='reportes')


@coordinador.route('/novedades-coordinador')
@solo_rol('coordinador')
def novedades_coordinador():
    return render_template('novedades_coordinador.html', active_page='novedades')


@coordinador.route('/historial-coordinador')
@solo_rol('coordinador')
def historia_coordinador():
    return render_template('historia_coordinador.html', active_page='historial')


@coordinador.route('/formulario-coordinador')
@solo_rol('coordinador')
def formulario_coordinador():
    return render_template(
        'aprendices.html',
        active_page='formulario',
        fichas=_obtener_fichas(),
        aprendices=_obtener_aprendices()
    )

@coordinador.route('/coordinador/aprendiz-manual', methods=['POST'])
@solo_rol('coordinador')
def aprendiz_manual():
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    tipo_doc = request.form.get('tipo_documento', '').strip()
    num_doc = request.form.get('numero_documento', '').strip()
    correo = request.form.get('correo', '').strip().lower()
    no_ficha = request.form.get('ficha', '').strip()

    if not (nombres and apellidos and tipo_doc and num_doc and no_ficha):
        flash('Completa todos los campos obligatorios.', 'error')
        return redirect(url_for('coordinador.formulario_coordinador'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Buscar la ficha real y su asignación usando el número de ficha (No_FICHA)
            cur.execute(
                """SELECT f.ID_FICHA, ufa.ID_ASIGNACION
                   FROM ficha f
                   JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                   WHERE f.No_FICHA = %s LIMIT 1""",
                (no_ficha,)
            )
            resultado = cur.fetchone()

            if not resultado:
                flash(f'La ficha {no_ficha} no existe o no tiene una asignación (instructor/horario) creada.', 'error')
                return redirect(url_for('coordinador.formulario_coordinador'))

            id_ficha = resultado['ID_FICHA']
            id_asignacion = resultado['ID_ASIGNACION']

            cur.execute(
                """INSERT INTO usuario
                   (Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, CORREO_SENA, ROL, Activo_SN)
                   VALUES (%s, %s, %s, %s, %s, 'Aprendiz', '1')""",
                (nombres, apellidos, num_doc, tipo_doc, correo)
            )
            nuevo_id = cur.lastrowid

            cur.execute(
                "INSERT INTO usuario_ficha_asignacion (Id_Usuario, ID_FICHA, ID_ASIGNACION) VALUES (%s, %s, %s)",
                (nuevo_id, id_ficha, id_asignacion)
            )
        conn.commit()
        flash('Aprendiz registrado correctamente.', 'success')
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {e}")
        flash('Error al registrar el aprendiz. Verifica que el documento no esté duplicado.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.formulario_coordinador'))

@coordinador.route('/coordinador/aprendices-masivo', methods=['POST'])
@solo_rol('coordinador')
def aprendices_masivo():
    archivo = request.files.get('archivo_csv')
    ficha_default = request.form.get('ficha_masivo', '').strip()

    if not archivo or archivo.filename == '':
        flash('Selecciona un archivo CSV.', 'error')
        return redirect(url_for('coordinador.formulario_coordinador'))

    stream = io.StringIO(archivo.stream.read().decode('utf-8-sig'))
    lector = csv.DictReader(stream)

    conn = get_db()
    insertados, errores = 0, 0
    detalle_errores = []
    try:
        with conn.cursor() as cur:
            for i, fila in enumerate(lector, start=2):  # fila 2 = primera fila de datos (después del encabezado)
                try:
                    no_ficha = (fila.get('ficha') or ficha_default or '').strip()
                    if not no_ficha:
                        errores += 1
                        detalle_errores.append(f"Fila {i}: sin ficha especificada.")
                        continue

                    # Buscar la ficha real y su asignación usando el número de ficha (No_FICHA)
                    cur.execute(
                        """SELECT f.ID_FICHA, ufa.ID_ASIGNACION
                           FROM ficha f
                           JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                           WHERE f.No_FICHA = %s LIMIT 1""",
                        (no_ficha,)
                    )
                    resultado = cur.fetchone()
                    if not resultado:
                        errores += 1
                        detalle_errores.append(f"Fila {i}: la ficha {no_ficha} no existe o no tiene asignación.")
                        continue

                    id_ficha = resultado['ID_FICHA']
                    id_asignacion = resultado['ID_ASIGNACION']

                    cur.execute(
                        """INSERT INTO usuario
                           (Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, CORREO_SENA, ROL, Activo_SN)
                           VALUES (%s, %s, %s, %s, %s, 'Aprendiz', '1')""",
                        (fila.get('nombres', '').strip(), fila.get('apellidos', '').strip(),
                         fila.get('numero_documento', '').strip(), fila.get('tipo_documento', '').strip(),
                         fila.get('correo', '').strip().lower())
                    )
                    nuevo_id = cur.lastrowid

                    cur.execute(
                        "INSERT INTO usuario_ficha_asignacion (Id_Usuario, ID_FICHA, ID_ASIGNACION) VALUES (%s, %s, %s)",
                        (nuevo_id, id_ficha, id_asignacion)
                    )
                    insertados += 1
                except Exception as e:
                    print(f"[DB ERROR fila {i}] {e}")
                    errores += 1
                    detalle_errores.append(f"Fila {i}: documento duplicado o dato inválido.")
        conn.commit()

        mensaje = f'{insertados} aprendices cargados correctamente. {errores} con error.'
        if detalle_errores:
            mensaje += ' Detalle: ' + ' | '.join(detalle_errores[:5])
        flash(mensaje, 'success' if insertados else 'error')
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {e}")
        flash('Error al procesar el archivo CSV.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.formulario_coordinador'))