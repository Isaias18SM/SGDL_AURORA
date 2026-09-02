from flask import Blueprint, render_template, session
from app.utils.decorators import solo_rol
from app.database import get_db

fichas_bp = Blueprint('fichas', __name__)


def _obtener_fichas_con_conteo(usuario_id):
    """Fichas asignadas al usuario logueado (instructor/coordinador), con su
    programa y el número de aprendices activos en cada una."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.ID_FICHA,
                       f.No_FICHA        AS codigo,
                       f.Jornada         AS jornada,
                       f.TipoDeFicha     AS tipo_ficha,
                       p.Nombre          AS programa,
                       COUNT(DISTINCT au.Id_Usuario) AS aprendices_activos
                FROM ficha f
                JOIN programa p ON p.Id_Programa = f.Id_Programa
                -- Solo fichas donde ESTE usuario tiene una asignación (como instructor)
                JOIN usuario_ficha_asignacion mia
                     ON mia.ID_FICHA = f.ID_FICHA
                    AND mia.Id_Usuario = %s
                -- Conteo de aprendices activos de esa ficha (independiente del filtro anterior)
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                LEFT JOIN usuario au ON au.Id_Usuario = ufa.Id_Usuario
                                     AND au.ROL = 'Aprendiz'
                                     AND au.Activo_SN = '1'
                GROUP BY f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha, p.Nombre
                ORDER BY f.No_FICHA
            """, (usuario_id,))
            return cur.fetchall()
    finally:
        conn.close()


@fichas_bp.route('/fichas')
@solo_rol('instructor', 'coordinador')
def fichas():
    usuario_id = session.get('id')
    return render_template(
        'fichas.html',
        active_page='fichas',
        fichas=_obtener_fichas_con_conteo(usuario_id)
    )