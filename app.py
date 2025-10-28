import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool  # evita problemas de locking con SQLite+pools


app = Flask(__name__, template_folder="templates", static_folder="static")

# --- RUTA ABSOLUTA A LA DB EN instance/ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(DB_DIR, exist_ok=True)  # crea la carpeta si no existe
DB_PATH = os.path.join(DB_DIR, "database.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Para SQLite + threads
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"check_same_thread": False},
    "poolclass": NullPool,
}

# Asegura que exista la carpeta instance/ para la DB
os.makedirs("instance", exist_ok=True)

db = SQLAlchemy(app)

# Fuerza threading para Socket.IO (evita eventlet/gevent en Render con Py 3.13)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# -----------------------------------------------------------------------------
# Modelo
# -----------------------------------------------------------------------------
class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    mesa = db.Column(db.String(50), nullable=False)
    detalles = db.Column(db.String(500), nullable=False)
    total = db.Column(db.Float, nullable=False)
    # 0=pendiente, 1=entregado, 2=rechazado
    estado = db.Column(db.Integer, default=0, nullable=False)

# Crear tablas al arrancar
with app.app_context():
    db.create_all()

# -----------------------------------------------------------------------------
# Rutas
# -----------------------------------------------------------------------------
@app.route("/")
def menu():
    return render_template("menu.html")

@app.route("/cocina")
def cocina():
    return render_template("cocina.html")

@app.route("/crear_pedido", methods=["POST"])
def crear_pedido():
    # Acepta JSON del cliente
    data = request.get_json(silent=True) or {}
    try:
        mesa = data["mesa"]
        detalles = data["detalles"]
        total = float(data["total"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "msg": "Payload inválido"}), 400

    nuevo = Pedido(mesa=mesa, detalles=detalles, total=total)
    db.session.add(nuevo)
    db.session.commit()

    pedido_data = {
        "id": nuevo.id,
        "nombre": nuevo.mesa,
        "detalles": nuevo.detalles,
        "total": nuevo.total,
    }

    # Notifica en tiempo real a la cocina
    socketio.emit("nuevo_pedido", pedido_data)
    return jsonify({"status": "ok", "pedido": pedido_data})

@app.route("/actualizar_estado", methods=["POST"])
def actualizar_estado():
    data = request.get_json(silent=True) or {}
    try:
        pedido_id = int(data["id"])
        estado = int(data["estado"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "msg": "Payload inválido"}), 400

    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return jsonify({"status": "error", "msg": "Pedido no encontrado"}), 404

    pedido.estado = estado
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/api/pedidos_pendientes")
def pedidos_pendientes():
    pedidos = Pedido.query.filter_by(estado=0).all()
    data = [
        {"id": p.id, "nombre": p.mesa, "detalles": p.detalles, "total": p.total}
        for p in pedidos
    ]
    return jsonify(data)

# -----------------------------------------------------------------------------
# Arranque local
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # En local, usa 127.0.0.1. En Render, Gunicorn usará 0.0.0.0:$PORT desde el Procfile.
    print("✅ Servidor ejecutándose en http://127.0.0.1:5000")
    socketio.run(
        app,
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False,  # evita doble proceso y conflictos de puerto en Windows
    )
