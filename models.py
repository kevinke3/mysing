from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), default='user')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    missing_persons = db.relationship('MissingPerson', backref='reporter', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MissingPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    last_seen = db.Column(db.String(200), nullable=False)
    last_seen_date = db.Column(db.Date, nullable=False)
    region = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(200), default='/static/images/default-avatar.png')
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    is_found = db.Column(db.Boolean, default=False)
    
    # Foreign key
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class FoundPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    found_date = db.Column(db.Date, nullable=False)
    reunited_with = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(200), default='/static/images/default-avatar.png')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class SightingReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    missing_person_id = db.Column(db.Integer, db.ForeignKey('missing_person.id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    sighting_date = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.Text)
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_contact = db.Column(db.String(100), nullable=False)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    missing_person = db.relationship('MissingPerson', backref='sightings', lazy=True)
    user = db.relationship('User', backref='sighting_reports', lazy=True)