from flask import Flask, render_template, request, redirect, session
from models import db, User, Project, Task
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- AUTH ---------------- #

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect('/dashboard')

        return "Invalid credentials"

    return render_template('login.html')


@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    role = request.form['role']

    user = User(name=name, email=email, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    return redirect('/')


# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    role = session['role']

    if role == 'admin':
        tasks = Task.query.all()
        projects = Project.query.all()
    else:
        tasks = Task.query.filter_by(assigned_to=user_id).all()
        projects = Project.query.all()

    users = User.query.all()

    total = len(tasks)
    completed = len([t for t in tasks if t.status == 'Done'])
    overdue = len([t for t in tasks if t.deadline and t.deadline < datetime.utcnow()])

    return render_template('dashboard.html',
                           tasks=tasks,
                           users=users,
                           projects=projects,
                           total=total,
                           completed=completed,
                           overdue=overdue,
                           role=role)


# ---------------- PROJECT ---------------- #

@app.route('/create_project', methods=['POST'])
def create_project():
    if session.get('role') != 'admin':
        return "Access Denied"

    name = request.form['name']

    project = Project(name=name, created_by=session['user_id'])
    db.session.add(project)
    db.session.commit()

    return redirect('/dashboard')


# ---------------- TASK ---------------- #

@app.route('/create_task', methods=['POST'])
def create_task():
    title = request.form['title']
    description = request.form['description']
    assigned_to = int(request.form['assigned_to'])
    project_id = int(request.form['project_id'])
    deadline = request.form['deadline']

    task = Task(
        title=title,
        description=description,
        assigned_to=assigned_to,
        project_id=project_id,
        status="Todo",
        deadline=datetime.strptime(deadline, "%Y-%m-%d") if deadline else None
    )

    db.session.add(task)
    db.session.commit()

    return redirect('/dashboard')


@app.route('/update_task/<int:id>', methods=['POST'])
def update_task(id):
    task = Task.query.get(id)
    task.status = request.form['status']
    db.session.commit()

    return redirect('/dashboard')


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)