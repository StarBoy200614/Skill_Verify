import re

new_data = """# ============= CAREER DATA =============
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
                'skills': ['Python', 'Java', 'Data Structures', 'System Design'],
                'required_skills': ['Python / Java / C++', 'Data Structures & Algorithms', 'System Design', 'Version Control (Git)', 'Cloud Architecture (AWS/Azure)', 'Problem Solving'],
                'ladder': [
                    {'title': 'Trainee Software Engineer', 'desc': 'Learning the ropes, assisting the team, and mastering the fundamentals.', 'icon': 'school'},
                    {'title': 'Junior Software Engineer', 'desc': 'Writing basic code, fixing minor bugs, and learning best practices.', 'icon': 'code'},
                    {'title': 'Software Engineer', 'desc': 'Developing features independently, code reviews, and system design basics.', 'icon': 'developer_mode'},
                    {'title': 'Senior Software Engineer', 'desc': 'Leading the architecture of complex modules and mentoring junior devs.', 'icon': 'architecture'},
                    {'title': 'Lead Software Engineer', 'desc': 'Guiding technical direction, unblocking the team, and ensuring quality.', 'icon': 'groups'},
                    {'title': 'Development Manager', 'desc': 'Managing teams, driving strategy, and optimizing developer productivity.', 'icon': 'psychology'},
                ]
            },
            {
                'title': 'Data Scientist',
                'description': 'Analyze complex data sets to extract valuable insights.',
                'salary': '$135,000',
                'growth': '36% (Much faster than average)',
                'skills': ['Machine Learning', 'Statistics', 'SQL', 'Python'],
                'required_skills': ['Python / R', 'Statistical Analysis', 'Machine Learning Models', 'Data Visualization (Tableau/PowerBI)', 'SQL / Databases', 'Big Data Technologies'],
                'ladder': [
                    {'title': 'Data Analyst', 'desc': 'Querying databases, cleaning data, and generating reports.', 'icon': 'query_stats'},
                    {'title': 'Junior Data Scientist', 'desc': 'Building basic models and performing exploratory data analysis.', 'icon': 'bar_chart'},
                    {'title': 'Data Scientist', 'desc': 'Developing complex machine learning models and predictive analytics.', 'icon': 'insights'},
                    {'title': 'Senior Data Scientist', 'desc': 'Leading data science projects, defining methodologies, and mentoring.', 'icon': 'hub'},
                    {'title': 'Lead Data Scientist', 'desc': 'Driving the data strategy, research, and cross-functional AI integration.', 'icon': 'science'},
                    {'title': 'Chief Data Officer', 'desc': 'Executive leadership over the organization\\'s data and analytics strategy.', 'icon': 'account_balance'},
                ]
            },
            {
                'title': 'Cybersecurity Analyst',
                'description': 'Protect networks and systems from cyber threats.',
                'salary': '$112,000',
                'growth': '32% (Much faster than average)',
                'skills': ['Network Security', 'Cryptography', 'Risk Assessment'],
                'required_skills': ['Network Architecture', 'Security Protocols', 'Penetration Testing', 'Incident Response', 'Cryptography', 'SIEM Tools'],
                'ladder': [
                    {'title': 'Security Technician', 'desc': 'Monitoring systems, managing access controls, and responding to basic alerts.', 'icon': 'security'},
                    {'title': 'Junior Security Analyst', 'desc': 'Conducting vulnerability scans and assisting in incident response.', 'icon': 'policy'},
                    {'title': 'Cybersecurity Analyst', 'desc': 'Analyzing threats, implementing security measures, and handling breaches.', 'icon': 'gpp_bad'},
                    {'title': 'Senior Security Analyst', 'desc': 'Designing secure network architectures and leading incident response.', 'icon': 'shield'},
                    {'title': 'Lead Security Architect', 'desc': 'Defining enterprise security strategy and ensuring compliance.', 'icon': 'castle'},
                    {'title': 'Chief Information Security Officer', 'desc': 'Executive responsibility for the organization\\'s information and data security.', 'icon': 'admin_panel_settings'},
                ]
            }
        ]
    },
    'healthcare': {
        'title': 'Health Care',
        'subtitle': 'Make a difference in people\\'s lives through medicine',
        'careers': [
            {
                'title': 'Registered Nurse',
                'description': 'Provide and coordinate patient care in hospitals and clinics.',
                'salary': '$77,000',
                'growth': '6% (Faster than average)',
                'skills': ['Patient Care', 'Clinical Skills', 'Communication'],
                'required_skills': ['Patient Assessment', 'Medication Administration', 'Medical Terminology', 'Empathy & Care', 'Emergency Response', 'Electronic Health Records'],
                'ladder': [
                    {'title': 'Nursing Assistant/Student RN', 'desc': 'Assisting with basic patient care, taking vitals, and learning clinical workflows.', 'icon': 'favorite'},
                    {'title': 'Staff Registered Nurse', 'desc': 'Providing direct patient care, administering medications, and updating records.', 'icon': 'healing'},
                    {'title': 'Charge Nurse', 'desc': 'Overseeing a shift of nurses, coordinating schedules, and managing crises.', 'icon': 'health_and_safety'},
                    {'title': 'Nurse Manager', 'desc': 'Managing a department, handling budgets, and ensuring quality of care.', 'icon': 'medical_services'},
                    {'title': 'Director of Nursing', 'desc': 'Leading nursing operations across the facility and setting clinical standards.', 'icon': 'local_hospital'},
                    {'title': 'Chief Nursing Officer (CNO)', 'desc': 'Executive leadership of nursing practice and patient care operations.', 'icon': 'workspace_premium'},
                ]
            },
            {
                'title': 'Physician Assistant',
                'description': 'Practice medicine on teams with physicians and other healthcare workers.',
                'salary': '$126,000',
                'growth': '27% (Much faster than average)',
                'skills': ['Diagnosis', 'Treatment', 'Medical History', 'Teamwork'],
                'required_skills': ['Medical Diagnosis', 'Treatment Planning', 'Surgical Assisting', 'Pharmacology', 'Patient Counseling', 'Anatomy/Physiology'],
                'ladder': [
                    {'title': 'PA Student/Pre-PA', 'desc': 'Completing clinical rotations, shadowing, and foundational medical coursework.', 'icon': 'school'},
                    {'title': 'Junior Staff PA', 'desc': 'Assisting physicians, taking histories, and performing routine check-ups.', 'icon': 'stethoscope'},
                    {'title': 'Physician Assistant', 'desc': 'Diagnosing illnesses, developing treatment plans, and prescribing medications independently.', 'icon': 'vaccines'},
                    {'title': 'Senior PA / Specialized PA', 'desc': 'Working in specialized surgical or critical care fields with high autonomy.', 'icon': 'medication'},
                    {'title': 'Lead PA / Chief PA', 'desc': 'Managing teams of PAs, overseeing schedules, and contributing to hospital policy.', 'icon': 'badge'},
                    {'title': 'Clinical Director', 'desc': 'Executive leadership of clinical operations and interdisciplinary medical teams.', 'icon': 'event_available'},
                ]
            },
            {
                'title': 'Physical Therapist',
                'description': 'Help injured or ill people improve their movement and manage pain.',
                'salary': '$97,000',
                'growth': '15% (Much faster than average)',
                'skills': ['Rehabilitation', 'Anatomy', 'Treatment Planning'],
                'required_skills': ['Biomechanics', 'Exercise Therapy', 'Manual Therapy Techniques', 'Patient Assessment', 'Pain Management', 'Documentation'],
                'ladder': [
                    {'title': 'PT Student / Aide', 'desc': 'Assisting in setting up equipment and observing therapeutic sessions.', 'icon': 'fitness_center'},
                    {'title': 'Staff Physical Therapist', 'desc': 'Evaluating patients and implementing basic rehabilitation plans.', 'icon': 'elderly'},
                    {'title': 'Senior Physical Therapist', 'desc': 'Handling complex cases, mentoring staff, and specializing (e.g., ortho, neuro).', 'icon': 'assist_walker'},
                    {'title': 'Clinical Coordinator', 'desc': 'Managing clinic schedules, supervising PT assistants, and ensuring protocol adherence.', 'icon': 'calendar_today'},
                    {'title': 'Clinic Director', 'desc': 'Running the business and clinical operations of a therapy center.', 'icon': 'storefront'},
                    {'title': 'Rehab Services Director', 'desc': 'Overseeing physical, occupational, and speech therapy programs at an organizational level.', 'icon': 'corporate_fare'},
                ]
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
                'skills': ['Design', 'CAD', 'Creativity', 'Technical Knowledge'],
                'required_skills': ['AutoCAD/Revit', '3D Modeling', 'Building Codes', 'Structural Design', 'Client Communication', 'Project Management'],
                'ladder': [
                    {'title': 'Architectural Intern', 'desc': 'Drafting basic plans, building models, and assisting with project documentation.', 'icon': 'straighten'},
                    {'title': 'Junior Architect', 'desc': 'Developing designs, preparing presentations, and coordinating with engineers.', 'icon': 'edit'},
                    {'title': 'Project Architect', 'desc': 'Leading the design, ensuring code compliance, and managing the drafting team.', 'icon': 'architecture'},
                    {'title': 'Senior Architect', 'desc': 'Managing large-scale projects, client relations, and complex architectural challenges.', 'icon': 'location_city'},
                    {'title': 'Design Director', 'desc': 'Leading the creative vision for the firm and winning new business.', 'icon': 'palette'},
                    {'title': 'Principal/Partner', 'desc': 'Executive leadership, owning the business strategy, and leading the firm.', 'icon': 'real_estate_agent'},
                ]
            },
            {
                'title': 'Civil Engineer',
                'description': 'Design, build, and supervise infrastructure projects and systems.',
                'salary': '$89,000',
                'growth': '5% (As fast as average)',
                'skills': ['Engineering Principles', 'Project Management', 'Problem Solving'],
                'required_skills': ['AutoCAD Civil 3D', 'Structural Analysis', 'Geotechnical Knowledge', 'Math/Physics', 'Construction Management', 'Environmental Regulations'],
                'ladder': [
                    {'title': 'Engineering Technician', 'desc': 'Conducting surveys, taking soil samples, and assisting in drawing preparations.', 'icon': 'terrain'},
                    {'title': 'Junior Civil Engineer (EIT)', 'desc': 'Assisting in design calculations, cost estimates, and site inspections.', 'icon': 'engineering'},
                    {'title': 'Civil Engineer (PE)', 'desc': 'Designing infrastructure, signing off on plans, and managing subcontractors.', 'icon': 'construction'},
                    {'title': 'Senior Civil Engineer', 'desc': 'Leading massive public works projects, from bridges to highway systems.', 'icon': 'emoji_transportation'},
                    {'title': 'Engineering Manager', 'desc': 'Overseeing multiple engineering teams, budgets, and municipal contracts.', 'icon': 'domain'},
                    {'title': 'Chief Engineer / Director', 'desc': 'Executive responsibility for regional or departmental engineering operations.', 'icon': 'account_balance'},
                ]
            },
            {
                'title': 'Urban Planner',
                'description': 'Develop land use plans and programs that help create communities.',
                'salary': '$79,000',
                'growth': '4% (As fast as average)',
                'skills': ['Analysis', 'Communication', 'GIS', 'Planning Law'],
                'required_skills': ['GIS Mapping', 'Urban Policy', 'Zoning Laws', 'Public Speaking', 'Environmental Science', 'Statistical Analysis'],
                'ladder': [
                    {'title': 'Planning Assistant', 'desc': 'Gathering data, preparing public notices, and mapping zoning areas.', 'icon': 'map'},
                    {'title': 'Junior Planner', 'desc': 'Reviewing site plans, conducting community surveys, and writing reports.', 'icon': 'description'},
                    {'title': 'Urban Planner', 'desc': 'Developing community plans, presenting to city councils, and managing grant projects.', 'icon': 'nature_people'},
                    {'title': 'Senior Planner', 'desc': 'Leading major city redevelopment projects and revising comprehensive city plans.', 'icon': 'location_on'},
                    {'title': 'Principal Planner', 'desc': 'Advising mayors and councils, handling high-profile policy implementations.', 'icon': 'public'},
                    {'title': 'Director of City Planning', 'desc': 'Executive oversight of a city\\'s entire planning, zoning, and development department.', 'icon': 'account_balance'},
                ]
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
                'skills': ['Research', 'Analysis', 'Writing', 'Public Policy'],
                'required_skills': ['Statistical Analysis', 'Policy Evaluation', 'Research Writing', 'Economics Background', 'Public Speaking', 'Data Modeling'],
                'ladder': [
                    {'title': 'Research Assistant', 'desc': 'Collecting data, reviewing literature, and preparing policy summaries.', 'icon': 'search'},
                    {'title': 'Junior Policy Analyst', 'desc': 'Drafting policy briefs, monitoring legislation, and assisting in evaluations.', 'icon': 'article'},
                    {'title': 'Policy Analyst', 'desc': 'Evaluating policy impacts, testifying in hearings, and publishing reports.', 'icon': 'assessment'},
                    {'title': 'Senior Policy Analyst', 'desc': 'Leading major research initiatives and advising lawmakers directly.', 'icon': 'psychology'},
                    {'title': 'Director of Policy', 'desc': 'Managing a team of analysts and setting the research agenda for a think tank or agency.', 'icon': 'groups'},
                    {'title': 'Chief Policy Officer', 'desc': 'Executive leadership shaping the organization\\'s public policy strategy.', 'icon': 'gavel'},
                ]
            },
            {
                'title': 'Legislative Assistant',
                'description': 'Support legislators in drafting and analyzing legislation.',
                'salary': '$58,000',
                'growth': '5% (As fast as average)',
                'skills': ['Research', 'Communication', 'Legislative Process'],
                'required_skills': ['Constituent Relations', 'Legal Research', 'Speech Writing', 'Negotiation', 'Event Coordination', 'Government Structure Knowledge'],
                'ladder': [
                    {'title': 'Legislative Intern', 'desc': 'Answering phones, sorting mail, and assisting constituents with basic issues.', 'icon': 'mail'},
                    {'title': 'Staff Assistant', 'desc': 'Managing schedules, drafting standard correspondence, and coordinating office logistics.', 'icon': 'calendar_month'},
                    {'title': 'Legislative Assistant', 'desc': 'Briefing the representative, drafting legislation, and tracking specific issue areas.', 'icon': 'gavel'},
                    {'title': 'Senior Legislative Assistant', 'desc': 'Handling complex committees, negotiating with other offices, and leading projects.', 'icon': 'handshake'},
                    {'title': 'Legislative Director', 'desc': 'Overseeing the entire legislative agenda and managing the legislative staff.', 'icon': 'account_tree'},
                    {'title': 'Chief of Staff', 'desc': 'Running the elected official\\'s operations, political strategy, and office management.', 'icon': 'stars'},
                ]
            },
            {
                'title': 'Public Relations Specialist',
                'description': 'Create and maintain a positive public image for organizations.',
                'salary': '$67,000',
                'growth': '6% (Faster than average)',
                'skills': ['Communication', 'Media Relations', 'Writing'],
                'required_skills': ['Copywriting', 'Crisis Management', 'Social Media Strategy', 'Press Release Creation', 'Media Pitching', 'Public Speaking'],
                'ladder': [
                    {'title': 'PR Coordinator', 'desc': 'Building media lists, tracking press coverage, and drafting social media posts.', 'icon': 'list_alt'},
                    {'title': 'Junior PR Specialist', 'desc': 'Drafting press releases, pitching to local media, and organizing events.', 'icon': 'campaign'},
                    {'title': 'Public Relations Specialist', 'desc': 'Managing media relationships, developing campaign strategies, and acting as a spokesperson.', 'icon': 'record_voice_over'},
                    {'title': 'PR Manager', 'desc': 'Overseeing complete PR campaigns, crisis communication, and brand messaging.', 'icon': 'manage_accounts'},
                    {'title': 'Director of Public Relations', 'desc': 'Leading the PR department, setting long-term communication strategies.', 'icon': 'lan'},
                    {'title': 'Chief Comm Officer', 'desc': 'Executive leadership over all internal and external corporate communications.', 'icon': 'supervisor_account'},
                ]
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
                'skills': ['Leadership', 'Logistics', 'Strategic Planning'],
                'required_skills': ['Team Leadership', 'Process Optimization', 'Budget Management', 'Supply Chain Knowledge', 'Risk Management', 'Conflict Resolution'],
                'ladder': [
                    {'title': 'Operations Coordinator', 'desc': 'Tracking schedules, inventory, and supporting day-to-day operations.', 'icon': 'event_note'},
                    {'title': 'Operations Supervisor', 'desc': 'Supervising a shift or unit, ensuring safety protocols and efficiency.', 'icon': 'badge'},
                    {'title': 'Operations Manager', 'desc': 'Managing facility operations, optimizing processes, and reducing costs.', 'icon': 'settings_applications'},
                    {'title': 'Senior Operations Manager', 'desc': 'Overseeing multiple facilities or complex cross-functional teams.', 'icon': 'hub'},
                    {'title': 'Director of Operations', 'desc': 'Setting operational strategy and working with other department heads.', 'icon': 'corporate_fare'},
                    {'title': 'Chief Operating Officer (COO)', 'desc': 'Executive responsibility for the daily operation of the entire company.', 'icon': 'business_center'},
                ]
            },
            {
                'title': 'Logistics Coordinator',
                'description': 'Oversee the supply chain and movement of goods.',
                'salary': '$77,000',
                'growth': '18% (Much faster than average)',
                'skills': ['Supply Chain', 'Coordination', 'Problem Solving'],
                'required_skills': ['Inventory Control', 'Freight Management', 'Route Optimization', 'Vendor Negotiation', 'ERP Software', 'Data Analysis'],
                'ladder': [
                    {'title': 'Logistics Clerk', 'desc': 'Entering shipping data, tracking packages, and communicating with carriers.', 'icon': 'inventory_2'},
                    {'title': 'Junior Logistics Coordinator', 'desc': 'Planning shipments, solving delivery delays, and optimizing small routes.', 'icon': 'local_shipping'},
                    {'title': 'Logistics Coordinator', 'desc': 'Managing major supply chain accounts, negotiating rates, and maintaining inventory.', 'icon': 'trolley'},
                    {'title': 'Logistics Manager', 'desc': 'Overseeing regional supply chains, warehousing, and transportation strategy.', 'icon': 'warehouse'},
                    {'title': 'Director of Supply Chain', 'desc': 'Leading global supply operations and long-term procurement strategies.', 'icon': 'public'},
                    {'title': 'VP of Supply Chain', 'desc': 'Executive leadership ensuring the company supply chain remains resilient and profitable.', 'icon': 'verified'},
                ]
            },
            {
                'title': 'Security Consultant',
                'description': 'Assess and improve an organization’s security measures.',
                'salary': '$95,000',
                'growth': '8% (Faster than average)',
                'skills': ['Risk Assessment', 'Security Procedures', 'Surveillance'],
                'required_skills': ['Physical Security Planning', 'Threat Assessment', 'Emergency Protocol Design', 'Access Control Systems', 'Investigation', 'Compliance Law'],
                'ladder': [
                    {'title': 'Security Guard/Officer', 'desc': 'Monitoring premises, controlling access, and reporting suspicious activity.', 'icon': 'shield'},
                    {'title': 'Security Supervisor', 'desc': 'Managing a team of guards, scheduling, and leading incident response.', 'icon': 'admin_panel_settings'},
                    {'title': 'Security Consultant', 'desc': 'Auditing client facilities, designing security systems, and conducting risk assessments.', 'icon': 'gpp_good'},
                    {'title': 'Senior Security Consultant', 'desc': 'Handling high-risk corporate clients and designing complex emergency plans.', 'icon': 'health_and_safety'},
                    {'title': 'Director of Security', 'desc': 'Overseeing the security posture for an entire corporation or organization.', 'icon': 'apartment'},
                    {'title': 'Chief Security Officer (CSO)', 'desc': 'Executive in charge of all physical and environmental security for the enterprise.', 'icon': 'verified_user'},
                ]
            }
        ]
    }
}
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
pattern = re.compile(r'# ============= CAREER DATA =============\nCAREER_DATA = \{.*?\n}\n', re.DOTALL)
new_content = pattern.sub(new_data + "\n", content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("App data updated.")
