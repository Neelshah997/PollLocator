from flask import Blueprint,render_template,request,Response,jsonify
import json,traceback
from database.models import *
from flask_jwt_extended import JWTManager, create_access_token



poleSurvey = Blueprint('poleSurvey',__name__)

@poleSurvey.route('/healthcheck',methods=['GET'])
def healthcheck():
    return "pole Survey is running smoothly"
from app import bcrypt
@poleSurvey.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        phone = data.get('phone')
        role_name = data.get('role', 'user')

        if User.objects(phone=phone).first():
            return jsonify({"error": "Phone already exists"}), 400

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        role = Role.objects(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name} role").save()

        user = User(
            name=name,
            email=email,
            password=hashed_pw,
            phone=phone,
            role=role
        ).save()

        return jsonify({"message": "User registered successfully", "user": user.to_json()}), 201

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@poleSurvey.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        phone = data.get('number')
        password = data.get('password')

        user = User.objects(phone=phone).first()
        if not user or not bcrypt.check_password_hash(user.password, password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(identity=str(user.id))
        return jsonify({"token": access_token, "user": user.to_json()}), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@poleSurvey.route('/recommendations', methods=['GET'])
def get_recommendations():
    try:
        recommendations = {}

        divisions = Division.objects()
        recommendations['divisions'] = [div.to_json() for div in divisions]

        division_id = request.args.get('division_id')
        if division_id:
            division = Division.objects(id=division_id).first()
            if division:
                subdivisions = Subdivision.objects(division=division)
                recommendations['subdivisions'] = [subdiv.to_json() for subdiv in subdivisions]

        subdivision_id = request.args.get('subdivision_id')
        if subdivision_id:
            subdivision = Subdivision.objects(id=subdivision_id).first()
            if subdivision:
                feeders = Feeder.objects(subdivision=subdivision)
                recommendations['feeders'] = [feeder.to_json() for feeder in feeders]
        feeder_id = request.args.get('feeder_id')
        if feeder_id:
            feeder = Feeder.objects(id=feeder_id).first()
            if not feeder:
                return jsonify({"error": "Feeder not found"}), 404

            tcs = Transformer.objects(feeder=feeder)
            recommendations['tc_number'] = [tc.to_json() for tc in tcs]

        return recommendations, 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@poleSurvey.route('/division', methods=['POST'])
def create_division():
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({"error": "Name is required"}), 400

        division = Division(name=name)
        division.save()

        return jsonify({"message": "Division created", "division_id": str(division.id)}), 201

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@poleSurvey.route('/subdivisions', methods=['POST'])
def create_subdivisions():
    try:
        data = request.get_json()
        names = data.get('names')  # expecting a list
        division_id = data.get('division_id')

        if not names or not isinstance(names, list) or not division_id:
            return jsonify({"error": "List of names and division_id are required"}), 400

        division = Division.objects(id=division_id).first()
        if not division:
            return jsonify({"error": "Division not found"}), 404

        created_subdivisions = []
        for name in names:
            if name:
                subdivision = Subdivision(name=name, division=division)
                subdivision.save()
                created_subdivisions.append(subdivision.to_json())

        return jsonify({
            "message": "Subdivisions created",
            "subdivisions": created_subdivisions
        }), 201

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@poleSurvey.route('/transformer', methods=['POST','GET'])
def handle_transformer():

    if request.method == 'POST':
        try:
            data = request.get_json()
            tc_number = data.get('tc_number')
            feeder_id = data.get('feeder_id')
            tc_name = data.get('tc_name')
            lat = data.get('lat')
            long = data.get('long')

            if not tc_number or not feeder_id:
                return jsonify({"error": "tc_number and feeder_id are required"}), 400

            feeder = Feeder.objects(id=feeder_id).first()
            if not feeder:
                return jsonify({"error": "Feeder not found"}), 404

            # Check for duplicate
            if Transformer.objects(tc_number=tc_number, feeder=feeder).first():
                return jsonify({"error": "TC with this number already exists"}), 400

            transformer = Transformer(tc_number=tc_number,name=tc_name, feeder=feeder, lat=lat, long=long)
            transformer.save()

            return jsonify({"message": "Transformer created", "tc_id": str(transformer.id)}), 201
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
    if request.method == 'GET':
        try:
            tc_id = request.args.get('tc_id')

            if tc_id:
                tc = Transformer.objects(id=tc_id).first()
                if not tc:
                    return jsonify({"error": "Transformer not found"}), 404

                return jsonify({
                    "tc": {
                        "id": str(tc.id),
                        "name": tc.name,
                        "tc_number": tc.tc_number,
                        "lat": tc.lat,
                        "long": tc.long,
                        "capacity": tc.capacity
                    }
                }), 200

            # Fetch all TCs
            tcs = Transformer.objects()
            tcs_data = [{
                "id": str(tc.id),
                "name": tc.name,
                "tc_number": tc.tc_number,
                "lat": tc.lat,
                "long": tc.long,
                "capacity": tc.capacity
            } for tc in tcs]

            return jsonify({"tcs": tcs_data}), 200

        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
@poleSurvey.route('/feeder', methods=['POST'])
def create_feeders():
    try:
        data = request.get_json()
        names = data.get('names')  # List of names
        subdivision_id = data.get('subdivision_id')

        if not names or not subdivision_id or not isinstance(names, list):
            return jsonify({"error": "List of names and subdivision_id are required"}), 400

        subdivision = Subdivision.objects(id=subdivision_id).first()
        if not subdivision:
            return jsonify({"error": "Subdivision not found"}), 404

        created_feeders = []
        skipped_feeders = []

        for name in names:
            existing = Feeder.objects(name=name, subdivision=subdivision).first()
            if existing:
                skipped_feeders.append(name)
            else:
                feeder = Feeder(name=name, subdivision=subdivision)
                feeder.save()
                created_feeders.append(feeder.to_json())

        return jsonify({
            "message": f"{len(created_feeders)} feeder(s) created, {len(skipped_feeders)} skipped due to duplication",
            "created": created_feeders,
            "skipped": skipped_feeders
        }), 201

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371 * 1000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # in meters

@poleSurvey.route('/pole', methods=['POST','GET'])
def create_pole():
    if request.method == 'POST':
        try:
            data = request.get_json()

            tc_id = data.get("tc_id")
            pole_number = data.get("pole_number")
            is_existing = data.get("is_existing")
            previous_connector_type = data.get("previous_connector_type")  # "tc" or "pole"
            previous_connector_id = data.get("previous_connector_id")
            lat = data.get("lat")
            long = data.get("long")

            if not tc_id or not pole_number or lat is None or long is None:
                return jsonify({"error": "TC ID, pole Number, lat and long are required"}), 400

            # Lookup the Transformer
            tc = Transformer.objects(id=tc_id).first()
            if not tc:
                return jsonify({"error": "Transformer (TC) not found"}), 404

            # Calculate span_length
            span_length = None
            if previous_connector_type and previous_connector_id:
                if previous_connector_type == "tc":
                    connector = Transformer.objects(id=previous_connector_id).first()
                elif previous_connector_type == "pole":
                    connector = Pole.objects(id=previous_connector_id).first()
                else:
                    return jsonify({"error": "Invalid previous_connector_type"}), 400
                
                if connector and connector.lat is not None and connector.long is not None:
                    span_length = haversine(connector.lat, connector.long, lat, long)

            pole = Pole(
                tc=tc,
                pole_number=pole_number,
                is_existing=is_existing,
                previous_connector=f"{previous_connector_type}-{previous_connector_id}",
                lat=lat,
                long=long,
                span_length=span_length
            )
            pole.save()

            return jsonify({
                "message": "pole created successfully",
                "pole_id": str(pole.id),
                "span_length": span_length
            }), 201

        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
    if request.method == 'GET':
        try:
            poleId = request.args['poleId']
            pole = Pole.objects(id = poleId).first()
            return jsonify(pole.to_json()),200
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
    
    
@poleSurvey.route('/poles', methods=['GET'])
def get_pole_numbers_by_tc():
    try:
        tc_id = request.args.get('tc_id')
        if not tc_id:
            return jsonify({"error": "tc_id is required"}), 400

        tc = Transformer.objects(id=tc_id).first()
        if not tc:
            return jsonify({"error": "Transformer not found"}), 404

        poles = Pole.objects(tc=tc)
        pole_numbers = [{
                "id": str(pole.id),
                "pole_number": pole.pole_number,
            } for pole in poles]

        return jsonify({"pole_numbers": pole_numbers}), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@poleSurvey.route('/questions', methods=['GET'])
def getQuestions():
    try:
        existingQuestions = ["Type of Arrangement","Span Three Phase", "Span Single Phase","Type of Conductor (Weasel/Rabbit/Dog)","Type of PSC/RSJ","Condition of Pole (Good, Damage/Rusted/Bend etc.)","Danger Board","Barbed Wire","LT Cross Arm","C Type L T cross arm","L T Porcelain Pin Insulators","Connection Box","Stay set (GUY SET)","Coil Earthing","Guarding","REQUIREMENTS OF TREE CUTTING (YES/NO)"]
        proposedQuestion = ["8mtr PSC","Danger Board","Barbed wire","Stay set (GUY SET)","Coil Earthing","Guarding","Self‐Tightening Anchoring","Self‐locking suspension clamp with pole bracket &buckle","Mid‐span Tension Joints","Stainless steel of size strap 20mm*0.7mm& Buckle width 20 mm","Insulation piercing connector (I P C)","EYE HOOKS","AB XLPE CABLE 1.1 KV 3C X 50 SQ.MM+1Cx25 SQ. MM.+1x35 SQ.MM.","AB XLPE CABLE 1.1 KV 1Cx 35 SQMM + 1CX16 SQ MM + 25 SQ MM","insulation piercing connector connection box (I P C)","connection box plat","Supply of 1‐ph Pole mounted service connection box for LT connections (8 connections)","Supply of 3‐ph Pole mounted service connection box for LT connections (4 connections)","Supply of 4Cx10 mm2 LT PVC Cable","Supply of 4Cx16 mm2 LT PVC Cable"]

        return jsonify([{"existingQuestions": existingQuestions},{"proposedQuestion":proposedQuestion}]), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@poleSurvey.route('/material-info/<poleId>', methods=['POST'])
def fillMaterial(poleId):
    try:
        pole = Pole.objects(id = poleId).first()
        if request.args["poleType"] == "existing":
            pole.existing_info = request.json
        elif request.args["poleType"] == "new_proposed":
            pole.proposed_materials = request.json
        pole.save()
        return jsonify(pole.to_json()), 200
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
            