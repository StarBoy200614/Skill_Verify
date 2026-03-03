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
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

app = Flask(__name__)

# ============= CONFIGURATION =============
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillverify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    redirect_to='google_login'
)
app.register_blueprint(google_bp, url_prefix='/login')

# GitHub OAuth Blueprint
github_bp = make_github_blueprint(
    client_id=app.config['GITHUB_OAUTH_CLIENT_ID'],
    client_secret=app.config['GITHUB_OAUTH_CLIENT_SECRET'],
    scope='user:email',
    redirect_to='github_login'
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
            return jsonify({
                'success': False, 
                'message': 'An account with this email already exists. Please log in with your password.'
            }), 400
        
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
            return jsonify({
                'success': False, 
                'message': 'An account with this email already exists. Please log in with your password.'
            }), 400
        
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
    """Regular email/password registration"""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400
    
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Create profile
    profile = UserProfile(user_id=user.id)
    db.session.add(profile)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    """Regular email/password login"""
    data = request.get_json()
    
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
    
    session['user_id'] = user.id
    session['email'] = user.email
    
    if remember_me:
        session.permanent = True
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Chat API endpoint powered by Gemini"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
        
    try:
        import google.generativeai as genai
        # Try to use environment variable first, then fallback to the known working key test_api.py
        api_key = os.environ.get('GEMINI_API_KEY', "AIzaSyAk0Rxl3-e96BTkdAN1xkhauPjVoGqs5Rg")
        genai.configure(api_key=api_key)
        
        # Use a system instruction to instruct the AI Model to act as a career counselor 
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction="You are an expert career guidance counselor and assistant for SkillVerify. SkillVerify is a career advancement platform with AI-powered assessments, skill verification, and real-world challenges. Be very concise, helpful, and friendly. Answer career-related questions and provide guidance."
        )
        response = model.generate_content(message)
        
        if response and response.text:
            return jsonify({'success': True, 'message': response.text}), 200
        else:
            return jsonify({'success': False, 'message': "I'm sorry, I couldn't generate a response."}), 500
            
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'success': False, 'message': "I'm sorry, I'm having trouble connecting to my brain right now."}), 500

@app.route('/')
def index():
    return render_template('dashboard.html')

# ============= INITIALIZATION =============
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database initialized!")
        print("\n🔐 OAuth Setup Required:")
        print("1. Google: https://console.cloud.google.com/")
        print("2. GitHub: https://github.com/settings/developers")
        print("\nSet environment variables:")
        print("  GOOGLE_OAUTH_CLIENT_ID")
        print("  GOOGLE_OAUTH_CLIENT_SECRET")
        print("  GITHUB_OAUTH_CLIENT_ID")
        print("  GITHUB_OAUTH_CLIENT_SECRET")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)