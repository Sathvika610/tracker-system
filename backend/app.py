from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_crontab import Crontab


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*') 
crontab = Crontab(app)



# Database model for Client Instances
class ClientInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False)
    restaurant_status = db.Column(db.Integer, nullable=False)
    last_active = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<ClientInstance id={self.id}, restaurant_id={self.restaurant_id}, restaurant_status={self.restaurant_status}, last_active={self.last_active}>'

# API endpoint to receive status updates from client instances
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    restaurant_id = data.get('restaurant_id')
    restaurant_status = data.get('restaurant_status')

    if restaurant_id is None or restaurant_status is None:
        return jsonify({'status': 'failed', 'message': 'Invalid data. Both restaurant_id and restaurant_status are required.'}), 400

    if restaurant_status not in [0, 1]:
        return jsonify({'status': 'failed', 'message': 'Invalid restaurant_status. Use 0 for down and 1 for active.'}), 400

    # Update or create the client instance in the database
    client_instance = ClientInstance.query.filter_by(restaurant_id=restaurant_id).first()
    if not client_instance:
        client_instance = ClientInstance(restaurant_id=restaurant_id, restaurant_status=restaurant_status, last_active=db.func.current_timestamp())
        db.session.add(client_instance)
    else:
        client_instance.restaurant_status = restaurant_status
        client_instance.last_active = db.func.current_timestamp()

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Status updated successfully.'}), 200

# API endpoint to fetch all client instances' status
@app.route('/get_status', methods=['GET'])
def get_status():
    all_instances = ClientInstance.query.all()
    status_list = [{'restaurant_id': instance.restaurant_id, 'restaurant_status': instance.restaurant_status} for instance in all_instances]
    return jsonify(status_list), 200

# Background task to check for inactive client instances every 1 minute
@crontab.job(minute="*")
def check_inactive_instances():
    all_instances = ClientInstance.query.all()
    current_time = db.func.current_timestamp()

    # List to store down instances for notification
    down_instances = []

    for instance in all_instances:
        time_difference = current_time - instance.last_active
        if time_difference.seconds > 600 and instance.restaurant_status == 1:
            instance.restaurant_status = 0
            down_instances.append(instance)

    db.session.commit()

    # Emit a real-time update to all connected clients
    if down_instances:
        emit('status_update', {'status': 'down', 'instances': [inst.restaurant_id for inst in down_instances]}, broadcast=True)


# SocketIO event when a client instance connects
@socketio.on('connect')
def handle_connect():
    all_instances = ClientInstance.query.all()
    status_list = [{'restaurant_id': instance.restaurant_id, 'restaurant_status': instance.restaurant_status} for instance in all_instances]
    emit('initial_status', {'status': 'success', 'data': status_list})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='127.0.0.1', port=3002, debug=True,use_reloader=False)