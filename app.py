from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.power_grid_survey

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET')
JWT_EXPIRATION = timedelta(days=1)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
        except:
            return jsonify({'message': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'phone': data['phone']})
    
    if user and user['password'] == data['password']:  # In production, use proper password hashing
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + JWT_EXPIRATION
        }, JWT_SECRET)
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if db.users.find_one({'phone': data['phone']}):
        return jsonify({'message': 'Phone number already registered'}), 400
    
    user_id = db.users.insert_one({
        'phone': data['phone'],
        'password': data['password'],  # In production, hash the password
        'created_at': datetime.utcnow()
    }).inserted_id
    
    token = jwt.encode({
        'user_id': str(user_id),
        'exp': datetime.utcnow() + JWT_EXPIRATION
    }, JWT_SECRET)
    
    return jsonify({'token': token})

@app.route('/api/recommendations/division', methods=['GET'])
@token_required
def get_divisions(current_user):
    divisions = list(db.recommendations.distinct('division'))
    return jsonify(divisions)

@app.route('/api/recommendations/subdivision', methods=['GET'])
@token_required
def get_subdivisions(current_user):
    division = request.args.get('division')
    subdivisions = list(db.recommendations.find(
        {'division': division},
        {'subdivision': 1}
    ).distinct('subdivision'))
    return jsonify(subdivisions)

@app.route('/api/recommendations/feeder', methods=['GET'])
@token_required
def get_feeders(current_user):
    division = request.args.get('division')
    subdivision = request.args.get('subdivision')
    feeders = list(db.recommendations.find(
        {'division': division, 'subdivision': subdivision},
        {'feeder': 1}
    ).distinct('feeder'))
    return jsonify(feeders)

@app.route('/api/submit-poll', methods=['POST'])
@token_required
def submit_poll(current_user):
    data = request.get_json()
    
    # Get previous poll for span length calculation
    previous_poll = db.polls.find_one(
        {'user_id': current_user['_id']},
        sort=[('created_at', -1)]
    )
    
    poll_data = {
        'tc_number': data['tc_number'],
        'poll_number': data['poll_number'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'user_id': current_user['_id'],
        'created_at': datetime.utcnow()
    }
    
    if previous_poll:
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth's radius in meters
        lat1, lon1 = radians(previous_poll['latitude']), radians(previous_poll['longitude'])
        lat2, lon2 = radians(data['latitude']), radians(data['longitude'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        span_length = R * c
        
        poll_data['span_length'] = round(span_length)
    
    db.polls.insert_one(poll_data)
    return jsonify({'message': 'Poll submitted successfully'})

if __name__ == '__main__':
    app.run(debug=True)