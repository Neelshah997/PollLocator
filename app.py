from flask import Flask,request
from database.db import initializeDB
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

from resources.routes import poleSurvey
app.register_blueprint(poleSurvey)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=8095,debug=True)