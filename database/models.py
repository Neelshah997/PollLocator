# models.py

from mongoengine import Document, StringField, ReferenceField, DateTimeField,FloatField,BooleanField,DictField,IntField
from datetime import datetime

class Role(Document):
    name = StringField(required=True, unique=True)  # e.g., 'user', 'admin', 'agent'
    description = StringField()

    def to_json(self):
        return {"id": str(self.id), "name": self.name}


class User(Document):
    name = StringField(required=True)
    email = StringField()
    password = StringField(required=True)  # Hashed password
    phone = StringField(required=True, unique=True)
    role = ReferenceField(Role, required=True)
    created_at = DateTimeField(default=datetime.utcnow)

    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role.name if self.role else None,
            "created_at": self.created_at.isoformat(),
        }

class Division(Document):
    name = StringField(required=True,unique=True)  # e.g., "North Division"
    created_at = DateTimeField(default=datetime.utcnow)
    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
        }
# Subdivision Model
class Subdivision(Document):
    name = StringField(required=True,unique=True)  # e.g., "Subdivision A"
    created_at = DateTimeField(default=datetime.utcnow)
    division = ReferenceField(Division, required=True)  # Division this subdivision belongs to
    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "division": {
                "id": str(self.division.id),
                "name": self.division.name
            } if self.division else None
        }
# Feeder Model
class Feeder(Document):
    name = StringField(required=True,unique=True)  # e.g., "Feeder 1"
    created_at = DateTimeField(default=datetime.utcnow)
    subdivision = ReferenceField(Subdivision, required=True)  # Subdivision this feeder belongs to
    meta = {
        'indexes': [
            {'fields': ['name', 'subdivision'], 'unique': True}
        ]
    }
    def to_json(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "subdivision": str(self.subdivision.id),
        }
    
class Transformer(Document):
    tc_number = StringField(required=True, unique=True)
    feeder = ReferenceField(Feeder, required=True)
    lat = FloatField()
    long = FloatField()
    name = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    capacity = StringField()
    def to_json(self):
        return {
            "id": str(self.id),
            "tc_number": self.tc_number,
            "feeder": str(self.feeder.id),
            "lat": self.lat,
            "long":self.long,
        }

class Pole(Document):
    tc = ReferenceField(Transformer, required=True)
    pole_number = StringField(required=True)
    is_existing = BooleanField(default=False)
    previous_connector = StringField()  # "tc-<id>" or "poll-<id>"
    lat = FloatField()
    long = FloatField()
    span_length = FloatField()  # in meters
    created_at = DateTimeField(default=datetime.utcnow)
    existing_info = DictField(default = lambda:{"Type of Arrangement": "",
    "Type of Conductor": "",
    "Type of Pole": "",
    "Condition of Pole": "",
    "Danger Board": "",
    "Barbed Wire": "",
    "LT Cross Arm": "",
    "C Type L T cross arm": "",
    "L T Porcelain Pin Insulators": "",
    "Connection Box": "",
    "Stay set (GUY SET)": "",
    "Coil Earthing": "",
    "Guarding": "",
    "TREE CUTTING": "",
    })  # Store 1-20 keys
    proposed_materials = DictField(default = lambda:{
        "Coil Earthing": "",
    "Guarding": "",
    "TREE CUTTING": "",
    "Self-Tightening Anchoring Clamp": "",
    "Suspension Clamp": "",
    "Mid‐span Joints": "",
    "Stainless steel-20mm*0.7mm": "",
    "IPC": "",
    "EYE HOOKS": "",
    "1PH Connection Box(8 connections)": "",
    "3PH Connection Box(4 connections)": "",
    "4Cx10 mm2 LT PVC Cable": "",
    "4Cx16 mm2 LT PVC Cable": "",
    "8mtr PSC": "1"
    })  # Store 21-40 keys
    sag = IntField()
    def to_json(self):
        return {
            "id": str(self.id),
            "pole_number": self.pole_number,
            "tc_id": str(self.tc.id),
            "existing": self.is_existing,
            "lat": self.lat,
            "long": self.long,
            "span_length": self.span_length,
            "existing_info": self.existing_info,
            "proposed_materials": self.proposed_materials,
            "created_at": self.created_at.isoformat(),
        }
# TC Number
# Exisiting/Non Existing
# Poll Number

