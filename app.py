from flask import Flask
from app.routes.auth import auth_bp
from app.routes.instructores import instructor_bp
from app.routes.aprendices import aprendiz_bp
from app.routes.api import api_bp
from app.routes.coordinador import coordinador
from app.routes.fichas import fichas_bp

app = Flask(__name__, static_folder='app/static')
app.secret_key = 'aurora_sena_secret_2026'

# Registro de Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(instructor_bp)
app.register_blueprint(aprendiz_bp)
app.register_blueprint(coordinador)
app.register_blueprint(fichas_bp)
app.register_blueprint(api_bp)  # <- faltaba esta línea, por eso /api/fichas y /api/buscar-aprendiz daban 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)