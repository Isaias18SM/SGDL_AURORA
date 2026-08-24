"""
app/models/__init__.py

Punto central de importación de todos los modelos.
Esto permite seguir haciendo:

    from app.models import Usuario, Ficha, Asignacion, ...

y garantiza que SQLAlchemy conozca TODAS las tablas antes de que
llames db.create_all() o generes una migración con Alembic/Flask-Migrate.
"""

# --- Entidades base / catálogos ---
from app.models.sede import Sede
from app.models.programa import Programa
from app.models.competencia import Competencia
from app.models.programa_competencia import programa_competencia

# --- Usuario / Ficha / Trimestre ---
from app.models.usuario import Usuario
from app.models.ficha import Ficha
from app.models.trimestre import Trimestre

# --- Asignacion (horarios) y su relación ternaria ---
from app.models.asignacion import Asignacion
from app.models.usuario_ficha_asignacion import UsuarioFichaAsignacion

# --- Resultados de aprendizaje ---
from app.models.resultado_de_aprendizaje import ResultadoDeAprendizaje
from app.models.asignacion_resultado_aprendizaje import asignacion_resultado_aprendizaje

# --- Observaciones ---
from app.models.observaciones import Observaciones
from app.models.usuario_observacion import usuario_observacion
from app.models.asignacion_observacion import asignacion_observacion

# --- Asistencia / Justificacion ---
from app.models.asistencia import Asistencia
from app.models.justificacion import Justificacion
from app.models.asistencia_justificacion_usuario import AsistenciaJustificacionUsuario

__all__ = [
    'Sede', 'Programa', 'Competencia', 'programa_competencia',
    'Usuario', 'Ficha', 'Trimestre',
    'Asignacion', 'UsuarioFichaAsignacion',
    'ResultadoDeAprendizaje', 'asignacion_resultado_aprendizaje',
    'Observaciones', 'usuario_observacion', 'asignacion_observacion',
    'Asistencia', 'Justificacion', 'AsistenciaJustificacionUsuario',
]
