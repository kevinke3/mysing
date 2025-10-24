from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, MissingPerson, FoundPerson, SightingReport, PasswordResetToken
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from datetime import timedelta

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'loket-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Gmail Configuration for Loket
EMAIL_CONFIG = {
    'SMTP_SERVER': 'smtp.gmail.com',
    'SMTP_PORT': 587,
    'SENDER_EMAIL': 'myssing.help@gmail.com',  # Your dedicated Gmail
    'SENDER_PASSWORD': 'foql qinw zomt frvm',  # You'll generate this from Gmail
    'SENDER_NAME': 'Mysing Missing Persons'
}

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

def send_password_reset_email(recipient_email, reset_url, user_name):
    """
    Send password reset email using Gmail SMTP
    """
    try:
        # Create message
        message = MIMEMultipart()
        message['From'] = f"{EMAIL_CONFIG['SENDER_NAME']} <{EMAIL_CONFIG['SENDER_EMAIL']}>"
        message['To'] = recipient_email
        message['Subject'] = "Reset Your Mysing Password"
        
        # Beautiful email template (keep the same HTML content)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ 
                    font-family: 'Inter', Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    margin: 0; 
                    padding: 0; 
                    background: #f5f5f5;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: #0077B6; 
                    color: white; 
                    padding: 30px 20px; 
                    text-align: center; 
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                }}
                .header p {{
                    margin: 5px 0 0 0;
                    opacity: 0.9;
                }}
                .content {{ 
                    padding: 30px; 
                }}
                .button {{ 
                    display: inline-block; 
                    background: #0077B6; 
                    color: white; 
                    padding: 14px 28px; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                    font-weight: 600;
                    font-size: 16px;
                    transition: all 0.3s ease;
                }}
                .button:hover {{
                    background: #005a8c;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0, 119, 182, 0.3);
                }}
                .footer {{ 
                    text-align: center; 
                    margin-top: 30px; 
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                    color: #666; 
                    font-size: 14px;
                }}
                .security-note {{
                    background: #E6F2F9;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #0077B6;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #0077B6;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size: 48px; margin-bottom: 10px;">🔍</div>
                    <h1>mysing</h1>
                    <p>Missing Persons Identification & Recovery</p>
                </div>
                <div class="content">
                    <h2 style="color: #0077B6; margin-top: 0;">Password Reset Request</h2>
                    
                    <p>Hello <strong>{user_name}</strong>,</p>
                    
                    <p>We received a request to reset your password for your Loket account. Click the button below to create a new secure password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Your Password</a>
                    </div>
                    
                    <div class="security-note">
                        <strong>⚠️ Important Security Note:</strong>
                        <p>This password reset link will expire in <strong>1 hour</strong> for your security. If you didn't request this reset, please ignore this email - your account remains safe.</p>
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px; font-size: 14px;">
                        {reset_url}
                    </p>
                    
                    <div class="footer">
                        <div class="logo">Mysing</div>
                        <p>Bringing hope to families • Reuniting loved ones</p>
                        <p>If you need help, reply to this email or contact support</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text = f"""
        LOKET - Password Reset Request
        
        Hello {user_name},
        
        We received a request to reset your password for your Loket account.
        
        Reset your password here: {reset_url}
        
        This link expires in 1 hour for security reasons.
        
        If you didn't request this reset, please ignore this email.
        
        Thank you for helping us reunite families,
        
        The mysing Team
        Bringing hope to families • Reuniting loved ones
        """
        
        # Add both HTML and plain text versions
        message.attach(MIMEText(text, 'plain'))
        message.attach(MIMEText(html, 'html'))
        
        # Create SMTP session
        server = smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()  # Enable security
        server.login(EMAIL_CONFIG['SENDER_EMAIL'], EMAIL_CONFIG['SENDER_PASSWORD'])
        
        # Send email
        server.send_message(message)
        server.quit()
        
        print(f"✅ Password reset email sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email to {recipient_email}: {e}")
        return False

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

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = PasswordResetToken.generate_token(user.id)
            reset_url = url_for('reset_password', token=token.token, _external=True)
            
            # Send email
            if send_password_reset_email(user.email, reset_url, user.name):
                flash('✅ Password reset link has been sent to your email. Please check your inbox.', 'success')
            else:
                flash('❌ Failed to send email. Please try again later or contact support.', 'error')
        else:
            # Don't reveal whether email exists or not (security best practice)
            flash('📧 If an account with that email exists, a reset link has been sent. Please check your email.', 'success')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        flash('Invalid or expired reset link. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update user password
        user = reset_token.user
        user.set_password(password)
        
        # Mark token as used
        reset_token.used = True
        
        db.session.commit()
        
        flash('Your password has been reset successfully. You can now login with your new password.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', token=token)

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

# Test email setup route
@app.route('/test-email-setup')
def test_email_setup():
    """Test the email configuration"""
    try:
        # Test connection
        server = smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(EMAIL_CONFIG['SENDER_EMAIL'], EMAIL_CONFIG['SENDER_PASSWORD'])
        server.quit()
        
        # Test email sending
        test_success = send_password_reset_email(
            'test@example.com', 
            'https://example.com/reset?token=test', 
            'Test User'
        )
        
        if test_success:
            return """
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #28a745;">✅ Email Setup Successful!</h1>
                <p>Your Gmail configuration is working correctly.</p>
                <p>You can now test the password reset feature.</p>
            </div>
            """
        else:
            return """
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #dc3545;">❌ Email Setup Failed</h1>
                <p>Check your app password and configuration.</p>
            </div>
            """
            
    except Exception as e:
        return f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1 style="color: #dc3545;">❌ Email Setup Error</h1>
            <p>Error: {e}</p>
            <p>Check your Gmail app password configuration.</p>
        </div>
        """

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