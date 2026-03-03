import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix conflict 1
conflict_1_pattern = r"<<<<<<< ours\nimport google\.generativeai as genai\nfrom dotenv import load_dotenv\n=======\nfrom dotenv import load_dotenv\n\n# Load variables from \.env file into os\.environ\n>>>>>>> theirs"
replacement_1 = "import google.generativeai as genai\nfrom dotenv import load_dotenv\n\n# Load variables from .env file into os.environ"
content = re.sub(conflict_1_pattern, replacement_1, content)

# Fix conflict 2
# We know the start is <<<<<<< ours\n@app.route('/api/dashboard-data')
# And the end is >>>>>>> theirs
# Let's extract what we want to keep
# We keep from @app.route('/api/dashboard-data') up to right before @app.route('/api/chat', methods=['POST']) inside "ours"
# And then we keep the @app.route('/api/chat', methods=['POST']) from "theirs"

conflict_2_pattern = re.compile(r"<<<<<<< ours\n(.*?)(@app\.route\('/api/chat.*?)\n=======\n(.*?)>>>>>>> theirs", re.DOTALL)

def replacer(match):
    dashboard_and_others = match.group(1)
    chat_theirs = match.group(3)
    return dashboard_and_others + chat_theirs

content = re.sub(conflict_2_pattern, replacer, content)

with open('app.py', 'w') as f:
    f.write(content)
print("Done")
