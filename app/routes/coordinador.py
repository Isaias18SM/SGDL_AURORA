import csv
import io
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.utils.decorators import solo_rol
from app.database import get_db, obtener_novedades_pendientes, marcar_novedad_resuelta

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

# Única función optimizada para obtener todas las fichas con su programa
def _obtener_fichas():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.No_FICHA, f.Jornada, f.TipoDeFicha, 
                       f.FechaInicio, f.FechaFinal, p.Nombre
                FROM ficha f
                LEFT JOIN programa p ON p.Id_Programa = f.Id_Programa
            """)
            filas = cur.fetchall()
            return [
                {
                    "numero_ficha": r['No_FICHA'],
                    "jornada": r['Jornada'],
                    "tipo_ficha": r['TipoDeFicha'],
                    "fecha_inicio": r['FechaInicio'],
                    "fecha_final": r['FechaFinal'],
                    "programa": r['Nombre'] or 'Sin programa'
                }
                for r in filas
            ]
    finally:
        conn.close()


def _obtener_programas():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Id_Programa AS id, Nombre AS nombre FROM programa")
            datos = cur.fetchall()
            return datos
    finally:
        conn.close()


# RUTA CORREGIDA: Ahora le enviamos tanto 'programas' como 'fichas' al HTML
@coordinador.route('/formulario-ficha')
@solo_rol('coordinador')
def formulario_ficha():
    datos_programas = _obtener_programas()
    lista_fichas = _obtener_fichas()  # <-- Obtenemos las fichas aquí
    return render_template(
        'Formulario_New_Ficha.html',
        active_page='formulario_ficha',
        programas=datos_programas,
        fichas=lista_fichas        # <-- Las inyectamos a la plantilla
    )
def _obtener_programas():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Id_Programa AS id, Nombre AS nombre FROM programa")
            return cur.fetchall()
    finally:
        conn.close()


@coordinador.route('/lista-coordinador')
@solo_rol('coordinador')
def lista_coordinador():
    return render_template('lista_coordinador.html', active_page='lista')


@coordinador.route('/reportes-coordinador')
@solo_rol('coordinador')
def reportes_coordinador():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 1. Instructores
            cur.execute("""
                SELECT Id_Usuario as id, CONCAT(Nombre, ' ', Apellidos) as nombre
                FROM usuario 
                WHERE ROL = 'Instructor'
            """)
            instructores = cur.fetchall()

            # 2. Fichas asignadas a cada instructor
            for ins in instructores:
                cur.execute("""
                    SELECT f.No_FICHA as codigo, p.Nombre as programa, f.Jornada as jornada
                    FROM ficha f
                    JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                    LEFT JOIN programa p ON p.Id_Programa = f.Id_Programa
                    WHERE ufa.Id_Usuario = %s
                """, (ins['id'],))
                ins['fichas'] = cur.fetchall()

            # 3. Fichas sin instructor asignado
            cur.execute("""
                SELECT f.No_FICHA as codigo, p.Nombre as programa
                FROM ficha f
                LEFT JOIN programa p ON p.Id_Programa = f.Id_Programa
                WHERE f.ID_FICHA NOT IN (
                    SELECT DISTINCT ufa.ID_FICHA 
                    FROM usuario_ficha_asignacion ufa
                    JOIN usuario u ON u.Id_Usuario = ufa.Id_Usuario
                    WHERE u.ROL = 'Instructor'
                )
            """)
            fichas_libres = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        'reportes_coordinador.html',
        active_page='reportes',
        instructores=instructores,
        fichas_libres=fichas_libres
    )


@coordinador.route('/coordinador/asignar-ficha', methods=['POST'])
@solo_rol('coordinador')
def coordinador_asignar_ficha():
    instructor_id = request.form.get('instructor_id')
    fichas_codigos = request.form.getlist('ficha_codigo')

    if not fichas_codigos:
        flash('Selecciona al menos una ficha para asignar.', 'error')
        return redirect(url_for('coordinador.reportes_coordinador'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT Id_Trimestre FROM trimestre ORDER BY Id_Trimestre DESC LIMIT 1")
            trimestre = cur.fetchone()
            if not trimestre:
                flash('No hay trimestres registrados en la base de datos.', 'error')
                return redirect(url_for('coordinador.reportes_coordinador'))
            id_trimestre = trimestre['Id_Trimestre']

            cur.execute(
                """INSERT INTO asignacion (Id_Usuario, Id_Trimestre, HORA_INICIO, HORA_FINALIZACION)
                   VALUES (%s, %s, '07:00:00', '13:00:00')""",
                (instructor_id, id_trimestre)
            )
            id_asignacion = cur.lastrowid

            asignadas, no_encontradas = 0, []

            for ficha_codigo in fichas_codigos:
                cur.execute("SELECT ID_FICHA FROM ficha WHERE No_FICHA = %s LIMIT 1", (ficha_codigo,))
                ficha = cur.fetchone()

                if not ficha:
                    no_encontradas.append(ficha_codigo)
                    continue

                cur.execute(
                    """SELECT 1 FROM usuario_ficha_asignacion
                       WHERE Id_Usuario = %s AND ID_FICHA = %s LIMIT 1""",
                    (instructor_id, ficha['ID_FICHA'])
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    """INSERT INTO usuario_ficha_asignacion (Id_Usuario, ID_FICHA, ID_ASIGNACION)
                       VALUES (%s, %s, %s)""",
                    (instructor_id, ficha['ID_FICHA'], id_asignacion)
                )
                asignadas += 1

            conn.commit()

            if asignadas:
                flash(f'{asignadas} ficha(s) asignada(s) al instructor correctamente.', 'success')
            if no_encontradas:
                flash(f'No se encontraron estas fichas: {", ".join(no_encontradas)}.', 'error')
    except Exception as e:
        conn.rollback()
        print(f"[ERROR ASIGNACION]: {e}")
        flash('Error al asignar la ficha.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.reportes_coordinador'))


@coordinador.route('/coordinador/desasignar-ficha', methods=['POST'])
@solo_rol('coordinador')
def coordinador_desasignar_ficha():
    ficha_codigo = request.form.get('ficha_codigo')

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ID_FICHA FROM ficha WHERE No_FICHA = %s LIMIT 1", (ficha_codigo,))
            ficha = cur.fetchone()
            if ficha:
                cur.execute("DELETE FROM usuario_ficha_asignacion WHERE ID_FICHA = %s", (ficha['ID_FICHA'],))
                conn.commit()
                flash('Asignación removida.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error al desasignar la ficha.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.reportes_coordinador'))


@coordinador.route('/novedades-coordinador')
@solo_rol('coordinador')
def novedades_coordinador():
    novedades = obtener_novedades_pendientes()
    return render_template(
        'novedades_coordinador.html',
        active_page='novedades',
        novedades=novedades
    )


@coordinador.route('/api/novedades/<int:id_novedad>/accion', methods=['POST'])
@solo_rol('coordinador')
def resolver_novedad(id_novedad):
    """Llamado por fetch() desde novedades_coordinador.html para marcar una novedad como resuelta."""
    resultado = marcar_novedad_resuelta(id_novedad, session.get('id'))
    return jsonify({
        'status': 'success' if resultado['ok'] else 'error',
        'message': resultado['message']
    })


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



@coordinador.route('/coordinador/registrar-usuario', methods=['POST'])
@solo_rol('coordinador')
def registrar_usuario():
    nombres = request.form.get('nombres', '').strip().title()
    apellidos = request.form.get('apellidos', '').strip().title()
    rol = request.form.get('rol', '').strip()
    tipo_doc = request.form.get('tipo_documento', '').strip()
    num_doc = request.form.get('numero_documento', '').strip()
    correo = request.form.get('correo', '').strip().lower()
    no_ficha = request.form.get('ficha', '').strip()

    if rol not in ('Aprendiz', 'Instructor'):
        flash('Selecciona un rol válido.', 'error')
        return redirect(url_for('coordinador.formulario_coordinador'))

    campos_base_ok = nombres and apellidos and tipo_doc and num_doc
    if rol == 'Aprendiz' and not (campos_base_ok and no_ficha):
        flash('Completa todos los campos obligatorios.', 'error')
        return redirect(url_for('coordinador.formulario_coordinador'))
    if rol == 'Instructor' and not campos_base_ok:
        flash('Completa todos los campos obligatorios.', 'error')
        return redirect(url_for('coordinador.formulario_coordinador'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            id_ficha = None
            id_asignacion = None

            if rol == 'Aprendiz':
                cur.execute(
                    """SELECT f.ID_FICHA, ufa.ID_ASIGNACION
                    FROM ficha f
                    JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                    WHERE f.No_FICHA = %s LIMIT 1""",
                    (no_ficha,)
                )
                resultado = cur.fetchone()

                if not resultado:
                    flash(f'La ficha {no_ficha} no existe o no tiene una asignación creada.', 'error')
                    return redirect(url_for('coordinador.formulario_coordinador'))

                id_ficha = resultado['ID_FICHA']
                id_asignacion = resultado['ID_ASIGNACION']

            clave_encriptada = str(num_doc)

            cur.execute(
                """INSERT INTO usuario
                (Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, CORREO_SENA, CONTRASENA, ROL, Activo_SN)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (nombres, apellidos, num_doc, tipo_doc, correo, clave_encriptada, rol, '1')
            )
            nuevo_id = cur.lastrowid

            if rol == 'Aprendiz':
                cur.execute(
                    "INSERT INTO usuario_ficha_asignacion (Id_Usuario, ID_FICHA, ID_ASIGNACION) VALUES (%s, %s, %s)",
                    (nuevo_id, id_ficha, id_asignacion)
                )

        conn.commit()
        flash(f'{rol} registrado correctamente.', 'success')
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {e}")
        flash('Error al registrar. Verifica que el documento no esté duplicado.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.formulario_coordinador'))


@coordinador.route('/coordinador/ficha-manual', methods=['POST'])
@solo_rol('coordinador')
def ficha_manual():
    NumeroFicha = request.form.get('NumeroFicha', '').strip()
    Jornada = request.form.get('Jornada', '').strip()
    TipoFicha = request.form.get('TipoFicha', '').strip()
    Vigencia = request.form.get('Vigencia', '').strip()
    FechaInicio = request.form.get('FechaInicio', '').strip()
    FechaFinal = request.form.get('FechaFinal', '').strip()
    Programa = request.form.get('Programa')

    if not (NumeroFicha and Jornada and TipoFicha and Vigencia and FechaInicio and FechaFinal and Programa):
        flash('Completa todos los campos obligatorios.', 'error')
        return redirect(url_for('coordinador.formulario_ficha'))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ficha
                (No_FICHA, Jornada, TipoDeFicha, Vigencia, FechaInicio, FechaFinal, Id_Programa)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (NumeroFicha, Jornada, TipoFicha, Vigencia, FechaInicio, FechaFinal, Programa)
            )

        conn.commit()
        flash(f'Ficha {NumeroFicha} registrada correctamente.', 'success')

    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] {e}")
        flash('Error al registrar la ficha.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.formulario_ficha'))


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
            for i, fila in enumerate(lector, start=2):
                try:
                    no_ficha = (fila.get('ficha') or ficha_default or '').strip()
                    if not no_ficha:
                        errores += 1
                        detalle_errores.append(f"Fila {i}: sin ficha especificada.")
                        continue

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

                    numero_documento = fila.get('numero_documento', '').strip()
                    contrasena_inicial = numero_documento
                    token_qr = uuid.uuid4().hex

                    cur.execute(
                        """INSERT INTO usuario
                           (Nombre, Apellidos, No_Documento, TPI_DOCUMENTO, CORREO_SENA,
                            CONTRASENA, ROL, Activo_SN, Token_QR)
                           VALUES (%s, %s, %s, %s, %s, %s, 'Aprendiz', '1', %s)""",
                        (fila.get('nombres', '').strip(), fila.get('apellidos', '').strip(),
                         numero_documento, fila.get('tipo_documento', '').strip(),
                         fila.get('correo', '').strip().lower(),
                         contrasena_inicial, token_qr)
                    )
                    nuevo_id = cur.lastrowid

                    cur.execute(
                        "INSERT INTO usuario_ficha_asignacion (Id_Usuario, ID_FICHA, ID_ASIGNACION) VALUES (%s, %s, %s)",
                        (nuevo_id, id_ficha, id_asignacion)
                    )
                    insertados += 1
                except Exception as e:
                    errores += 1
                    detalle_errores.append(f"Fila {i}: documento duplicado o dato inválido.")
        conn.commit()

        mensaje = f'{insertados} aprendices cargados correctamente. {errores} con error.'
        if detalle_errores:
            mensaje += ' Detalle: ' + ' | '.join(detalle_errores[:5])
        flash(mensaje, 'success' if insertados else 'error')
    except Exception as e:
        conn.rollback()
        flash('Error al procesar el archivo CSV.', 'error')
    finally:
        conn.close()

    return redirect(url_for('coordinador.formulario_coordinador'))