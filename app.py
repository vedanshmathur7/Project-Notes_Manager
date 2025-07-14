from flask import Flask, render_template, redirect, request, session
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
import os
import uuid
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load .env file
load_dotenv("op.env")

app = Flask(__name__)
Scss(app)

# Secret key for sessions (stored in .env)
app.secret_key = os.getenv('SECRET_KEY')

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]  # global default
)

# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
db = SQLAlchemy(app)

# Model
class MyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100))  # Unique session ID per user
    content = db.Column(db.String(100))
    complete = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Task {self.id}"

with app.app_context():
    db.create_all()

# Home
@app.route('/', methods=["POST", "GET"])
@limiter.limit("20 per minute")  # Limit to 5 submissions per minute per IP
def index():
    # Create a unique session_id if not already present
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    # Add a task
    if request.method == "POST":
        current_task = request.form['content']
        new_task = MyTask(content=current_task, session_id=session["session_id"])
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return "An error occurred while adding the task.", 500

    # View tasks for this session
    else:
        tasks = MyTask.query.filter_by(session_id=session["session_id"]).order_by(MyTask.created).all()
        return render_template('index.html', tasks=tasks)

# Delete a task
@app.route('/delete/<int:id>')
@limiter.limit("20 per minute")  # Limit to 5 submissions per minute per IP
def delete(id: int):
    task = MyTask.query.get_or_404(id)
    if task.session_id != session.get("session_id"):
        return "Unauthorized", 403
    try:
        db.session.delete(task)
        db.session.commit()
        return redirect('/')
    except Exception as e:
        return "An error occurred while deleting the task.", 500

# Edit a task
@app.route('/edit/<int:id>', methods=["GET", "POST"])
@limiter.limit("20 per minute")  # Limit to 5 submissions per minute per IP
def edit(id: int):
    task = MyTask.query.get_or_404(id)
    if task.session_id != session.get("session_id"):
        return "Unauthorized", 403
    if request.method == "POST":
        task.content = request.form['content']
        try:
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return "An error occurred while editing the task.", 500
    else:
        return render_template('edit.html', task=task)

if __name__ == '__main__':
    app.run(debug=True)
