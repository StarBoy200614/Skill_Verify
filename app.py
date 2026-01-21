from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from datetime import datetime, timedelta
import os
import google.generativeai as genai

# Configure Gemini API
# In production, use: os.getenv('GEMINI_API_KEY')
# Using the key provided by the user for this session
GEMINI_API_KEY = "AIzaSyAk0Rxl3-e96BTkdAN1xkhauPjVoGqs5Rg"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillverify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)

# ============= DATABASE MODELS =============

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    survey_responses = db.relationship('SurveyResponse', backref='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_readiness = db.Column(db.Integer, default=0)
    verified_skills = db.Column(db.Integer, default=0)
    total_xp = db.Column(db.Integer, default=0)
    certifications = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'skill_readiness': self.skill_readiness,
            'verified_skills': self.verified_skills,
            'total_xp': self.total_xp,
            'certifications': self.certifications
        }


class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_1 = db.Column(db.String(50))
    question_2 = db.Column(db.String(50))
    question_3 = db.Column(db.String(50))
    question_4 = db.Column(db.String(50))
    question_5 = db.Column(db.String(50))
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question_1': self.question_1,
            'question_2': self.question_2,
            'question_3': self.question_3,
            'question_4': self.question_4,
            'question_5': self.question_5,
            'completed_at': self.completed_at.isoformat()
        }


class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(100))
    domain = db.Column(db.String(100))
    difficulty = db.Column(db.String(50))
    deadline = db.Column(db.String(50))
    status = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'domain': self.domain,
            'difficulty': self.difficulty,
            'deadline': self.deadline,
            'status': self.status
        }


# ============= MAIN ROUTES =============

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/organizations')
def organizations():
    """Organizations page"""
    return render_template('organizations.html')


@app.route('/careers/cs')
def careers_cs():
    """Computer Science Careers page"""
    return render_template('careers_new.html')

@app.route('/careers/habitation')
def careers_habitation():
    """Habitation Careers page"""
    return render_template('careers_habitation.html')

@app.route('/careers/polsci')
def careers_polsci():
    """Political Science Careers page"""
    return render_template('careers_polsci.html')



# ============= CAREER DATA =============
CAREER_DATA = {
    'cs': {
        'title': 'Computer Science',
        'subtitle': 'Design and build the future of technology',
        'careers': [
            {
                'title': 'Software Engineer',
                'description': 'Build and maintain software systems. High demand and growth potential.',
                'salary': '$120,000',
                'growth': '22% (Much faster than average)',
                'skills': ['Python', 'Java', 'System Design', 'Algorithms']
            },
            {
                'title': 'Data Scientist',
                'description': 'Analyze complex data to help make business decisions.',
                'salary': '$135,000',
                'growth': '36% (Much faster than average)',
                'skills': ['Machine Learning', 'Statistics', 'SQL', 'Python']
            },
            {
                'title': 'Cybersecurity Analyst',
                'description': 'Protect computer networks and systems from cyber threats.',
                'salary': '$112,000',
                'growth': '32% (Much faster than average)',
                'skills': ['Network Security', 'Ethical Hacking', 'Risk Analysis']
            }
        ]
    },
    'health': {
        'title': 'Health Care',
        'subtitle': 'Save lives and improve patient well-being',
        'careers': [
            {
                'title': 'Registered Nurse',
                'description': 'Provide and coordinate patient care, educate patients about health conditions.',
                'salary': '$81,000',
                'growth': '6% (Faster than average)',
                'skills': ['Patient Care', 'Medical Knowledge', 'Empathy', 'Communication']
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
    
    if category == 'cs':
        return redirect(url_for('careers_cs'))
    
    if category == 'habitation':
        return redirect(url_for('careers_habitation'))
        
    if category == 'polsci':
        return redirect(url_for('careers_polsci'))

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

@app.route('/community')
def community():
    """Community page"""
    return render_template('community.html')


@app.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


@app.route('/about')
def about():
    """About Us page"""
    return render_template('About_US.html')


@app.route('/register-page')
def register_page():
    """Simple registration page"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Register - SkillVerify</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 50px;
                border-radius: 24px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 450px;
                width: 100%;
            }
            h1 {
                font-size: 32px;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p { color: #666; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label {
                display: block;
                color: #333;
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 14px;
            }
            input {
                width: 100%;
                padding: 14px;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                font-size: 15px;
                transition: all 0.3s ease;
            }
            input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            button {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            }
            .link {
                text-align: center;
                margin-top: 20px;
                color: #666;
            }
            .link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .message {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }
            .success {
                background: #d4f4dd;
                color: #22863a;
                display: block;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Create Account</h1>
            <p>Join SkillVerify to start your journey</p>
            
            <div id="message" class="message"></div>
            
            <form id="registerForm">
                <div class="form-group">
                    <label>Full Name</label>
                    <input type="text" id="name" placeholder="Enter your name" required>
                </div>
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" id="email" placeholder="Enter your email" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" placeholder="Create a password" required>
                </div>
                <button type="submit" id="submitBtn">Create Account</button>
            </form>
            
            <div class="link">
                Already have an account? <a href="/">Sign In</a>
            </div>
        </div>

        <script>
            document.getElementById('registerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const submitBtn = document.getElementById('submitBtn');
                const message = document.getElementById('message');
                
                submitBtn.textContent = 'Creating Account...';
                submitBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/register', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            name: document.getElementById('name').value,
                            email: document.getElementById('email').value,
                            password: document.getElementById('password').value
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        message.className = 'message success';
                        message.textContent = 'Account created successfully! Redirecting...';
                        setTimeout(() => window.location.href = '/', 2000);
                    } else {
                        message.className = 'message error';
                        message.textContent = data.message;
                        submitBtn.textContent = 'Create Account';
                        submitBtn.disabled = false;
                    }
                } catch (error) {
                    message.className = 'message error';
                    message.textContent = 'An error occurred. Please try again.';
                    submitBtn.textContent = 'Create Account';
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    '''


# ============= API ROUTES =============

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
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
    
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    remember_me = data.get('rememberMe', False)
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
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


@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get dashboard data for logged-in user"""
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
            'challenges': [c.to_dict() for c in Challenge.query.all()]
        }), 200
    
    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    challenges = Challenge.query.all()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'stats': profile.to_dict() if profile else {},
        'challenges': [c.to_dict() for c in challenges]
    }), 200


@app.route('/api/submit-survey', methods=['POST'])
def submit_survey():
    """Submit career test survey"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to submit survey'}), 401
    
    data = request.get_json()
    
    survey = SurveyResponse(
        user_id=user_id,
        question_1=data.get('1'),
        question_2=data.get('2'),
        question_3=data.get('3'),
        question_4=data.get('4'),
        question_5=data.get('5')
    )
    db.session.add(survey)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Survey submitted successfully',
        'survey': survey.to_dict()
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
def chat():
    """Chat with Gemini AI"""
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
        
    try:
        # Construct a system prompt to give context to the AI
        system_context = """
        You are the AI assistant for SkillVerify, a career advancement platform.
        Your goal is to help students and professionals discover their ideal career path, verify skills, and find real-world challenges.
        
        Key features of SkillVerify:
        1. Career Assessment: A 5-minute test to match interests and skills to careers.
        2. Skill Verification: Earn badges by completing challenges.
        3. Real Challenges: Practical projects from top companies.
        
        Career Paths offered: Computer Science, Health Care, Habitation, Political Science, Veteran Careers.
        
        User context: The user is asking a question about the site or career advice.
        Answer concisely and helpfully. If you don't know the answer, suggest they contact support or check the 'More' section.
        """
        
        full_prompt = f"{system_context}\n\nUser: {user_message}\nAI:"
        
        response = model.generate_content(full_prompt)
        ai_reply = response.text
        
        return jsonify({
            'success': True,
            'message': ai_reply
        }), 200
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return jsonify({
            'success': False, 
            'message': f"Error: {str(e)}" 
        }), 500


# ============= ADMIN ROUTES =============

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard HTML page"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - SkillVerify</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            font-size: 32px;
            color: #1a1a1a;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 16px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-box {
            background: white;
            padding: 25px;
            border-radius: 16px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }

        .stat-box:hover {
            transform: translateY(-5px);
        }

        .stat-number {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .stat-label {
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .tab {
            padding: 12px 24px;
            background: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            color: #666;
        }

        .tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .tab:hover:not(.active) {
            background: #f0f0f0;
        }

        .content-box {
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            overflow-x: auto;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            min-width: 800px;
        }

        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }

        tbody tr {
            transition: background 0.3s ease;
        }

        tbody tr:hover {
            background: #f8f9ff;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        .badge-success {
            background: #d4f4dd;
            color: #22863a;
        }

        .badge-info {
            background: #d1ecf1;
            color: #0c5460;
        }

        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }

        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-right: 5px;
            font-size: 13px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn-danger {
            background: #ef4444;
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .search-box {
            width: 100%;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            margin-bottom: 20px;
            transition: border-color 0.3s ease;
        }

        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }

        .loading {
            text-align: center;
            padding: 40px;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
        }

        .refresh-btn:hover {
            transform: scale(1.1) rotate(90deg);
        }

        .back-btn {
            display: inline-block;
            padding: 10px 20px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }

        .back-btn:hover {
            background: #f0f0f0;
            transform: translateX(-5px);
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Dashboard</a>
        
        <div class="header">
            <h1>🔧 Admin Dashboard</h1>
            <p>Manage users, view statistics, and monitor system activity</p>
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number" id="totalUsers">0</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="totalSurveys">0</div>
                <div class="stat-label">Surveys Completed</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="totalChallenges">0</div>
                <div class="stat-label">Active Challenges</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="avgSkill">0%</div>
                <div class="stat-label">Avg Skill Readiness</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('users')">👥 Users</button>
            <button class="tab" onclick="switchTab('surveys')">📋 Surveys</button>
            <button class="tab" onclick="switchTab('challenges')">🎯 Challenges</button>
        </div>

        <div class="content-box">
            <div class="tab-content active" id="users-tab">
                <input type="text" class="search-box" id="searchUsers" placeholder="🔍 Search users by email or name...">
                <div id="usersContent">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading users...</p>
                    </div>
                </div>
            </div>

            <div class="tab-content" id="surveys-tab">
                <input type="text" class="search-box" id="searchSurveys" placeholder="🔍 Search surveys...">
                <div id="surveysContent">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading surveys...</p>
                    </div>
                </div>
            </div>

            <div class="tab-content" id="challenges-tab">
                <div id="challengesContent">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading challenges...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadAllData()" title="Refresh Data">↻</button>

    <script>
        let allUsers = [];
        let allSurveys = [];
        let allChallenges = [];

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        }

        async function loadAllData() {
            await Promise.all([
                loadUsers(),
                loadSurveys(),
                loadChallenges(),
                loadStats()
            ]);
        }

        async function loadUsers() {
            try {
                const response = await fetch('/api/admin/users');
                const data = await response.json();
                allUsers = data.users || [];
                displayUsers(allUsers);
            } catch (error) {
                console.error('Error loading users:', error);
                document.getElementById('usersContent').innerHTML = '<div class="empty-state">Error loading users</div>';
            }
        }

        function displayUsers(users) {
            const content = document.getElementById('usersContent');
            
            if (users.length === 0) {
                content.innerHTML = '<div class="empty-state"><p>No users found. <a href="/register-page">Register a user</a></p></div>';
                return;
            }

            let html = '<table><thead><tr><th>ID</th><th>Email</th><th>Name</th><th>Skill Readiness</th><th>Verified Skills</th><th>Total XP</th><th>Joined</th><th>Actions</th></tr></thead><tbody>';

            users.forEach(user => {
                const profile = user.profile || {};
                const date = new Date(user.created_at).toLocaleDateString();
                
                html += `
                    <tr>
                        <td><span class="badge badge-info">#${user.id}</span></td>
                        <td>${user.email}</td>
                        <td>${user.name || 'N/A'}</td>
                        <td><span class="badge badge-success">${profile.skill_readiness || 0}%</span></td>
                        <td>${profile.verified_skills || 0}</td>
                        <td>${profile.total_xp || 0}</td>
                        <td>${date}</td>
                        <td>
                            <button class="btn btn-primary" onclick="viewUserDetails(${user.id})">View</button>
                            <button class="btn btn-danger" onclick="deleteUser(${user.id})">Delete</button>
                        </td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            content.innerHTML = html;
        }

        async function loadSurveys() {
            try {
                const response = await fetch('/api/admin/surveys');
                const data = await response.json();
                allSurveys = data.surveys || [];
                displaySurveys(allSurveys);
            } catch (error) {
                console.error('Error loading surveys:', error);
                document.getElementById('surveysContent').innerHTML = '<div class="empty-state">Error loading surveys</div>';
            }
        }

        function displaySurveys(surveys) {
            const content = document.getElementById('surveysContent');
            
            if (surveys.length === 0) {
                content.innerHTML = '<div class="empty-state"><p>No surveys completed yet</p></div>';
                return;
            }

            let html = '<table><thead><tr><th>ID</th><th>User Email</th><th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th><th>Q5</th><th>Completed</th></tr></thead><tbody>';

            surveys.forEach(survey => {
                const date = new Date(survey.completed_at).toLocaleDateString();
                
                html += `
                    <tr>
                        <td><span class="badge badge-info">#${survey.id}</span></td>
                        <td>${survey.user_email || 'Unknown'}</td>
                        <td>${survey.question_1 || 'N/A'}</td>
                        <td>${survey.question_2 || 'N/A'}</td>
                        <td>${survey.question_3 || 'N/A'}</td>
                        <td>${survey.question_4 || 'N/A'}</td>
                        <td>${survey.question_5 || 'N/A'}</td>
                        <td>${date}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            content.innerHTML = html;
        }

        async function loadChallenges() {
            try {
                const response = await fetch('/api/admin/challenges');
                const data = await response.json();
                allChallenges = data.challenges || [];
                displayChallenges(allChallenges);
            } catch (error) {
                console.error('Error loading challenges:', error);
                document.getElementById('challengesContent').innerHTML = '<div class="empty-state">Error loading challenges</div>';
            }
        }

        function displayChallenges(challenges) {
            const content = document.getElementById('challengesContent');
            
            if (challenges.length === 0) {
                content.innerHTML = '<div class="empty-state"><p>No challenges available</p></div>';
                return;
            }

            let html = '<table><thead><tr><th>ID</th><th>Title</th><th>Company</th><th>Domain</th><th>Difficulty</th><th>Deadline</th><th>Status</th></tr></thead><tbody>';

            challenges.forEach(challenge => {
                let difficultyClass = 'badge-info';
                if (challenge.difficulty === 'Easy') difficultyClass = 'badge-success';
                if (challenge.difficulty === 'Hard') difficultyClass = 'badge-warning';
                
                html += `
                    <tr>
                        <td><span class="badge badge-info">#${challenge.id}</span></td>
                        <td>${challenge.title}</td>
                        <td>${challenge.company}</td>
                        <td>${challenge.domain}</td>
                        <td><span class="badge ${difficultyClass}">${challenge.difficulty}</span></td>
                        <td>${challenge.deadline}</td>
                        <td>${challenge.status}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            content.innerHTML = html;
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/admin/stats');
                const data = await response.json();
                
                document.getElementById('totalUsers').textContent = data.total_users || 0;
                document.getElementById('totalSurveys').textContent = data.total_surveys || 0;
                document.getElementById('totalChallenges').textContent = data.total_challenges || 0;
                document.getElementById('avgSkill').textContent = (data.avg_skill_readiness || 0) + '%';
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        function viewUserDetails(userId) {
            const user = allUsers.find(u => u.id === userId);
            if (!user) return;
            
            alert(`User Details:\\n\\nEmail: ${user.email}\\nName: ${user.name || 'N/A'}\\nID: ${user.id}\\nJoined: ${new Date(user.created_at).toLocaleDateString()}`);
        }

        async function deleteUser(userId) {
            if (!confirm('Are you sure you want to delete this user?')) return;
            
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    alert('User deleted successfully');
                    loadAllData();
                } else {
                    alert('Error deleting user: ' + data.message);
                }
            } catch (error) {
                console.error('Error deleting user:', error);
                alert('Error deleting user');
            }
        }

        document.getElementById('searchUsers').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = allUsers.filter(u => 
                u.email.toLowerCase().includes(query) || 
                (u.name && u.name.toLowerCase().includes(query))
            );
            displayUsers(filtered);
        });

        document.getElementById('searchSurveys').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = allSurveys.filter(s => 
                (s.user_email && s.user_email.toLowerCase().includes(query)) ||
                Object.values(s).some(v => String(v).toLowerCase().includes(query))
            );
            displaySurveys(filtered);
        });

        loadAllData();
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
    '''


@app.route('/api/admin/users')
def admin_get_users():
    """Get all users with profiles"""
    users = User.query.all()
    users_data = []
    
    for user in users:
        user_dict = user.to_dict()
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        user_dict['profile'] = profile.to_dict() if profile else {}
        users_data.append(user_dict)
    
    return jsonify({'success': True, 'users': users_data}), 200


@app.route('/api/admin/surveys')
def admin_get_surveys():
    """Get all survey responses"""
    surveys = SurveyResponse.query.all()
    surveys_data = []
    
    for survey in surveys:
        survey_dict = survey.to_dict()
        user = User.query.get(survey.user_id)
        survey_dict['user_email'] = user.email if user else 'Unknown'
        surveys_data.append(survey_dict)
    
    return jsonify({'success': True, 'surveys': surveys_data}), 200


@app.route('/api/admin/challenges')
def admin_get_challenges():
    """Get all challenges"""
    challenges = Challenge.query.all()
    return jsonify({
        'success': True,
        'challenges': [c.to_dict() for c in challenges]
    }), 200


@app.route('/api/admin/stats')
def admin_get_stats():
    """Get overall statistics"""
    total_users = User.query.count()
    total_surveys = SurveyResponse.query.count()
    total_challenges = Challenge.query.count()
    
    profiles = UserProfile.query.all()
    avg_skill = sum(p.skill_readiness for p in profiles) / len(profiles) if profiles else 0
    
    return jsonify({
        'success': True,
        'total_users': total_users,
        'total_surveys': total_surveys,
        'total_challenges': total_challenges,
        'avg_skill_readiness': round(avg_skill, 1)
    }), 200


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    """Delete a user"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'}), 200


# ============= INITIALIZATION =============

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created!")
        
        # Add sample challenges if none exist
        if Challenge.query.count() == 0:
            challenges = [
                Challenge(
                    title='Full-Stack Web Development Challenge',
                    company='TechCorp Inc.',
                    domain='Web Development',
                    difficulty='Medium',
                    deadline='Jan 25, 2026',
                    status='Continue Challenge'
                ),
                Challenge(
                    title='Data Science & ML Pipeline',
                    company='DataMinds AI',
                    domain='Machine Learning',
                    difficulty='Hard',
                    deadline='Feb 1, 2026',
                    status='Start Challenge'
                ),
                Challenge(
                    title='React Component Library Design',
                    company='DesignHub',
                    domain='Frontend Development',
                    difficulty='Easy',
                    deadline='Jan 30, 2026',
                    status='View Details'
                )
            ]
            db.session.add_all(challenges)
            db.session.commit()
            print("✅ Sample challenges added!")
        
        print("\n🚀 Server is ready!")
        print("📍 Main Dashboard: http://127.0.0.1:5000")
        print("📍 Registration: http://127.0.0.1:5000/register-page")
        print("📍 Admin Panel: http://127.0.0.1:5000/admin")
        print("\n")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)