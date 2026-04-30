from flask import Flask, render_template, request, redirect, session, flash
from models import db, User, Project, Task
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    task_columns = [column["name"] for column in inspector.get_columns("task")]
    if "priority" not in task_columns:
        with db.engine.connect() as connection:
            connection.execute(text("ALTER TABLE task ADD COLUMN priority VARCHAR(20) DEFAULT 'Medium'"))
            connection.commit()


STATUSES = ["Todo", "In Progress", "Done"]
PRIORITIES = ["Low", "Medium", "High"]

# ---------------- AUTH ---------------- #

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect('/dashboard')

        flash("Invalid email or password.", "error")

    return render_template('login.html')


@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name'].strip()
    email = request.form['email'].strip().lower()
    password_value = request.form['password']
    role = request.form.get('role', 'member')

    if role not in ["admin", "member"]:
        flash("Please choose a valid role.", "error")
        return redirect('/')

    if User.query.filter_by(email=email).first():
        flash("An account with this email already exists.", "error")
        return redirect('/')

    password = generate_password_hash(password_value)

    user = User(name=name, email=email, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    flash("Account created. You can log in now.", "success")
    return redirect('/')


# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    role = session['role']
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')

    if role == 'admin':
        task_query = Task.query
        projects = Project.query.all()
    else:
        task_query = Task.query.filter_by(assigned_to=user_id)
        projects = Project.query.all()

    if status_filter in STATUSES:
        task_query = task_query.filter_by(status=status_filter)

    if priority_filter in PRIORITIES:
        task_query = task_query.filter_by(priority=priority_filter)

    tasks = task_query.all()

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
                           role=role,
                           statuses=STATUSES,
                           priorities=PRIORITIES,
                           status_filter=status_filter,
                           priority_filter=priority_filter,
                           now=datetime.utcnow())


# ---------------- PROJECT ---------------- #

@app.route('/create_project', methods=['POST'])
def create_project():
    if session.get('role') != 'admin':
        flash("Only admins can create projects.", "error")
        return redirect('/dashboard')

    name = request.form['name'].strip()

    project = Project(name=name, created_by=session['user_id'])
    db.session.add(project)
    db.session.commit()

    flash("Project created.", "success")
    return redirect('/dashboard')


# ---------------- TASK ---------------- #

@app.route('/create_task', methods=['POST'])
def create_task():
    if 'user_id' not in session:
        return redirect('/')

    title = request.form['title']
    description = request.form['description']
    assigned_to = int(request.form['assigned_to'])
    project_id = int(request.form['project_id'])
    deadline = request.form['deadline']
    priority = request.form.get('priority', 'Medium')

    if priority not in PRIORITIES:
        flash("Please choose a valid task priority.", "error")
        return redirect('/dashboard')

    task = Task(
        title=title.strip(),
        description=description.strip(),
        assigned_to=assigned_to,
        project_id=project_id,
        priority=priority,
        status="Todo",
        deadline=datetime.strptime(deadline, "%Y-%m-%d") if deadline else None
    )

    db.session.add(task)
    db.session.commit()

    flash("Task created.", "success")
    return redirect('/dashboard')


@app.route('/update_task/<int:id>', methods=['POST'])
def update_task(id):
    if 'user_id' not in session:
        return redirect('/')

    task = Task.query.get_or_404(id)
    status = request.form['status']

    if status not in STATUSES:
        flash("Please choose a valid task status.", "error")
        return redirect('/dashboard')

    task.status = status
    db.session.commit()

    flash("Task updated.", "success")
    return redirect('/dashboard')


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
