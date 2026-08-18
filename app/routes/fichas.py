from flask import Blueprint, render_template
from decorators import solo_rol
from database import get_db

fichas_bp = Blueprint('fichas', __name__)


def _obtener_fichas_con_conteo():
    """Fichas con su programa y el número de aprendices activos."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.ID_FICHA,
                       f.No_FICHA        AS codigo,
                       f.Jornada         AS jornada,
                       f.TipoDeFicha     AS tipo_ficha,
                       p.Nombre          AS programa,
                       COUNT(ufa.Id_Usuario) AS aprendices_activos
                FROM ficha f
                JOIN programa p ON p.Id_Programa = f.Id_Programa
                LEFT JOIN usuario_ficha_asignacion ufa ON ufa.ID_FICHA = f.ID_FICHA
                LEFT JOIN usuario u ON u.Id_Usuario = ufa.Id_Usuario AND u.ROL = 'Aprendiz' AND u.Activo_SN = '1'
                GROUP BY f.ID_FICHA, f.No_FICHA, f.Jornada, f.TipoDeFicha, p.Nombre
                ORDER BY f.No_FICHA
            """)
            return cur.fetchall()
    finally:
        conn.close()


@fichas_bp.route('/fichas')
@solo_rol('instructor', 'coordinador')
def fichas():
    return render_template('fichas.html', active_page='fichas', fichas=_obtener_fichas_con_conteo())