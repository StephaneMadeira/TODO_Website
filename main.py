from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, abort
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import relationship, declarative_base
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Environment Variables
load_dotenv("D:\Python\EnvironmentVariables\.env.txt")

# ------------- Setup Flask app -----------------------------#
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("Flask_KEY")


# ------------- Connect to Database -------------------------#
# rest of connection code using the connection string `uri`
if os.environ.get('DATABASE_URL') is None:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
else:
    uri = os.environ.get('DATABASE_URL')
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Deal with the login and sessions
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # *******Add parent relationship******* #
    # This will act like a List of Tasks objects attached to each User.
    # The "owner" refers to the owner property in the Tasks class.
    tasks = relationship("Task", back_populates="owner")

    # Optional: this will allow each task object to be identified by its name when printed.
    def __repr__(self):
        return f'<User {self.name}>'

class Task(db.Model):
    __tablename__ = "Tasks"
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "tasks" refers to the tasks property in the User class.
    owner = relationship("User", back_populates="tasks")

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(250), nullable = False, unique = True)
    category = db.Column(db.String(6), nullable = False, default = "To Do")

    # Optional: this will allow each task object to be identified by its name when printed.
    def __repr__(self):
        return f'<Task {self.name}>'


# Just use when creating the tables
# db.create_all()


@app.route('/')
def home():
    # Pull all tasks from the database
    all_tasks = Task.query.order_by(Task.owner_id).all()
    db.session.commit()
    return render_template("index.html", current_user=current_user, tasks = all_tasks)


@app.route("/add", methods=["GET", "POST"])
# Using POST to add a new task to the database
def add_task():
    if request.method == 'POST':
        task_name = request.form['task']
        new_task = Task(name=task_name,
                        owner_id = current_user.id
                        )
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/update/<int:task_id>", methods=["GET", "POST"])
# Using POST to update the state of the task to the database
def update_task(task_id):
    task_to_update = Task.query.filter_by(id=task_id).first()
    if task_to_update.category == "To Do":
        task_to_update.category = "DOING"
        db.session.commit()
    else:
        task_to_update.category = "DONE"
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/delete/<int:task_id>")
# Delete a task from the database
def delete_task(task_id):
    task_to_delete = Task.query.get(task_id)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/register", methods=["GET", "POST"])
def register():
    # Register a new user, using POST to add the user to the database
    if request.method == 'POST':
        # If user's email already exists
        if User.query.filter_by(email=request.form['register-email']).first():
            # Send flash message
            flash("You've already signed up with that email, log in instead!", category='error')
        else:
            # Use hash and salt to better security
            hash_and_salted_password = generate_password_hash(
                password=request.form['register-password'],
                method='pbkdf2:sha256',
                salt_length=8
            )
            new_user = User(
                email=request.form['register-email'],
                password=hash_and_salted_password,
                name=request.form['register-name'],
            )
            db.session.add(new_user)
            db.session.commit()

            # This line will authenticate the user with Flask-Login
            login_user(new_user)
            return redirect(url_for("home"))
    return render_template("register.html", current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
# Using POST to check the user login info with the data in the database
def login():
    error = None
    if request.method == "POST":
        email = request.form['login-email']
        password = request.form['login-password']
        # Find user by email entered.
        user = User.query.filter_by(email=email).first()
        if not user:
            # Send flash message
            flash('That email does not exist, please try again.', category='error')
            return redirect(url_for('login'))
        # Check stored password hash against entered password hashed.
        elif not check_password_hash(user.password, password):
            flash("Password incorrect, please try again!", category="error")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html", current_user=current_user)

@app.route('/logout')
# Logout user
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
