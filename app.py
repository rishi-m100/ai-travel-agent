from flask import Flask, request, jsonify, render_template
import json
import sys
from pathlib import Path

# Add the root directory to path so we can import from agent
sys.path.append(str(Path(__file__).parent))

from agent.agent import run_agent
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("prompt", "")
    
    if not user_message:
        return jsonify({"error": "Prompt cannot be empty"}), 400
        
    try:
        # call the agent — run_agent returns a JSON string,
        # so parse it to avoid double-encoding in jsonify
        result = run_agent(user_message, verbose=True)
        try:
            parsed = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            parsed = {"result": result}
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
