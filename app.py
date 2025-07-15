from flask import Flask, render_template, redirect, request, make_response
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid

# Initialize Flask app
app = Flask(__name__)
Scss(app)

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"]  # global default
)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Define the model
class MyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))  # Unique user ID per device via cookie
    content = db.Column(db.String(100))
    complete = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Task {self.id}"

# Create database tables
with app.app_context():
    db.create_all()

# Home route
@app.route('/', methods=["POST", "GET"])
@limiter.limit("20 per minute")
def index():
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())

    if request.method == "POST":
        content = request.form['content'].strip()
        if not content:
            return "Task content cannot be empty.", 400
        new_task = MyTask(content=content, user_id=user_id)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return "An error occurred while adding the task.", 500

    tasks = MyTask.query.filter_by(user_id=user_id).order_by(MyTask.created).all()
    resp = make_response(render_template('index.html', tasks=tasks))
    resp.set_cookie('user_id', user_id)
    return resp

# Delete route
@app.route('/delete/<int:id>')
@limiter.limit("20 per minute")
def delete(id):
    user_id = request.cookies.get("user_id")
    task = MyTask.query.get_or_404(id)
    if task.user_id != user_id:
        return "Unauthorized", 403
    try:
        db.session.delete(task)
        db.session.commit()
        return redirect('/')
    except Exception as e:
        return "An error occurred while deleting the task.", 500

# Edit route
@app.route('/edit/<int:id>', methods=["GET", "POST"])
@limiter.limit("20 per minute")
def edit(id):
    user_id = request.cookies.get("user_id")
    task = MyTask.query.get_or_404(id)
    if task.user_id != user_id:
        return "Unauthorized", 403
    if request.method == "POST":
        task.content = request.form['content'].strip()
        if not task.content:
            return "Task content cannot be empty.", 400
        try:
            db.session.commit()
            return redirect('/')
        except Exception as e:
            return "An error occurred while editing the task.", 500
    else:
        return render_template('edit.html', task=task)

if __name__ == '__main__':
    app.run(debug=True)
