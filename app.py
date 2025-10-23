from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, MissingPerson, FoundPerson, SightingReport
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'loket-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file, person_id):
    """Process and save the uploaded image"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"missing_person_{person_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Open and process image
        try:
            image = Image.open(file.stream)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Resize image to reasonable dimensions (max 800x800)
            image.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            # Save processed image
            image.save(filepath, 'JPEG', quality=85, optimize=True)
            
            return filename
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    return None

# Create tables and sample data
def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if we need to add sample data
        if not User.query.first():
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
            print("Sample data created!")

# Routes
@app.route('/')
def index():
    missing_persons = MissingPerson.query.filter_by(is_found=False).order_by(MissingPerson.date_reported.desc()).limit(6).all()
    found_persons = FoundPerson.query.order_by(FoundPerson.date_added.desc()).limit(3).all()
    return render_template('index.html', 
                         missing_persons=missing_persons,
                         found_persons=found_persons)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(name=name, email=email, phone=phone)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/browse')
def browse():
    region = request.args.get('region', '')
    query = request.args.get('q', '')
    
    missing_persons = MissingPerson.query.filter_by(is_found=False)
    
    if region:
        missing_persons = missing_persons.filter_by(region=region)
    
    if query:
        missing_persons = missing_persons.filter(
            (MissingPerson.name.ilike(f'%{query}%')) | 
            (MissingPerson.description.ilike(f'%{query}%'))
        )
    
    missing_persons = missing_persons.order_by(MissingPerson.date_reported.desc()).all()
    regions = db.session.query(MissingPerson.region).distinct().all()
    regions = [r[0] for r in regions if r[0]]
    
    return render_template('browse.html', 
                         missing_persons=missing_persons,
                         regions=regions,
                         selected_region=region,
                         search_query=query)

@app.route('/report-missing', methods=['GET', 'POST'])
@login_required
def report_missing():
    if request.method == 'POST':
        # First create the missing person record to get an ID
        missing_person = MissingPerson(
            name=request.form.get('name'),
            age=request.form.get('age'),
            gender=request.form.get('gender'),
            last_seen=request.form.get('last_seen'),
            last_seen_date=datetime.strptime(request.form.get('last_seen_date'), '%Y-%m-%d').date(),
            region=request.form.get('region'),
            description=request.form.get('description'),
            contact_name=request.form.get('contact_name'),
            contact_phone=request.form.get('contact_phone'),
            contact_email=request.form.get('contact_email'),
            reported_by=current_user.id
        )
        
        db.session.add(missing_person)
        db.session.flush()  # This assigns an ID without committing
        
        # Handle file upload
        file = request.files.get('photo')
        if file and file.filename:
            filename = process_image(file, missing_person.id)
            if filename:
                missing_person.photo_filename = filename
        
        db.session.commit()
        
        flash('Missing person report submitted successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('report.html')

@app.route('/report-sighting/<int:person_id>', methods=['POST'])
@login_required
def report_sighting(person_id):
    missing_person = MissingPerson.query.get_or_404(person_id)
    
    sighting = SightingReport(
        missing_person_id=person_id,
        location=request.form.get('location'),
        sighting_date=datetime.strptime(request.form.get('sighting_date'), '%Y-%m-%dT%H:%M'),
        details=request.form.get('details'),
        reporter_name=request.form.get('reporter_name'),
        reporter_contact=request.form.get('reporter_contact'),
        reported_by=current_user.id
    )
    
    db.session.add(sighting)
    db.session.commit()
    
    flash('Sighting report submitted successfully!', 'success')
    return redirect(url_for('browse'))

@app.route('/profile')
@login_required
def profile():
    user_reports = MissingPerson.query.filter_by(reported_by=current_user.id).order_by(MissingPerson.date_reported.desc()).all()
    return render_template('profile.html', user_reports=user_reports)

@app.route('/case-details/<int:person_id>')
def case_details(person_id):
    missing_person = MissingPerson.query.get_or_404(person_id)
    return render_template('case_details.html', person=missing_person)

# Serve uploaded files
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API endpoints for AJAX
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    region = request.args.get('region', '')
    
    missing_persons = MissingPerson.query.filter_by(is_found=False)
    
    if query:
        missing_persons = missing_persons.filter(
            (MissingPerson.name.ilike(f'%{query}%')) | 
            (MissingPerson.description.ilike(f'%{query}%'))
        )
    
    if region:
        missing_persons = missing_persons.filter_by(region=region)
    
    results = missing_persons.order_by(MissingPerson.date_reported.desc()).all()
    
    # Convert to JSON-serializable format
    results_data = []
    for person in results:
        results_data.append({
            'id': person.id,
            'name': person.name,
            'age': person.age,
            'gender': person.gender,
            'last_seen': person.last_seen,
            'last_seen_date': person.last_seen_date.strftime('%Y-%m-%d'),
            'region': person.region,
            'description': person.description,
            'photo_url': person.photo_url,
            'reporter_name': person.reporter.name
        })
    
    return jsonify(results_data)

if __name__ == '__main__':
    init_db()  # Initialize database and sample data
    app.run(debug=True, host='0.0.0.0', port=5000)