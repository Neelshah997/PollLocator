from flask import Flask, request, jsonify, send_file, render_template_string
from database.db import initializeDB
from database.models import User
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv 
import os
from urllib.parse import quote_plus

load_dotenv()

password = quote_plus(os.getenv('MONGODB_PASSWORD', 'Test1234'))
default_host = f"mongodb+srv://qsinnotech:{password}@cluster0.h3cbvc2.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0"
mongodb_uri = os.getenv('MONGODB_URI', default_host)

app = Flask(__name__)

app.config['MONGODB_SETTINGS'] = {
        'host': mongodb_uri
}

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_secret_key')  # default if not set

initializeDB(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    try:
        user_id = jwt_payload.get("sub")
        token_version = jwt_payload.get("token_version", 1)
        if not user_id:
            return True
        user = User.objects(id=user_id).first()
        if not user:
            return True
        user_version = getattr(user, 'token_version', 1)
        if user_version is None:
            user_version = 1
        if user_version > token_version:
            return True
    except Exception as e:
        print("Token check exception:", e)
        return True
    return False

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return jsonify({
        "error": "token_invalid",
        "message": "Your session has been revoked by an administrator."
    }), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        "error": "token_expired",
        "message": "Your token has expired."
    }), 403

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        "error": "token_missing",
        "message": "Authorization token is missing."
    }), 401

from resources.routes import poleSurvey
app.register_blueprint(poleSurvey)

@app.route('/swagger.json', methods=['GET'])
def get_swagger_json():
    return send_file('swagger.json', mimetype='application/json')

@app.route('/docs', methods=['GET'])
def swagger_ui():
    swagger_ui_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Pole Locator Survey API Docs</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4/swagger-ui.css">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
        <script>
            window.onload = () => {
                window.ui = SwaggerUIBundle({
                    url: '/swagger.json',
                    dom_id: '#swagger-ui',
                });
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(swagger_ui_html)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=8095,debug=True)