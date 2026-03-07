# ============================================
# OAUTH INTEGRATION FOR SKILLVERIFY
# ============================================
# This shows how to add Google and GitHub OAuth to your Flask app

# 1. First, install required packages:
# pip install flask-dance

# 2. Update your main Flask app (app.py or main.py):

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import random
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

# Allow OAuth to work over HTTP locally
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Relax token scope to prevent crashes when Google returns different scopes than requested
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

app = Flask(__name__)

# ============= GEMINI CONFIGURATION =============
api_key = os.environ.get('GEMINI_API_KEY')
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None
    print("WARNING: GEMINI_API_KEY not set. AI features will be disabled.")

# ============= CONFIGURATION =============
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillverify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ============= MAIL CONFIGURATION =============
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
mail = Mail(app)

# OAuth Configuration
# Google OAuth - Get credentials from https://console.cloud.google.com/
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

# GitHub OAuth - Get credentials from https://github.com/settings/developers
app.config['GITHUB_OAUTH_CLIENT_ID'] = os.environ.get('GITHUB_OAUTH_CLIENT_ID')
app.config['GITHUB_OAUTH_CLIENT_SECRET'] = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET')

db = SQLAlchemy(app)

# ============= OAUTH BLUEPRINTS =============
# Google OAuth Blueprint
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=['profile', 'email'],
    redirect_to='google_callback'
)
app.register_blueprint(google_bp, url_prefix='/login')

# GitHub OAuth Blueprint
github_bp = make_github_blueprint(
    client_id=app.config['GITHUB_OAUTH_CLIENT_ID'],
    client_secret=app.config['GITHUB_OAUTH_CLIENT_SECRET'],
    scope='user:email',
    redirect_to='github_callback'
)
app.register_blueprint(github_bp, url_prefix='/login')

# ============= DATABASE MODELS =============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    name = db.Column(db.String(100))
    oauth_provider = db.Column(db.String(50))  # 'google', 'github', or None
    oauth_id = db.Column(db.String(200))  # ID from OAuth provider
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'oauth_provider': self.oauth_provider,
            'created_at': self.created_at.isoformat()
        }

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_readiness = db.Column(db.Integer, default=0)
    verified_skills = db.Column(db.Integer, default=0)
    total_xp = db.Column(db.Integer, default=0)
    certifications = db.Column(db.Integer, default=0)
    survey_insight = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'skill_readiness': self.skill_readiness,
            'verified_skills': self.verified_skills,
            'total_xp': self.total_xp,
            'certifications': self.certifications,
            'survey_insight': self.survey_insight
        }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True) # e.g. "Tech & Coding"
    tags = db.Column(db.String(255), nullable=True)     # stored as comma-separated "#React,#JavaScript"
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('posts', lazy=True))

    def to_dict(self, current_user_id=None):
        import random
        random_names = ["Alex M.", "Sarah C.", "Marcus R.", "Priya S.", "David T.", "Emma W.", "James K.", "Sofia G.", "Chris J.", "Taylor L."]
        
        # Determine if we should use the system user or a random name
        is_system_user = self.author and self.author.email == "demo@skillverify.com"
        
        if is_system_user:
            random.seed(self.user_id + self.id) # Seed so it's consistent for this post/user combo
            display_name = random.choice(random_names)
            random.seed() # Reset seed
        else:
            display_name = self.author.name if self.author else "Anonymous"
        
        has_liked = False
        has_saved = False
        if current_user_id:
            has_liked = PostLike.query.filter_by(user_id=current_user_id, post_id=self.id).first() is not None
            has_saved = SavedPost.query.filter_by(user_id=current_user_id, post_id=self.id).first() is not None
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author_name': display_name,
            'content': self.content,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'likes': self.likes,
            'comments_count': self.comments_count,
            'has_liked': has_liked,
            'has_saved': has_saved,
            'created_at': self.created_at.isoformat()
        }

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class SavedPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    
    def to_dict(self):
        import random
        random_names = ["Alex M.", "Sarah C.", "Marcus R.", "Priya S.", "David T.", "Emma W.", "James K.", "Sofia G.", "Chris J.", "Taylor L."]
        
        is_system_user = self.author and self.author.email == "demo@skillverify.com"
        if is_system_user:
            random.seed(self.user_id + self.id) # Seed so it's consistent
            display_name = random.choice(random_names)
            random.seed() # Reset seed
        else:
            display_name = self.author.name if self.author else "Anonymous"
            
        return {
            'id': self.id,
            'user_id': self.user_id,
            'post_id': self.post_id,
            'author_name': display_name,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

# ============= OAUTH ROUTES =============

@app.route('/auth/google')
def google_login_route():
    """Initiate Google OAuth login"""
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('google_callback'))

@app.route('/login/google/callback')
def google_callback():
    """Google OAuth callback"""
    if not google.authorized:
        return jsonify({'success': False, 'message': 'Failed to log in with Google'}), 400
    
    # Get user info from Google
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return jsonify({'success': False, 'message': 'Failed to fetch user info from Google'}), 400
    
    google_info = resp.json()
    google_id = google_info['id']
    email = google_info['email']
    name = google_info.get('name', '')
    
    # Check if user exists
    user = User.query.filter_by(oauth_provider='google', oauth_id=google_id).first()
    
    if not user:
        # Check if email already exists with different provider
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Generate OTP for existing user
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['pending_user_id'] = existing_user.id
            
            # Send OTP via Email
            try:
                msg_email = Message('Your Verification Code - SkillVerify', 
                              sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                              recipients=[email])
                msg_email.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.'
                mail.send(msg_email)
                print(f"DEBUG: OAuth collision OTP sent to {email}: {otp}")
            except Exception as e:
                print(f"ERROR: Failed to send email: {e}")
                print(f"DEBUG: OAuth collision OTP for {email} (Fallback): {otp}")
                
            return redirect(url_for('index', show_otp='true', message='Verification code sent to your email.'))
        
        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider='google',
            oauth_id=google_id
        )
        db.session.add(user)
        db.session.commit()
        
        # Create profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    
    # Log user in
    session['user_id'] = user.id
    session['email'] = user.email
    session.permanent = True
    
    return redirect(url_for('index'))

@app.route('/auth/github')
def github_login_route():
    """Initiate GitHub OAuth login"""
    if not github.authorized:
        return redirect(url_for('github.login'))
    return redirect(url_for('github_callback'))

@app.route('/login/github/callback')
def github_callback():
    """GitHub OAuth callback"""
    if not github.authorized:
        return jsonify({'success': False, 'message': 'Failed to log in with GitHub'}), 400
    
    # Get user info from GitHub
    resp = github.get('/user')
    if not resp.ok:
        return jsonify({'success': False, 'message': 'Failed to fetch user info from GitHub'}), 400
    
    github_info = resp.json()
    github_id = str(github_info['id'])
    name = github_info.get('name', github_info.get('login', ''))
    
    # Get email (GitHub doesn't always provide it in /user)
    email_resp = github.get('/user/emails')
    emails = email_resp.json() if email_resp.ok else []
    email = next((e['email'] for e in emails if e['primary']), None)
    
    if not email:
        return jsonify({
            'success': False, 
            'message': 'Could not retrieve email from GitHub. Please make your email public.'
        }), 400
    
    # Check if user exists
    user = User.query.filter_by(oauth_provider='github', oauth_id=github_id).first()
    
    if not user:
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Generate OTP for existing user
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['pending_user_id'] = existing_user.id
            
            # Send OTP via Email
            try:
                msg_email = Message('Your Verification Code - SkillVerify', 
                              sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                              recipients=[email])
                msg_email.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.'
                mail.send(msg_email)
                print(f"DEBUG: OAuth collision OTP sent to {email}: {otp}")
            except Exception as e:
                print(f"ERROR: Failed to send email: {e}")
                print(f"DEBUG: OAuth collision OTP for {email} (Fallback): {otp}")
                
            return redirect(url_for('index', show_otp='true', message='Verification code sent to your email.'))
        
        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider='github',
            oauth_id=github_id
        )
        db.session.add(user)
        db.session.commit()
        
        # Create profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    
    # Log user in
    session['user_id'] = user.id
    session['email'] = user.email
    session.permanent = True
    
    return redirect(url_for('index'))

# ============= REGULAR AUTH ROUTES =============

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user with OTP verification"""
    data = request.get_json()
    
    # === PHASE 2: OTP VERIFICATION ===
    if 'otp' in data:
        otp_input = data.get('otp')
        
        # Check if we have pending registration data
        if 'pending_registration' not in session or 'otp' not in session:
            return jsonify({'success': False, 'message': 'Session expired. Please try registering again.'}), 400
        
        # Verify OTP
        if session.get('otp') == otp_input:
            reg_data = session['pending_registration']
            
            # Double check if user exists (edge case)
            if User.query.filter_by(email=reg_data['email']).first():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400

            # Create User
            user = User(email=reg_data['email'], name=reg_data['name'])
            user.password_hash = reg_data['password_hash'] # Already hashed
            db.session.add(user)
            db.session.commit()
            
            # Create default profile
            profile = UserProfile(
                user_id=user.id,
                skill_readiness=0,
                verified_skills=0,
                total_xp=0,
                certifications=0
            )
            db.session.add(profile)
            db.session.commit()
            
            # Clear session and Auto-Login
            session.pop('otp', None)
            session.pop('pending_registration', None)
            
            session['user_id'] = user.id
            session['email'] = user.email
            session.permanent = True
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': user.to_dict()
            }), 201
        else:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

    # === PHASE 1: INITIAL REGISTRATION REQUEST ===
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['pending_registration'] = {
        'email': email,
        'name': name,
        'password_hash': generate_password_hash(password)
    }
    
    # Send OTP via Email
    try:
        msg = Message('Verify Your Account - SkillVerify', 
                      sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                      recipients=[email])
        msg.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your registration.'
        mail.send(msg)
        print(f"DEBUG: Registration OTP sent to {email}: {otp}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        print(f"DEBUG: Registration OTP for {email} (Fallback): {otp}")

    return jsonify({
        'success': False,
        'otp_required': True,
        'message': 'Verification code sent to your email'
    }), 200

@app.route('/api/login', methods=['POST'])
def login():
    """Login user with OTP verification"""
    data = request.get_json()
    
    # OTP Verification Phase
    if 'otp' in data:
        otp_input = data.get('otp')
        
        # Check if we have a pending login session
        if 'pending_user_id' not in session or 'otp' not in session:
            return jsonify({'success': False, 'message': 'Session expired. Please try logging in again.'}), 400
        
        # Verify OTP
        if session.get('otp') == otp_input:
            user_id = session['pending_user_id']
            user = User.query.get(user_id)
            
            if not user:
                 return jsonify({'success': False, 'message': 'User not found'}), 400

            # Clear temporary session data
            session.pop('otp', None)
            session.pop('pending_user_id', None)
            
            # Finalize Login
            session['user_id'] = user.id
            session['email'] = user.email
            
            if session.get('_remember_me'):
                session.permanent = True
                session.pop('_remember_me', None)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

    # Initial Login Phase (Email/Password)
    email = data.get('email')
    password = data.get('password')
    remember_me = data.get('rememberMe', False)
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    if user.oauth_provider:
        return jsonify({
            'success': False, 
            'message': f'This account uses {user.oauth_provider} login. Please use the {user.oauth_provider} button.'
        }), 401
    
    if not user.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['pending_user_id'] = user.id
    if remember_me:
        session['_remember_me'] = True
    
    # Send OTP via Email
    try:
        msg = Message('Your Verification Code - SkillVerify', 
                      sender=app.config.get('MAIL_USERNAME', 'noreply@skillverify.com'), 
                      recipients=[email])
        msg.body = f'Your verification code is: {otp}\n\nPlease enter this code to complete your login.'
        mail.send(msg)
        print(f"DEBUG: OTP sent to {email}: {otp}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        # For development/demo purposes, print OTP to console
        print(f"DEBUG: OTP for {email} (Fallback): {otp}")
    
    return jsonify({
        'success': False,
        'otp_required': True,
        'message': 'Verification code sent to your email'
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get dashboard data for logged-in user"""
    print(f"DEBUG: get_dashboard_data session: {session}")
    user_id = session.get('user_id')
    
    if not user_id:
        # Return default data if not logged in
        return jsonify({
            'success': True,
            'user': None,
            'stats': {
                'skill_readiness': 87,
                'verified_skills': 12,
                'total_xp': 2450,
                'certifications': 5
            },
            'challenges': []
        }), 200
    
    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'stats': profile.to_dict() if profile else {},
        'challenges': []
    }), 200

@app.route('/api/submit-survey', methods=['POST'])
def submit_survey():
    """Submit career test survey and generate AI insights"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to submit survey'}), 401
    
    data = request.get_json()
    
    insight_text = ""
    if client:
        try:
            # Construct a prompt based on the user's survey answers
            prompt = f"""
            Act as an expert career counselor. Analyze the following career survey responses from a user and provide:
            1. A concise, encouraging paragraph with personalized career insights based on their interests, skills, and goals.
            2. A bulleted list of 3 specific, highly relevant websites, courses, or resources that can help them explore these career paths further (include actual URLs).
            
            Survey Responses:
            {data}
            """
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            insight_text = response.text
        except Exception as e:
            print(f"Error generating insight: {e}")
            insight_text = "Your survey has been recorded! Unfortunately, our AI is currently unavailable to generate personalized insights right now. Please check back later."
    else:
        insight_text = "Your survey has been recorded! AI insights are currently disabled because the GEMINI_API_KEY is not set."

    # Save to the user profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        
    profile.survey_insight = insight_text
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Survey submitted successfully',
        'insight': insight_text
    }), 201

@app.route('/api/update-profile', methods=['PUT'])
def update_profile():
    """Update user profile stats"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
    
    if 'skill_readiness' in data:
        profile.skill_readiness = data['skill_readiness']
    if 'verified_skills' in data:
        profile.verified_skills = data['verified_skills']
    if 'total_xp' in data:
        profile.total_xp = data['total_xp']
    if 'certifications' in data:
        profile.certifications = data['certifications']
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'profile': profile.to_dict()
    }), 200

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Chat API endpoint powered by Gemini"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
        
    try:
        from google import genai
        from google.genai import types
        # Try to use environment variable first, then fallback to the known working key test_api.py
        local_api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyAk0Rxl3-e96BTkdAN1xkhauPjVoGqs5Rg")
        if not local_api_key:
            return jsonify({'success': False, 'message': 'AI features are disabled due to missing API key.'}), 500
            
        client = genai.Client(api_key=local_api_key)
        
        # Use a system instruction to instruct the AI Model to act as a career counselor 
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction="You are an expert career guidance counselor and assistant for SkillVerify. SkillVerify is a career advancement platform with AI-powered assessments, skill verification, and real-world challenges. Be very concise, helpful, and friendly. Answer career-related questions and provide guidance."
            )
        )
        
        if response and response.text:
            return jsonify({'success': True, 'message': response.text}), 200
        else:
            return jsonify({'success': False, 'message': "I'm sorry, I couldn't generate a response."}), 500
            
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"Chat error: {e}\\n{err}")
        return jsonify({'success': False, 'message': "I'm sorry, I'm having trouble connecting to my brain right now.", "error": err}), 500


@app.route('/')
def index():
    show_otp = request.args.get('show_otp')
    message = request.args.get('message', 'Verification code sent to your email.')
    return render_template('dashboard.html', show_otp=show_otp, msg=message)

# ============= CAREER DATA =============
CAREER_DATA = {
    'cs': {
        'title': 'Computer Science',
        'subtitle': 'Build the future of technology through code',
        'careers': [
            {
                'title': 'Software Engineer',
                'description': 'Design, develop, and maintain software systems and applications.',
                'salary': '$120,000',
                'growth': '25% (Much faster than average)',
                'skills': ['Python', 'Java', 'Data Structures', 'System Design']
            },
            {
                'title': 'Data Scientist',
                'description': 'Analyze complex data sets to extract valuable insights.',
                'salary': '$135,000',
                'growth': '36% (Much faster than average)',
                'skills': ['Machine Learning', 'Statistics', 'SQL', 'Python']
            },
            {
                'title': 'Cybersecurity Analyst',
                'description': 'Protect networks and systems from cyber threats.',
                'salary': '$112,000',
                'growth': '32% (Much faster than average)',
                'skills': ['Network Security', 'Cryptography', 'Risk Assessment']
            }
        ]
    },
    'healthcare': {
        'title': 'Health Care',
        'subtitle': 'Make a difference in people\'s lives through medicine',
        'careers': [
            {
                'title': 'Registered Nurse',
                'description': 'Provide and coordinate patient care in hospitals and clinics.',
                'salary': '$77,000',
                'growth': '6% (Faster than average)',
                'skills': ['Patient Care', 'Clinical Skills', 'Communication']
            },
            {
                'title': 'Physician Assistant',
                'description': 'Practice medicine on teams with physicians and other healthcare workers.',
                'salary': '$126,000',
                'growth': '27% (Much faster than average)',
                'skills': ['Diagnosis', 'Treatment', 'Medical History', 'Teamwork']
            },
            {
                'title': 'Physical Therapist',
                'description': 'Help injured or ill people improve their movement and manage pain.',
                'salary': '$97,000',
                'growth': '15% (Much faster than average)',
                'skills': ['Rehabilitation', 'Anatomy', 'Treatment Planning']
            }
        ]
    },
    'habitation': {
        'title': 'Habitation',
        'subtitle': 'Design, build, and maintain our living spaces',
        'careers': [
            {
                'title': 'Architect',
                'description': 'Plan and design houses, factories, office buildings, and other structures.',
                'salary': '$93,000',
                'growth': '3% (As fast as average)',
                'skills': ['Design', 'CAD', 'Creativity', 'Technical Knowledge']
            },
            {
                'title': 'Civil Engineer',
                'description': 'Design, build, and supervise infrastructure projects and systems.',
                'salary': '$89,000',
                'growth': '5% (As fast as average)',
                'skills': ['Engineering Principles', 'Project Management', 'Problem Solving']
            },
            {
                'title': 'Urban Planner',
                'description': 'Develop land use plans and programs that help create communities.',
                'salary': '$79,000',
                'growth': '4% (As fast as average)',
                'skills': ['Analysis', 'Communication', 'GIS', 'Planning Law']
            }
        ]
    },
    'polsci': {
        'title': 'Political Science',
        'subtitle': 'Understand and influence public policy and government',
        'careers': [
            {
                'title': 'Policy Analyst',
                'description': 'Analyze policies and their effects on society and the economy.',
                'salary': '$65,000',
                'growth': '6% (Faster than average)',
                'skills': ['Research', 'Analysis', 'Writing', 'Public Policy']
            },
            {
                'title': 'Legislative Assistant',
                'description': 'Support legislators in drafting and analyzing legislation.',
                'salary': '$58,000',
                'growth': '5% (As fast as average)',
                'skills': ['Research', 'Communication', 'Legislative Process']
            },
            {
                'title': 'Public Relations Specialist',
                'description': 'Create and maintain a positive public image for organizations.',
                'salary': '$67,000',
                'growth': '6% (Faster than average)',
                'skills': ['Communication', 'Media Relations', 'Writing']
            }
        ]
    },
    'veteran': {
        'title': 'Veteran Careers',
        'subtitle': 'Transition military skills to civilian success',
        'careers': [
            {
                'title': 'Operations Manager',
                'description': 'Coordinate and oversee an organization’s operations.',
                'salary': '$98,000',
                'growth': '6% (Faster than average)',
                'skills': ['Leadership', 'Logistics', 'Strategic Planning']
            },
            {
                'title': 'Logistics Coordinator',
                'description': 'Oversee the supply chain and movement of goods.',
                'salary': '$77,000',
                'growth': '18% (Much faster than average)',
                'skills': ['Supply Chain', 'Coordination', 'Problem Solving']
            },
            {
                'title': 'Security Consultant',
                'description': 'Assess and improve an organization’s security measures.',
                'salary': '$95,000',
                'growth': '8% (Faster than average)',
                'skills': ['Risk Assessment', 'Security Procedures', 'Surveillance']
            }
        ]
    }
}

@app.route('/careers')
def careers():
    """Careers page"""
    category = request.args.get('cat', 'all')
    
    if category == 'all':
        # Flatten all careers for 'all' view or just show a selection
        data = {
            'title': 'Explore Careers',
            'subtitle': 'Discover detailed career paths, salary insights, and required skills.',
            'careers': []
        }
        # Add a few examples from each category
        for cat in CAREER_DATA:
            data['careers'].extend(CAREER_DATA[cat]['careers'][:1])
    else:
        data = CAREER_DATA.get(category, CAREER_DATA['cs'])
        
    return render_template('careers.html', data=data, current_cat=category)

@app.route('/careers/<category>')
def specific_career(category):
    """Specific career category page"""
    if category in CAREER_DATA:
        return render_template('careers.html', data=CAREER_DATA[category], current_cat=category)
    return redirect(url_for('careers'))

@app.route('/organizations')
def organizations():
    """Organizations page"""
    return render_template('organizations.html')

@app.route('/community')
def community():
    """Community page"""
    category = request.args.get('category')
    tag = request.args.get('tag')
    post_id = request.args.get('post_id')
    
    query = Post.query
    if post_id:
        query = query.filter_by(id=post_id)
    if category:
        query = query.filter_by(category=category)
    if tag:
        query = query.filter(Post.tags.contains(tag))
        
    posts = query.order_by(Post.created_at.desc()).all()
    current_user_id = session.get('user_id')
    posts_data = [p.to_dict(current_user_id=current_user_id) for p in posts]
    
    return render_template('community.html', posts=posts_data, current_category=category, current_tag=tag)

@app.route('/api/posts', methods=['POST'])
def create_post():
    """Create a new community post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to post'}), 401
        
    data = request.get_json()
    content = data.get('content')
    category = data.get('category', 'Home Feed')
    
    if not content:
        return jsonify({'success': False, 'message': 'Content cannot be empty'}), 400
        
    # Extract tags (words starting with #)
    import re
    tags_list = re.findall(r'#\w+', content)
    tags_str = ','.join(tags_list) if tags_list else None
    
    new_post = Post(
        user_id=user_id,
        content=content,
        category=category,
        tags=tags_str
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Post created successfully',
        'post': new_post.to_dict(current_user_id=user_id)
    }), 201

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def toggle_like(post_id):
    """Toggle a like for a post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to like a post'}), 401
        
    post = Post.query.get_or_404(post_id)
    existing_like = PostLike.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        post.likes = max(0, post.likes - 1)
        action = 'unliked'
    else:
        new_like = PostLike(user_id=user_id, post_id=post_id)
        db.session.add(new_like)
        post.likes += 1
        action = 'liked'
        
    db.session.commit()
    return jsonify({'success': True, 'action': action, 'likes': post.likes})

@app.route('/api/posts/<int:post_id>/save', methods=['POST'])
def toggle_save(post_id):
    """Toggle saving a post"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to save a post'}), 401
        
    post = Post.query.get_or_404(post_id)
    existing_save = SavedPost.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if existing_save:
        db.session.delete(existing_save)
        action = 'unsaved'
    else:
        new_save = SavedPost(user_id=user_id, post_id=post_id)
        db.session.add(new_save)
        action = 'saved'
        
    db.session.commit()
    return jsonify({'success': True, 'action': action})

@app.route('/api/posts/<int:post_id>/comments', methods=['GET', 'POST'])
def handle_comments(post_id):
    """Fetch or create comments for a post"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'GET':
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
        return jsonify({
            'success': True,
            'comments': [c.to_dict() for c in comments]
        })
        
    # POST handling
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to comment'}), 401
        
    data = request.get_json()
    content = data.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'}), 400
        
    new_comment = Comment(user_id=user_id, post_id=post_id, content=content)
    db.session.add(new_comment)
    post.comments_count += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Comment added successfully',
        'comment': new_comment.to_dict(),
        'comments_count': post.comments_count
    }), 201

@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')

@app.route('/about')
def about():
    """About Us page"""
    return render_template('About_US.html')

# ============= INITIALIZATION =============
def init_db():
    with app.app_context():
        db.create_all()
        
        # Seed some posts if none exist
        if Post.query.count() == 0:
            user = User.query.filter_by(email="demo@skillverify.com").first()
            if not user:
                user = User(email="demo@skillverify.com", name="System User")
                db.session.add(user)
                db.session.commit()
                
            demo_posts = [
                Post(user_id=user.id, content="Just completed the Advanced React Challenge! 🎉 After weeks of struggling with state management, I finally understand the Context API and custom hooks. The real-world project really helped solidify my understanding. Anyone else working on this challenge?", category="Tech & Coding", tags="#React,#JavaScript,#Frontend", likes=234, comments_count=45, created_at=datetime.utcnow() - timedelta(hours=2)),
                Post(user_id=user.id, content="Looking for feedback on my portfolio redesign! I've been working on implementing dark mode and improving accessibility. What are some must-have features for a designer portfolio in 2026? 🎨", category="Design", tags="#UXDesign,#Portfolio,#Feedback", likes=189, comments_count=67, created_at=datetime.utcnow() - timedelta(hours=5)),
                Post(user_id=user.id, content="🚀 Career Tip: Don't just list skills on your resume - prove them! I helped 15 candidates get hired last month by showcasing their SkillVerify verified badges. Employers love seeing concrete proof of abilities. What's your experience with skills-based hiring?", category="Career Advice", tags="#CareerAdvice,#JobSearch,#SkillVerified", likes=456, comments_count=89, created_at=datetime.utcnow() - timedelta(days=1)),
                Post(user_id=user.id, content="Just finished building my first machine learning model that predicts customer churn with 94% accuracy! 📈 The journey from zero ML knowledge to deploying a production model took 6 months. Thanks to everyone in this community who answered my questions along the way!", category="Data Science", tags="#MachineLearning,#DataScience,#Python", likes=567, comments_count=92, created_at=datetime.utcnow() - timedelta(days=2))
            ]
            db.session.bulk_save_objects(demo_posts)
            db.session.commit()
            print("✅ Database seeded with demo posts!")
            
        print("✅ Database initialized!")
        pass

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)