from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# === MODELO ===
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mesa = db.Column(db.String(50))
    detalles = db.Column(db.String(500))
    total = db.Column(db.Float)
    estado = db.Column(db.Integer, default=0)  # 0=pendiente, 1=entregado, 2=rechazado

with app.app_context():
    db.create_all()

# === RUTAS ===
@app.route('/')
def menu():
    return render_template('menu.html')

@app.route('/cocina')
def cocina():
    return render_template('cocina.html')

@app.route('/crear_pedido', methods=['POST'])
def crear_pedido():
    data = request.json
    nuevo = Pedido(
        mesa=data['mesa'],
        detalles=data['detalles'],
        total=data['total']
    )
    db.session.add(nuevo)
    db.session.commit()

    pedido_data = {
        'id': nuevo.id,
        'nombre': nuevo.mesa,
        'detalles': nuevo.detalles,
        'total': nuevo.total
    }

    socketio.emit('nuevo_pedido', pedido_data)
    return jsonify({'status': 'ok', 'pedido': pedido_data})

@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    data = request.json
    pedido = Pedido.query.get(data['id'])
    if not pedido:
        return jsonify({'status': 'error', 'msg': 'Pedido no encontrado'})

    pedido.estado = data['estado']
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/pedidos_pendientes')
def pedidos_pendientes():
    pedidos = Pedido.query.filter_by(estado=0).all()
    data = [
        {'id': p.id, 'nombre': p.mesa, 'detalles': p.detalles, 'total': p.total}
        for p in pedidos
    ]
    return jsonify(data)

if __name__ == '__main__':
    print("✅ Servidor ejecutándose en http://127.0.0.1:5000")
    socketio.run(app, debug=True)
