from flask import Flask,request
from resources.routes import poleSurvey
from database.db import initializeDB
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv 
import os
from urllib.parse import quote_plus

password = quote_plus(os.environ.get('MONGODB_PASSWORD', 'Test1234'))

load_dotenv()
app = Flask(__name__)

app.register_blueprint(poleSurvey)
app.config['MONGODB_SETTINGS'] = {
        'host':f"mongodb://qsinnotech:{password}@ac-ghjzltd-shard-00-00.foj9csc.mongodb.net:27017,ac-ghjzltd-shard-00-01.foj9csc.mongodb.net:27017,ac-ghjzltd-shard-00-02.foj9csc.mongodb.net:27017/poleSurvey?ssl=true&replicaSet=atlas-12dihf-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
}

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_secret_key')  # default if not set

initializeDB(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=8095,debug=True)