"""
app/models/usuario.py
"""
from app import db
from app.models.usuario_observacion import usuario_observacion


class Usuario(db.Model):
    __tablename__ = 'usuario'

    Id_Usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(80), nullable=False)
    Apellidos = db.Column(db.String(120), nullable=False)
    No_Documento = db.Column(db.String(30), unique=True, nullable=False)
    TPI_DOCUMENTO = db.Column(db.String(20))
    CORREO_SENA = db.Column(db.String(150), unique=True)
    CONTRASENA = db.Column(db.String(255), nullable=False)
    ROL = db.Column(db.String(30))
    Activo_SN = db.Column(db.String(1), default='S')

    asistencias = db.relationship('Asistencia', back_populates='usuario')
    asignaciones = db.relationship('Asignacion', back_populates='usuario')
    observaciones = db.relationship(
        'Observaciones', secondary=usuario_observacion, back_populates='usuarios'
    )

    def __repr__(self):
        return f'<Usuario {self.Nombre} {self.Apellidos}>'
