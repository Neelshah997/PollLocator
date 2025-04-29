from flask_mongoengine import MongoEngine

database = MongoEngine()

def initializeDB(app):
    database.init_app(app)