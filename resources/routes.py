from flask import Blueprint,render_template,request,Response,jsonify, send_file
import json,traceback
from database.models import *
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
# import pandas as pd
from io import BytesIO
from impl.excel_generator import generate_feeder_pole_excel

poleSurvey = Blueprint('poleSurvey',__name__)

import base64

def extract_image_bytes(req):
    """
    Extract image binary bytes from request.files (file upload) or request body (Base64 string).
    """
    for file_key in ['image', 'photo', 'file']:
        if file_key in req.files:
            file_obj = req.files[file_key]
            if file_obj and file_obj.filename:
                return file_obj.read()

    data = req.get_json(silent=True) or req.form
    if data:
        img_val = data.get('image') or data.get('photo') or data.get('image_base64')
        if img_val and isinstance(img_val, str):
            if ',' in img_val:
                img_val = img_val.split(',', 1)[1]
            try:
                return base64.b64decode(img_val)
            except Exception:
                return img_val.encode('utf-8')
    return None

def is_valid_object_id(val):
    if not val:
        return False
    val_str = str(val).strip()
    return len(val_str) == 24 and all(c in '0123456789abcdefABCDEF' for c in val_str)

def find_user(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            u = User.objects(id=ident_str).first()
            if u: return u
        except Exception:
            pass
    return User.objects(phone=ident_str).first()

def find_division(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            d = Division.objects(id=ident_str).first()
            if d: return d
        except Exception:
            pass
    return Division.objects(name=ident_str).first()

def find_subdivision(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            s = Subdivision.objects(id=ident_str).first()
            if s: return s
        except Exception:
            pass
    return Subdivision.objects(name=ident_str).first()

def find_feeder(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            f = Feeder.objects(id=ident_str).first()
            if f: return f
        except Exception:
            pass
    return Feeder.objects(name=ident_str).first()

def find_transformer(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            t = Transformer.objects(id=ident_str).first()
            if t: return t
        except Exception:
            pass
    t = Transformer.objects(tc_number=ident_str).first()
    if t: return t
    return Transformer.objects(name=ident_str).first()

def find_pole(identifier):
    if not identifier:
        return None
    ident_str = str(identifier).strip()
    if is_valid_object_id(ident_str):
        try:
            p = Pole.objects(id=ident_str).first()
            if p: return p
        except Exception:
            pass
    return Pole.objects(pole_number=ident_str).first()

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
        data = request.get_json(silent=True) or request.form or {}
        phone = data.get('number') or data.get('phone')
        password = data.get('password')

        if not phone or not password:
            return jsonify({"error": "Number/phone and password are required"}), 400

        user = User.objects(phone=phone).first()
        if not user or not bcrypt.check_password_hash(user.password, password):
            return jsonify({"error": "Invalid credentials"}), 401

        token_version = getattr(user, 'token_version', 1) or 1

        # Long-lived persistent token (1 year)
        expires_delta = timedelta(days=365)
        expires_at = (datetime.utcnow() + expires_delta).isoformat() + "Z"

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"token_version": token_version},
            expires_delta=expires_delta
        )
        return jsonify({
            "token": access_token,
            "user": user.to_json(),
            "expires_at": expires_at
        }), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@poleSurvey.route('/admin/revoke-user', methods=['POST'])
def revoke_user_session():
    try:
        data = request.get_json(silent=True) or request.form or {}
        user_id = data.get('user_id') or data.get('id')
        phone = data.get('phone') or data.get('number')

        user = find_user(user_id) or find_user(phone)

        if not user:
            return jsonify({"error": "User not found"}), 404

        current_version = getattr(user, 'token_version', 1) or 1
        user.token_version = current_version + 1
        user.save()

        return jsonify({
            "success": True,
            "message": "User session revoked successfully."
        }), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@poleSurvey.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    try:
        current_user_id = get_jwt_identity()
        return jsonify({
            "valid": True,
            "user_id": str(current_user_id)
        }), 200
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
            division = find_division(division_id)
            if division:
                subdivisions = Subdivision.objects(division=division)
                recommendations['subdivisions'] = [subdiv.to_json() for subdiv in subdivisions]

        subdivision_id = request.args.get('subdivision_id')
        if subdivision_id:
            subdivision = find_subdivision(subdivision_id)
            if subdivision:
                feeders = Feeder.objects(subdivision=subdivision)
                recommendations['feeders'] = [feeder.to_json() for feeder in feeders]
        feeder_id = request.args.get('feeder_id')
        if feeder_id:
            feeder = find_feeder(feeder_id)
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

        division = find_division(division_id)
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

@poleSurvey.route('/transformer', methods=['POST','GET','PATCH'])
def handle_transformer():
    if request.method == 'PATCH':
        try:
            data = request.get_json(silent=True) or request.form or {}
            tc_id = request.args.get('tc_id') or request.args.get('tc_number') or data.get('tc_id') or data.get('tc_number')
            tc = find_transformer(tc_id)
            if not tc:
                return jsonify({"error": "Transformer not found"}), 404

            image_bytes = extract_image_bytes(request)
            if data.get('name') or data.get('tc_name'):
                tc.name = data.get('name') or data.get('tc_name')
            if data.get('tc_number'):
                tc.tc_number = data.get('tc_number')
            if data.get('lat') is not None:
                tc.lat = float(data.get('lat'))
            if data.get('long') is not None:
                tc.long = float(data.get('long'))
            if data.get('capacity'):
                tc.capacity = data.get('capacity')
            if image_bytes is not None:
                tc.image = image_bytes
            tc.save()
            return jsonify({"message": "Transformer updated successfully", "tc": tc.to_json()}), 200
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or request.form or {}
            image_bytes = extract_image_bytes(request)

            tc_number = data.get('tc_number')
            feeder_id = data.get('feeder_id')
            tc_name = data.get('tc_name') or data.get('name')
            lat = data.get('lat')
            long = data.get('long')
            capacity = data.get('capacity')

            if not tc_number:
                return jsonify({"error": "tc_number is required"}), 400

            # UPSERT Check: Check if transformer with tc_number already exists
            existing_tc = find_transformer(tc_number)
            if existing_tc:
                if tc_name: existing_tc.name = tc_name
                if lat is not None: existing_tc.lat = float(lat)
                if long is not None: existing_tc.long = float(long)
                if capacity: existing_tc.capacity = capacity
                if feeder_id:
                    feeder = find_feeder(feeder_id)
                    if feeder: existing_tc.feeder = feeder
                if image_bytes is not None: existing_tc.image = image_bytes
                existing_tc.save()
                return jsonify({"message": "Transformer updated/retrieved successfully", "tc_id": str(existing_tc.id), "tc": existing_tc.to_json()}), 200

            if not feeder_id:
                return jsonify({"error": "feeder_id is required"}), 400

            feeder = find_feeder(feeder_id)
            if not feeder:
                return jsonify({"error": "Feeder not found"}), 404

            transformer = Transformer(
                tc_number=tc_number,
                name=tc_name or tc_number,
                feeder=feeder,
                lat=float(lat) if lat is not None else None,
                long=float(long) if long is not None else None,
                capacity=capacity,
                image=image_bytes
            )
            transformer.save()

            return jsonify({"message": "Transformer created", "tc_id": str(transformer.id), "tc": transformer.to_json()}), 201
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    if request.method == 'GET':
        try:
            tc_id = request.args.get('tc_id') or request.args.get('tc_number')
            feeder_id = request.args.get('feeder_id')
            if tc_id:
                tc = find_transformer(tc_id)
                if not tc:
                    return jsonify({"error": "Transformer not found"}), 404
                return jsonify({"tc": tc.to_json()}), 200

            if feeder_id:
                feeder = find_feeder(feeder_id)
                tcs = Transformer.objects(feeder=feeder) if feeder else []
            else:
                tcs = Transformer.objects()
            return jsonify({"tcs": [tc.to_json() for tc in tcs]}), 200
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

        subdivision = find_subdivision(subdivision_id)
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

@poleSurvey.route('/pole', methods=['POST','GET','PATCH'])
def create_pole():
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or request.form

            client_tx_id = data.get("client_tx_id")
            if client_tx_id:
                existing_tx_pole = Pole.objects(client_tx_id=client_tx_id).first()
                if existing_tx_pole:
                    return jsonify({
                        "message": "Existing pole updated/retrieved successfully",
                        "pole_id": str(existing_tx_pole.id),
                        "tc_id": str(existing_tx_pole.tc.id) if existing_tx_pole.tc else None,
                        "tc_number": existing_tx_pole.tc.tc_number if existing_tx_pole.tc else None,
                        "pole_number": existing_tx_pole.pole_number,
                        "is_existing": existing_tx_pole.is_existing,
                        "span_length": existing_tx_pole.span_length,
                        "sag": existing_tx_pole.sag,
                        "pole": existing_tx_pole.to_json()
                    }), 200

            tc_id = data.get("tc_id") or data.get("tc_number") or data.get("tc")
            pole_number = data.get("pole_number")
            is_existing = data.get("is_existing")
            if isinstance(is_existing, str):
                is_existing = is_existing.lower() in ['true', '1', 'yes']
            previous_connector_type = data.get("previous_connector_type")  # "tc" or "pole"
            previous_connector_id = data.get("previous_connector_id")
            lat = data.get("lat")
            long = data.get("long")
            if lat is not None: lat = float(lat)
            if long is not None: long = float(long)

            image_bytes = extract_image_bytes(request)

            if not tc_id or not pole_number or lat is None or long is None:
                return jsonify({"error": "TC ID/Number, pole Number, lat and long are required"}), 400

            # Lookup the Transformer by ID or TC Number
            tc = find_transformer(tc_id)
            if not tc:
                return jsonify({"error": "Transformer (TC) not found"}), 404

            # Calculate span_length
            span_length = 0.0
            if previous_connector_type and previous_connector_id:
                if previous_connector_type == "tc":
                    connector = find_transformer(previous_connector_id)
                elif previous_connector_type == "pole":
                    connector = find_pole(previous_connector_id)
                else:
                    return jsonify({"error": "Invalid previous_connector_type"}), 400
                
                if connector and connector.lat is not None and connector.long is not None:
                    span_length = haversine(connector.lat, connector.long, lat, long)

            # UPSERT Check: Check if pole with (tc, pole_number) already exists
            existing_pole = Pole.objects(tc=tc, pole_number=pole_number).first()
            if existing_pole:
                existing_pole.is_existing = bool(is_existing)
                existing_pole.lat = lat
                existing_pole.long = long
                if span_length:
                    existing_pole.span_length = round(span_length, 2)
                if previous_connector_type:
                    existing_pole.previous_connector = f"{previous_connector_type}-{previous_connector_id}"
                if image_bytes is not None:
                    existing_pole.image = image_bytes
                if client_tx_id:
                    existing_pole.client_tx_id = client_tx_id
                existing_pole.save()

                return jsonify({
                    "message": "Existing pole updated/retrieved successfully",
                    "pole_id": str(existing_pole.id),
                    "tc_id": str(tc.id),
                    "tc_number": tc.tc_number,
                    "pole_number": existing_pole.pole_number,
                    "is_existing": existing_pole.is_existing,
                    "span_length": existing_pole.span_length,
                    "sag": existing_pole.sag,
                    "pole": existing_pole.to_json()
                }), 200

            pole = Pole(
                tc=tc,
                pole_number=pole_number,
                is_existing=bool(is_existing),
                previous_connector=f"{previous_connector_type}-{previous_connector_id}" if previous_connector_type else None,
                lat=lat,
                long=long,
                span_length=round(span_length,2) if span_length else 0.0,
                image=image_bytes,
                client_tx_id=client_tx_id
            )
            pole.save()

            return jsonify({
                "message": "Pole created successfully",
                "pole_id": str(pole.id),
                "tc_id": str(tc.id),
                "tc_number": tc.tc_number,
                "pole_number": pole.pole_number,
                "is_existing": pole.is_existing,
                "span_length": round(span_length,2) if span_length else 0.0,
                "sag": pole.sag,
                "pole": pole.to_json()
            }), 201

        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    if request.method == 'GET':
        try:
            poleId = request.args.get('poleId') or request.args.get('pole_id') or request.args.get('pole_number')
            if not poleId:
                return jsonify({"error": "poleId/pole_number is required"}), 400
            pole = find_pole(poleId)
            if not pole:
                return jsonify({"error": "Pole not found"}), 404
            return jsonify(pole.to_json()), 200
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    if request.method == 'PATCH':
        try:
            data = request.get_json(silent=True) or request.form
            span_length = data.get("span_length")
            sag = data.get("sag")
            poleId = request.args.get('pole_id') or request.args.get('poleId') or (data.get('pole_id') if data else None) or (data.get('pole_number') if data else None)
            if not poleId:
                return jsonify({"error": "pole_id is required"}), 400
            pole = find_pole(poleId)
            if not pole:
                return jsonify({"error": "Pole not found"}), 404

            if span_length is not None: pole.span_length = float(span_length)
            if sag is not None: pole.sag = int(sag)

            image_bytes = extract_image_bytes(request)
            if image_bytes is not None:
                pole.image = image_bytes

            pole.save()
            return jsonify({"message": "Pole updated successfully", "pole": pole.to_json()}), 200
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
@poleSurvey.route('/poles', methods=['GET'])
def get_pole_numbers_by_tc():
    if request.method == 'GET':
        try:
            tc_id = request.args.get('tc_id') or request.args.get('tc_number') or request.args.get('tc')
            feeder_id = request.args.get('feeder_id')

            if feeder_id:
                feeder = find_feeder(feeder_id)
                if not feeder:
                    return jsonify({"error": "Feeder not found"}), 404
                tcs = Transformer.objects(feeder=feeder)
                poles = Pole.objects(tc__in=tcs)
                poles_data = [{
                    "id": str(pole.id),
                    "pole_number": pole.pole_number,
                    "tc_number": pole.tc.tc_number if pole.tc else None,
                    "is_existing": pole.is_existing,
                } for pole in poles]
                return jsonify({"pole_numbers": poles_data, "poles": [p.to_json() for p in poles]}), 200

            if not tc_id:
                return jsonify({"error": "tc_id, tc_number or feeder_id is required"}), 400

            tc = find_transformer(tc_id)
            if not tc:
                return jsonify({"error": "Transformer not found"}), 404

            poles = Pole.objects(tc=tc)
            pole_numbers = [{
                    "id": str(pole.id),
                    "pole_number": pole.pole_number,
                } for pole in poles]

            return jsonify({"pole_numbers": pole_numbers, "poles": [p.to_json() for p in poles]}), 200
        except Exception as e:
            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
    
@poleSurvey.route('/questions', methods=['GET'])
def getQuestions():
    try:
        # Original list of existing questions, now we need to enrich them with types
        existing_questions_list = [
            "Type of Arrangement",
            "Type of Conductor",
            "Type of Pole", # This was "Type of PSC/RSJ" in excel, assuming "Type of Pole" covers it
            "Condition of Pole",
            "Danger Board",
            "Barbed wire",
            "LT Cross Arm",
            "C Type L T cross arm",
            "L T Porcelain Pin Insulators",
            "Connection Box",
            "Stay set (GUY SET)",
            "Coil Earthing",
            "Guarding",
            "TREE CUTTING" # Assuming this maps to "REQUIREMENTS OF TREE CUTTING (YES/NO)"
        ]

        # Original list of proposed questions, now we need to enrich them with types
        proposed_questions_list = [
            "Type of Arrangement",
            "Coil Earthing",
            "Guarding",
            "Self-Tightening Anchoring Clamp",
            "Suspension Clamp", # Assuming this is "Self-locking suspensionclam with pole bracket"
            "Mid-span Joints",
            "Stainless steel-20mm", # Assuming this is "Stainless steel of size strap 20mm*0.7mm& Buc"
            "IPC", # Assuming this is "Insulation piercing connector (I P C)"
            "EYE HOOKS",
            "1PH Connection Box(8 connections)", # Assuming this maps to "Supply of 1-Ph Pole mounted service connection"
            "3PH Connection Box(4 connections)", # Assuming this maps to "Supply of 3-ph Pole mounted service connector"
            "4Cx10 mm2 LT PVC Cable",
            "4Cx16 mm2 LT PVC Cable"
        ]

        # Function to map questions to their types
        def get_typed_questions(questions_list):
            typed_questions = []
            for q in questions_list:
                if q == "Type of Arrangement":
                    typed_questions.append({"question": q, "type": "string", "options": ["1Ph", "3Ph"]})
                elif q == "Type of Conductor":
                    typed_questions.append({"question": q, "type": "string", "options": ["Dog", "Rabbit", "Weasel"]})
                elif q == "Type of Pole":
                    typed_questions.append({"question": q, "type": "string", "options": ["PSC", "RSJ"]})
                elif q == "Condition of Pole":
                    typed_questions.append({"question": q, "type": "string", "options": ["Good", "Damaged", "Rusted",'Bend']})
                elif q == "TREE CUTTING":
                     typed_questions.append({"question": q, "type": "string", "options": ["YES", "NO"]})
                elif q == "Suspension Clamp":
                     typed_questions.append({"question": q, "type": "integer"})
                elif q == "Stainless steel-20mm":
                     typed_questions.append({"question": q, "type": "integer"})
                else:
                    # For direct matches, get type from definitions, default to 'string' if not found
                    typed_questions.append({"question": q, "type": "integer"})
            return typed_questions


        existing_questions_typed = get_typed_questions(existing_questions_list)
        proposed_questions_typed = get_typed_questions(proposed_questions_list)


        return jsonify([
            {"existingQuestions": existing_questions_typed},
            {"proposedQuestion": proposed_questions_typed}
        ]), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@poleSurvey.route('/material-info/<poleId>', methods=['POST'])
def fillMaterial(poleId):
    try:
        data = request.get_json(silent=True) or request.form or {}
        actual_pole_id = poleId or request.args.get("pole_id") or data.get("pole_id") or data.get("pole_number")
        pole = find_pole(actual_pole_id)
        if not pole:
            return jsonify({"error": "Pole not found"}), 404

        requestPoleType = request.args.get("poleType") or data.get("poleType") or "new_proposed"
        existingvalues = data

        client_tx_id = data.get("client_tx_id")
        if client_tx_id:
            pole.client_tx_id = client_tx_id

        image_bytes = extract_image_bytes(request)
        if image_bytes is not None:
            pole.image = image_bytes

        if pole.is_existing == False:
            pole.proposed_materials['8mtr PSC'] = 1
            pole.proposed_materials['Danger Board'] = 1
            pole.proposed_materials['Barbed Wire'] = 1
            pole.proposed_materials['Stay set'] = 1

        for key, value in existingvalues.items():
            if key in ['image', 'photo', 'image_base64', 'client_tx_id', 'pole_id', 'poleId', 'poleType']:
                continue
            if requestPoleType == 'existing':
                pole.existing_info[key] = value
            elif requestPoleType == 'new_proposed':
                pole.proposed_materials[key] = value

        if existingvalues.get('Type of Arrangement') == "3Ph":
            if pole.is_existing == True and requestPoleType=='existing':
                pole.existing_info['Span Three Phase'] = pole.span_length
            elif requestPoleType=='new_proposed':
                pole.proposed_materials['3Core Wire'] = pole.span_length
        elif existingvalues.get('Type of Arrangement') == "1Ph":
            if pole.is_existing == True and requestPoleType=='existing':
                pole.existing_info['Span Single Phase'] = pole.span_length
            elif requestPoleType=='new_proposed':
                pole.proposed_materials['1Core Wire'] = pole.span_length

        pole.save()

        return jsonify({
            "success": True,
            "message": "Material information saved successfully",
            "pole_id": str(pole.id),
            "pole": pole.to_json()
        }), 200
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
            

@poleSurvey.route("/export/pole-schedule/<feeder_id>", methods=["GET"])
def export_feeder_poles(feeder_id):
    try:
        feeder = find_feeder(feeder_id)
        if not feeder:
            return jsonify({"error": "Feeder not found"}), 404
        transformers = Transformer.objects(feeder=feeder)
        transformer_ids = [t.id for t in transformers]

        # Step 2: Get all poles for these transformers
        poles = Pole.objects(tc__in=transformer_ids)

        # Step 3: Get feeder, subdivision info
        subdivision = feeder.subdivision.name if feeder.subdivision else ""
        feeder_name = feeder.name
        excel_stream = generate_feeder_pole_excel(feeder_name, subdivision, poles)

        return send_file(
            excel_stream,
            download_name=f"{feeder.name}_PoleScheduler.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
            