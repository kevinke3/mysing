from flask import Flask
from models import db, User, MissingPerson, FoundPerson
from datetime import datetime
import os

# Create a minimal Flask app for database operations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with the app
db.init_app(app)

def reset_database():
    with app.app_context():
        # Delete existing database
        if os.path.exists('instance/loket.db'):
            os.remove('instance/loket.db')
            print("🗑️  Old database deleted")
        
        # Create new tables with updated schema
        db.create_all()
        print("✅ New database created with all models")
        
        # Add sample data
        # Create admin user
        admin = User(
            name='Admin User',
            email='admin@loket.org',
            phone='(555) 000-0000',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create sample missing person
        missing_person = MissingPerson(
            name='Sarah Johnson',
            age=28,
            gender='Female',
            last_seen='Central Park, New York',
            last_seen_date=datetime(2024, 1, 15).date(),
            region='Northeast',
            description='Last seen wearing blue jeans and a red jacket. Brown hair, green eyes.',
            contact_name='Michael Johnson',
            contact_phone='(555) 123-4567',
            contact_email='m.johnson@email.com',
            reported_by=1
        )
        db.session.add(missing_person)
        
        # Create sample found person
        found_person = FoundPerson(
            name='Emily Rodriguez',
            age=32,
            found_date=datetime(2024, 1, 5).date(),
            reunited_with='Family in Miami'
        )
        db.session.add(found_person)
        
        db.session.commit()
        print("✅ Sample data added successfully!")
        print("\n🎉 Database reset complete!")
        print("🔑 Default admin login: admin@loket.org / admin123")
        print("🚀 You can now run: python app.py")

if __name__ == '__main__':
    reset_database()