"""
app/models/sede.py
"""
from app import db


class Sede(db.Model):
    __tablename__ = 'sede'

    Id_Sede = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Nombre = db.Column(db.String(150), nullable=False)
    Direccion = db.Column(db.String(250))
    Ciudad = db.Column(db.String(100))
    Estado = db.Column(db.String(30))

    trimestres = db.relationship('Trimestre', back_populates='sede')

    def __repr__(self):
        return f'<Sede {self.Nombre}>'
