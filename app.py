import os, json, cv2, numpy as np, base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from PIL import Image
from io import BytesIO


# --- Setup & config ---
load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def path(*parts): return os.path.join(BASE_DIR, *parts)
def ensure_dirs():
    os.makedirs(path("data", "faces"), exist_ok=True)
    os.makedirs(path("data", "models"), exist_ok=True)

ensure_dirs()

app = Flask(__name__, template_folder=path("templates"), static_folder=path("static"))
app.secret_key = os.getenv("SECRET_KEY", "dev")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///" + path("facerecognition.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- DB models ---
class Department(db.Model):
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(50), nullable=False)
    
    # Relationships
    users = db.relationship('User', backref='department', lazy=True)
    courses = db.relationship('Course', backref='department', lazy=True)

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    idno = db.Column(db.String(20), unique=True, nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'admin'|'faculty'|'student'
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.dept_id'), nullable=True)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, lazy=True)
    faculty = db.relationship('Faculty', backref='user', uselist=False, lazy=True)
    event_attendances = db.relationship('EventAttendance', backref='user', lazy=True)

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)
    
    @property
    def full_name(self):
        return f"{self.firstname} {self.lastname}"
    
    @property
    def username(self):
        return self.idno

class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey('department.dept_id'), nullable=False)
    
    # Relationships
    students = db.relationship('Student', backref='course', lazy=True)

class Student(db.Model):
    student_id = db.Column(db.Integer, primary_key=True)
    year_level = db.Column(db.String(20), nullable=False)
    attendance_image = db.Column(db.String(255), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.course_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    
    # Relationships
    student_classes = db.relationship('StudentClass', backref='student', lazy=True)
    
    @property
    def face_registered(self):
        return bool(self.attendance_image)

class Faculty(db.Model):
    faculty_id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(30), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    
    # Relationships
    classes = db.relationship('Class', backref='faculty', lazy=True)
    events = db.relationship('Event', backref='faculty', lazy=True)

class Day(db.Model):
    day_id = db.Column(db.Integer, primary_key=True)
    day_name = db.Column(db.String(10), nullable=False)
    
    # Relationships
    class_days = db.relationship('ClassDay', backref='day', lazy=True)

class Class(db.Model):
    class_id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(20), nullable=False)
    edpcode = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(10), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    
    # Relationships
    class_days = db.relationship('ClassDay', backref='class', lazy=True)
    student_classes = db.relationship('StudentClass', backref='class', lazy=True)

class ClassDay(db.Model):
    class_id = db.Column(db.Integer, db.ForeignKey('class.class_id'), primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('day.day_id'), primary_key=True)

class StudentClass(db.Model):
    studentclass_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.class_id'), nullable=False)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='student_class', lazy=True)

class Attendance(db.Model):
    attendance_id = db.Column(db.Integer, primary_key=True)
    attendance_date = db.Column(db.DateTime, nullable=False)
    attendance_status = db.Column(db.String(10), nullable=False)
    studentclass_id = db.Column(db.Integer, db.ForeignKey('student_class.studentclass_id'), nullable=False)

class Event(db.Model):
    event_id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(20), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'), nullable=False)
    
    # Relationships
    event_attendances = db.relationship('EventAttendance', backref='event', lazy=True)

class EventAttendance(db.Model):
    event_attend_id = db.Column(db.Integer, primary_key=True)
    attendance_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

with app.app_context():
    db.create_all()
    
    # Create default admin user if it doesn't exist
    if not User.query.filter_by(idno="admin").first():
        admin = User(
            idno="admin",
            firstname="System",
            lastname="Administrator",
            role="admin",
            dept_id=1
        )
        admin.set_password("admin")
        db.session.add(admin)
        db.session.commit()

# --- Helpers for model files ---
def model_paths():
    return (path("data", "models", "lbph.xml"), path("data", "models", "labels.json"))

def train_lbph():
    """Train LBPH model from images in data/faces/<student_id>/*.jpg"""
    faces_root = path("data", "faces")
    images, labels = [], []
    id_map, next_id = {}, 0

    # Collect data
    if not os.path.isdir(faces_root):
        return False, "No dataset folder found."

    # Ensure we only use directories as identities
    person_dirs = [d for d in sorted(os.listdir(faces_root)) if os.path.isdir(os.path.join(faces_root, d))]
    for person in person_dirs:
        sid = person.strip()
        if not sid:
            continue
        if sid not in id_map:
            id_map[sid] = next_id; next_id += 1
        person_path = os.path.join(faces_root, sid)
        for file in os.listdir(person_path):
            if not file.lower().endswith(".jpg"): 
                continue
            img_path = os.path.join(person_path, file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            # normalize size for LBPH consistency
            img = cv2.resize(img, (200, 200))
            images.append(img)
            labels.append(id_map[sid])

    if not images:
        return False, "No training images found. Register faces first."

    # Train model
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        return False, f"OpenCV LBPH not available: {e}. Ensure 'opencv-contrib-python' is installed."

    recognizer.train(images, np.array(labels))
    mpath, lpath = model_paths()
    recognizer.write(mpath)
    with open(lpath, "w") as f:
        json.dump({v: k for k, v in id_map.items()}, f, indent=2)

    return True, f"Trained LBPH model with {len(id_map)} identities and {len(images)} images."

# --- Routes ---
@app.route("/")
def index():
    # Redirect directly to login page
    return redirect(url_for("login"))

@app.route("/admin/users")
def admin_users_page():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))
    # Aggregate data for table
    users = User.query.all()
    data = []
    for u in users:
        item = {
            "user_id": u.user_id,
            "idno": u.idno,
            "firstname": u.firstname,
            "lastname": u.lastname,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else None,
            "dept_id": u.dept_id,
            "dept_name": u.department.dept_name if u.department else "N/A",
        }
        if u.role == "student" and u.student:
            item["year_level"] = u.student.year_level
            item["course_id"] = u.student.course_id
            item["course_name"] = u.student.course.course_name if u.student.course else "N/A"
        if u.role == "faculty" and u.faculty:
            item["position"] = u.faculty.position
        data.append(item)

    departments = [{"id": d.dept_id, "name": d.dept_name} for d in Department.query.all()]
    courses = [{"id": c.course_id, "name": c.course_name} for c in Course.query.all()]
    return render_template("admin_users.html", users=data, departments=departments, courses=courses)

@app.route("/admin/users/create", methods=["POST"])
def admin_users_create():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        data = request.get_json()
        idno = (data.get("idno") or "").strip()
        firstname = (data.get("firstname") or "").strip()
        lastname = (data.get("lastname") or "").strip()
        password = (data.get("password") or "").strip()
        role = (data.get("role") or "").strip()
        dept_id = data.get("dept_id")
        course_id = data.get("course_id")
        year_level = (data.get("year_level") or "").strip()
        position = (data.get("position") or "").strip()

        if not all([idno, firstname, lastname, password, role]):
            return jsonify({"success": False, "message": "All required fields must be provided"}), 400
        if User.query.filter_by(idno=idno).first():
            return jsonify({"success": False, "message": "User ID already exists"}), 400

        u = User(idno=idno, firstname=firstname, lastname=lastname, role=role, dept_id=int(dept_id) if dept_id else None)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
        if role == "student":
            if not course_id:
                return jsonify({"success": False, "message": "Course is required for students"}), 400
            db.session.add(Student(user_id=u.user_id, course_id=int(course_id), year_level=year_level or "1st Year"))
        elif role == "faculty":
            if not position:
                return jsonify({"success": False, "message": "Position is required for faculty"}), 400
            db.session.add(Faculty(user_id=u.user_id, position=position))
        db.session.commit()
        return jsonify({"success": True, "message": f"User {firstname} {lastname} created", "user_id": u.user_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error creating user: {e}"}), 500

@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
def admin_users_edit(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    u = User.query.get_or_404(user_id)
    if request.method == "GET":
        payload = {
            "user_id": u.user_id,
            "idno": u.idno,
            "firstname": u.firstname,
            "lastname": u.lastname,
            "role": u.role,
            "dept_id": u.dept_id,
        }
        if u.role == "student" and u.student:
            payload.update({"course_id": u.student.course_id, "year_level": u.student.year_level})
        if u.role == "faculty" and u.faculty:
            payload.update({"position": u.faculty.position})
        return jsonify({"user": payload})
    try:
        data = request.get_json()
        u.firstname = (data.get("firstname") or u.firstname or "").strip()
        u.lastname = (data.get("lastname") or u.lastname or "").strip()
        new_role = (data.get("role") or u.role or "").strip()
        u.dept_id = data.get("dept_id")
        course_id = data.get("course_id")
        year_level = (data.get("year_level") or "").strip()
        position = (data.get("position") or "").strip()

        if u.role != new_role:
            # remove old
            if u.role == "student" and u.student: db.session.delete(u.student)
            if u.role == "faculty" and u.faculty: db.session.delete(u.faculty)
            u.role = new_role
        # upsert role specifics
        if u.role == "student":
            if u.student is None:
                db.session.add(Student(user_id=u.user_id, course_id=course_id, year_level=year_level or "1st Year"))
            else:
                if course_id: u.student.course_id = course_id
                if year_level: u.student.year_level = year_level
        elif u.role == "faculty":
            if u.faculty is None:
                db.session.add(Faculty(user_id=u.user_id, position=position or "Instructor"))
            else:
                if position: u.faculty.position = position
        db.session.commit()
        return jsonify({"success": True, "message": f"User {u.full_name} updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating user: {e}"}), 500

@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_users_reset(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        u = User.query.get_or_404(user_id)
        new_password = request.get_json().get("password", "").strip()
        if len(new_password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400
        u.set_password(new_password)
        db.session.commit()
        return jsonify({"success": True, "message": f"Password reset for {u.full_name}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error resetting password: {e}"}), 500

@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
def admin_users_toggle(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        u = User.query.get_or_404(user_id)
        if u.user_id == session["user_id"]:
            return jsonify({"success": False, "message": "Cannot toggle your own account"}), 400
        u.is_active = not u.is_active
        db.session.commit()
        return jsonify({"success": True, "message": f"User {u.full_name} {'activated' if u.is_active else 'deactivated'}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error toggling status: {e}"}), 500

@app.route("/attendance-monitoring")
def attendance_monitoring_module():
    """Attendance Monitoring Module - Main interface for attendance management"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Allow admin and faculty to access this module
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return redirect(url_for("dashboard"))
    
    return render_template("attendance_monitoring.html")

@app.route("/api/attendance-records", methods=["GET"])
def get_attendance_records():
    """Get attendance records with optional filtering"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        date_filter = request.args.get('date')
        class_filter = request.args.get('class_id')
        
        # Query attendance records with joins
        query = db.session.query(
            Attendance.attendance_id,
            Attendance.attendance_date,
            Attendance.attendance_status,
            User.idno.label('student_id'),
            User.firstname,
            User.lastname,
            Class.class_name
        ).join(
            StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id
        ).join(
            Student, StudentClass.student_id == Student.student_id
        ).join(
            User, Student.user_id == User.user_id
        ).join(
            Class, StudentClass.class_id == Class.class_id
        )
        
        # Apply filters if provided
        if date_filter:
            query = query.filter(Attendance.attendance_date >= date_filter)
        if class_filter:
            query = query.filter(Class.class_id == class_filter)
        
        records = query.order_by(Attendance.attendance_date.desc()).limit(100).all()
        
        records_data = []
        for record in records:
            records_data.append({
                "id": record.attendance_id,
                "student_id": record.student_id,
                "student_name": f"{record.firstname} {record.lastname}",
                "class_name": record.class_name,
                "date": record.attendance_date.strftime("%Y-%m-%d") if record.attendance_date else "N/A",
                "time": record.attendance_date.strftime("%H:%M") if record.attendance_date else "N/A",
                "status": record.attendance_status
            })
        
        return jsonify({"success": True, "records": records_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching records: {e}"}), 500

@app.route("/api/daily-logs", methods=["GET"])
def get_daily_logs():
    """Get daily attendance logs and statistics"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get attendance statistics for the day
        attendance_stats = db.session.query(
            Attendance.attendance_status,
            db.func.count(Attendance.attendance_id).label('count')
        ).filter(
            db.func.date(Attendance.attendance_date) == target_date
        ).group_by(Attendance.attendance_status).all()
        
        stats = {"total": 0, "present": 0, "absent": 0, "late": 0}
        chart_data = {"present": 0, "absent": 0, "late": 0}
        
        for stat in attendance_stats:
            count = stat.count
            status = stat.attendance_status.lower()
            stats["total"] += count
            if status in stats:
                stats[status] = count
                chart_data[status] = count
        
        # Get class breakdown
        class_breakdown = db.session.query(
            Class.class_name,
            db.func.count(Attendance.attendance_id).label('total_attendance'),
            db.func.sum(db.case([(Attendance.attendance_status == 'present', 1)], else_=0)).label('present_count')
        ).join(
            StudentClass, Class.class_id == StudentClass.class_id
        ).join(
            Attendance, StudentClass.studentclass_id == Attendance.studentclass_id
        ).filter(
            db.func.date(Attendance.attendance_date) == target_date
        ).group_by(Class.class_id, Class.class_name).all()
        
        breakdown = []
        for item in class_breakdown:
            attendance_rate = round((item.present_count / item.total_attendance * 100), 1) if item.total_attendance > 0 else 0
            breakdown.append({
                "class_name": item.class_name,
                "attendance_rate": attendance_rate
            })
        
        return jsonify({
            "success": True,
            "stats": stats,
            "chartData": chart_data,
            "breakdown": breakdown
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching daily logs: {e}"}), 500

@app.route("/api/edit-attendance", methods=["POST"])
def edit_attendance():
    """Edit or override attendance record"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    # Only allow admin and faculty to edit attendance
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        attendance_id = data.get("attendance_id")
        new_status = data.get("status")
        notes = data.get("notes", "")
        
        if not attendance_id or not new_status:
            return jsonify({"success": False, "message": "Attendance ID and status required"}), 400
        
        # Find and update the attendance record
        attendance = Attendance.query.get(attendance_id)
        if not attendance:
            return jsonify({"success": False, "message": "Attendance record not found"}), 404
        
        attendance.attendance_status = new_status
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Attendance status updated to {new_status}"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating attendance: {e}"}), 500

@app.route("/api/export-attendance", methods=["POST"])
def export_attendance():
    """Export attendance data in various formats"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        format_type = data.get("format", "excel")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        class_id = data.get("class_id")
        
        # Build query for export data
        query = db.session.query(
            User.idno,
            User.firstname,
            User.lastname,
            Class.class_name,
            Attendance.attendance_date,
            Attendance.attendance_status
        ).join(
            StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id
        ).join(
            Student, StudentClass.student_id == Student.student_id
        ).join(
            User, Student.user_id == User.user_id
        ).join(
            Class, StudentClass.class_id == Class.class_id
        )
        
        # Apply filters
        if start_date:
            query = query.filter(Attendance.attendance_date >= start_date)
        if end_date:
            query = query.filter(Attendance.attendance_date <= end_date)
        if class_id:
            query = query.filter(Class.class_id == class_id)
        
        export_data = query.all()
        
        # For now, return success message
        # In a real implementation, you would generate actual Excel/PDF files
        return jsonify({
            "success": True,
            "message": f"Export completed: {len(export_data)} records exported as {format_type.upper()}",
            "download_url": f"/downloads/attendance_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Export error: {e}"}), 500

@app.route("/class-management")
def class_management_module():
    """Class & Event Management Module - Main interface for class and event management"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Allow admin and faculty to access this module
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return redirect(url_for("dashboard"))
    
    return render_template("class_management.html")

@app.route("/api/all-courses", methods=["GET"])
def get_all_courses():
    """Get all courses for class creation"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        courses = Course.query.all()
        courses_data = [{"id": c.course_id, "name": c.course_name, "department_id": c.dept_id} for c in courses]
        return jsonify({"success": True, "courses": courses_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching courses: {e}"}), 500

@app.route("/api/create-class", methods=["POST"])
def create_class():
    """Create a new class"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        class_name = (data.get("name") or "").strip()
        class_code = (data.get("code") or "").strip()
        course_id = data.get("course_id")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        days = data.get("days", [])
        room = (data.get("room") or "").strip()
        
        if not all([class_name, class_code, start_time, end_time]):
            return jsonify({"success": False, "message": "All required fields must be provided"}), 400
        
        # Check if EDP code already exists
        existing_class = Class.query.filter_by(edpcode=class_code).first()
        if existing_class:
            return jsonify({"success": False, "message": "Class code already exists"}), 400
        
        # Parse time strings to time objects
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
        
        # Create new class (note: using edpcode field for class_code)
        new_class = Class(
            class_name=class_name,
            edpcode=class_code,
            start_time=start_time_obj,
            end_time=end_time_obj,
            room=room,
            faculty_id=None  # No faculty assigned initially - must be assigned manually
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Class '{class_name}' created successfully",
            "class_id": new_class.class_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error creating class: {e}"}), 500

@app.route("/api/create-event", methods=["POST"])
def create_event():
    """Create a new event"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        event_name = (data.get("name") or "").strip()
        event_type = (data.get("type") or "").strip()
        event_date = data.get("date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        location = (data.get("location") or "").strip()
        description = (data.get("description") or "").strip()
        duration = data.get("duration")
        
        if not all([event_name, event_type, event_date, start_time, end_time]):
            return jsonify({"success": False, "message": "All required fields must be provided"}), 400
        
        # Parse date
        event_datetime = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
        
        # Create new event (assuming you have an Event model)
        # For now, we'll create a simplified event record
        # In a full implementation, you'd have a proper Event model
        
        return jsonify({
            "success": True,
            "message": f"Event '{event_name}' created successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error creating event: {e}"}), 500

@app.route("/api/faculty-list", methods=["GET"])
def get_faculty_list():
    """Get list of faculty members"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        faculty = User.query.filter_by(role="faculty").all()
        faculty_data = [
            {
                "id": f.user_id,
                "name": f"{f.firstname} {f.lastname}",
                "id_number": f.idno
            }
            for f in faculty
        ]
        return jsonify({"success": True, "faculty": faculty_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching faculty: {e}"}), 500

@app.route("/api/student-list", methods=["GET"])
def get_student_list():
    """Get list of students"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        students = db.session.query(
            User.user_id,
            User.firstname,
            User.lastname,
            User.idno
        ).join(Student, User.user_id == Student.user_id).all()
        
        students_data = [
            {
                "id": s.user_id,
                "name": f"{s.firstname} {s.lastname}",
                "id_number": s.idno
            }
            for s in students
        ]
        return jsonify({"success": True, "students": students_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching students: {e}"}), 500

@app.route("/api/class-list", methods=["GET"])
def get_class_list():
    """Get list of classes"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        classes = Class.query.all()
        classes_data = [
            {
                "id": c.class_id,
                "name": c.class_name,
                "code": c.edpcode
            }
            for c in classes
        ]
        return jsonify({"success": True, "classes": classes_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching classes: {e}"}), 500

@app.route("/api/event-list", methods=["GET"])
def get_event_list():
    """Get list of events"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # For now, return empty events list since we don't have Event model yet
        # In a full implementation, you'd query the Event model
        events_data = []
        return jsonify({"success": True, "events": events_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching events: {e}"}), 500

@app.route("/api/department-list", methods=["GET"])
def get_department_list():
    """Get list of departments"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        departments = Department.query.all()
        dept_data = [
            {
                "id": d.dept_id,
                "name": d.dept_name
            }
            for d in departments
        ]
        return jsonify({"success": True, "departments": dept_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching departments: {e}"}), 500

@app.route("/api/enroll-student", methods=["POST"])
def enroll_student():
    """Enroll a student in a class"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        user_id = data.get("student_id")  # This is actually user_id from frontend
        class_id = data.get("class_id")
        
        if not all([user_id, class_id]):
            return jsonify({"success": False, "message": "Student ID and Class ID required"}), 400
        
        # Get the student record from user_id
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({"success": False, "message": "Student record not found"}), 404
        
        # Check if class is active
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return jsonify({"success": False, "message": "Class not found"}), 404
        
        if class_obj.status != 'active':
            return jsonify({"success": False, "message": "Cannot enroll students in deactivated classes"}), 400
        
        # Check if student is already enrolled
        existing = StudentClass.query.filter_by(
            student_id=student.student_id,
            class_id=class_id
        ).first()
        
        if existing:
            return jsonify({"success": False, "message": "Student is already enrolled in this class"}), 400
        
        # Create enrollment
        enrollment = StudentClass(
            student_id=student.student_id,
            class_id=int(class_id)
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Student enrolled successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error enrolling student: {e}"}), 500

@app.route("/api/current-enrollments", methods=["GET"])
def get_current_enrollments():
    """Get current student enrollments"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        class_filter = request.args.get("class_id")
        
        # Build query
        query = db.session.query(StudentClass, Class, Student, User).join(
            Class, StudentClass.class_id == Class.class_id
        ).join(
            Student, StudentClass.student_id == Student.student_id
        ).join(
            User, Student.user_id == User.user_id
        )
        
        if class_filter:
            query = query.filter(StudentClass.class_id == class_filter)
        
        enrollments = query.all()
        
        enrollment_data = []
        for student_class, class_obj, student, user in enrollments:
            enrollment_data.append({
                "enrollment_id": student_class.studentclass_id,
                "class_id": class_obj.class_id,
                "class_name": class_obj.class_name,
                "class_code": class_obj.edpcode,
                "student_id": student.student_id,
                "student_name": user.full_name,
                "student_idno": user.idno,
                "year_level": student.year_level,
                "course_name": student.course.course_name if student.course else "Unknown"
            })
        
        return jsonify({
            "success": True,
            "enrollments": enrollment_data,
            "count": len(enrollment_data)
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching enrollments: {e}"}), 500

@app.route("/api/classes-detailed", methods=["GET"])
def get_classes_detailed():
    """Get detailed classes data for view lists"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Get classes with faculty and enrollment information
        classes = db.session.query(Class, Faculty, User).outerjoin(
            Faculty, Class.faculty_id == Faculty.faculty_id
        ).outerjoin(
            User, Faculty.user_id == User.user_id
        ).all()
        
        classes_data = []
        for class_obj, faculty, user in classes:
            # Get enrollment count
            enrollment_count = StudentClass.query.filter_by(class_id=class_obj.class_id).count()
            
            classes_data.append({
                "id": class_obj.class_id,
                "code": class_obj.edpcode,
                "name": class_obj.class_name,
                "schedule": f"{class_obj.start_time.strftime('%H:%M')} - {class_obj.end_time.strftime('%H:%M')}",
                "room": class_obj.room,
                "instructor": user.full_name if user else "Not Assigned",
                "enrolled": enrollment_count,
                "status": class_obj.status
            })
        
        return jsonify({"success": True, "classes": classes_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching classes: {e}"}), 500

@app.route("/api/events-detailed", methods=["GET"])
def get_events_detailed():
    """Get detailed events data for view lists"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Get events with faculty information
        events = db.session.query(Event, Faculty, User).outerjoin(
            Faculty, Event.faculty_id == Faculty.faculty_id
        ).outerjoin(
            User, Faculty.user_id == User.user_id
        ).all()
        
        events_data = []
        for event_obj, faculty, user in events:
            events_data.append({
                "id": event_obj.event_id,
                "name": event_obj.event_name,
                "type": getattr(event_obj, 'event_type', 'General'),
                "date_time": f"{event_obj.event_date.strftime('%Y-%m-%d')} {event_obj.start_time.strftime('%H:%M')} - {event_obj.end_time.strftime('%H:%M')}",
                "location": getattr(event_obj, 'room', 'TBD'),
                "organizer": user.full_name if user else "Not Assigned",
                "status": "Active" if event_obj.event_date >= datetime.now().date() else "Completed"
            })
        
        return jsonify({"success": True, "events": events_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching events: {e}"}), 500

@app.route("/api/class-management-stats", methods=["GET"])
def get_class_management_stats():
    """Get statistics for class management dashboard"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        total_classes = Class.query.count()
        active_events = Event.query.count()
        enrolled_students = StudentClass.query.count()
        assigned_faculty = Class.query.filter(Class.faculty_id.isnot(None)).count()
        
        stats = {
            "total_classes": total_classes,
            "active_events": active_events,
            "enrolled_students": enrolled_students,
            "assigned_faculty": assigned_faculty
        }
        
        return jsonify({"success": True, "stats": stats})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching stats: {e}"}), 500

@app.route("/api/class-details/<int:class_id>", methods=["GET"])
def get_class_details(class_id):
    """Get detailed information about a specific class"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return jsonify({"success": False, "message": "Class not found"}), 404
        
        # Get class days
        class_days = ClassDay.query.filter_by(class_id=class_id).all()
        days = [day.day.day_name for day in class_days]
        
        # Format times for frontend
        start_time = class_obj.start_time.strftime('%H:%M')
        end_time = class_obj.end_time.strftime('%H:%M')
        
        class_data = {
            "id": class_obj.class_id,
            "name": class_obj.class_name,
            "code": class_obj.edpcode,
            "start_time": start_time,
            "end_time": end_time,
            "room": class_obj.room,
            "days": days,
            "status": class_obj.status
        }
        
        return jsonify({"success": True, "class": class_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching class details: {e}"}), 500

@app.route("/api/update-class", methods=["POST"])
def update_class():
    """Update an existing class"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        class_id = data.get("id")
        class_name = (data.get("name") or "").strip()
        class_code = (data.get("code") or "").strip()
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        days = data.get("days", [])
        room = (data.get("room") or "").strip()
        
        if not all([class_id, class_name, class_code, start_time, end_time, room]):
            return jsonify({"success": False, "message": "All required fields must be provided"}), 400
        
        # Get the class to update
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return jsonify({"success": False, "message": "Class not found"}), 404
        
        # Check if EDP code already exists (excluding current class)
        existing_class = Class.query.filter(Class.edpcode == class_code, Class.class_id != class_id).first()
        if existing_class:
            return jsonify({"success": False, "message": "Class code already exists"}), 400
        
        # Parse time strings to time objects
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
        
        # Update class information
        class_obj.class_name = class_name
        class_obj.edpcode = class_code
        class_obj.start_time = start_time_obj
        class_obj.end_time = end_time_obj
        class_obj.room = room
        
        # Update class days
        # First, remove existing class days
        ClassDay.query.filter_by(class_id=class_id).delete()
        
        # Add new class days
        for day_name in days:
            day_obj = Day.query.filter_by(day_name=day_name).first()
            if day_obj:
                class_day = ClassDay(class_id=class_id, day_id=day_obj.day_id)
                db.session.add(class_day)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Class '{class_name}' updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating class: {e}"}), 500

@app.route("/api/toggle-class-status", methods=["POST"])
def toggle_class_status():
    """Toggle class status between active and deactivated"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        class_id = data.get("class_id")
        status = data.get("status")
        
        if not class_id or not status:
            return jsonify({"success": False, "message": "Class ID and status are required"}), 400
        
        if status not in ['active', 'deactivated']:
            return jsonify({"success": False, "message": "Invalid status. Must be 'active' or 'deactivated'"}), 400
        
        # Get the class to update
        class_obj = Class.query.get(class_id)
        if not class_obj:
            return jsonify({"success": False, "message": "Class not found"}), 404
        
        # Update class status
        class_obj.status = status
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Class '{class_obj.class_name}' {status} successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating class status: {e}"}), 500

@app.route("/api/assign-faculty", methods=["POST"])
def assign_faculty():
    """Assign faculty to a class or event"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        faculty_user_id = data.get("faculty_id")  # This is actually user_id from frontend
        assignment_type = data.get("assignment_type")  # "class" or "event"
        class_id = data.get("class_id")
        event_id = data.get("event_id")
        role = data.get("role", "instructor")
        
        if not all([faculty_user_id, assignment_type]):
            return jsonify({"success": False, "message": "Faculty ID and assignment type required"}), 400
        
        # Get faculty record using user_id
        faculty = Faculty.query.filter_by(user_id=faculty_user_id).first()
        if not faculty:
            return jsonify({"success": False, "message": "Faculty not found"}), 404
        
        if assignment_type == "class":
            if not class_id:
                return jsonify({"success": False, "message": "Class ID required for class assignment"}), 400
            
            # Update class with faculty assignment
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({"success": False, "message": "Class not found"}), 404
            
            class_obj.faculty_id = faculty.faculty_id
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Faculty {faculty.user.full_name} assigned to class {class_obj.class_name} as {role}"
            })
            
        elif assignment_type == "event":
            if not event_id:
                return jsonify({"success": False, "message": "Event ID required for event assignment"}), 400
            
            # Update event with faculty assignment
            event_obj = Event.query.get(event_id)
            if not event_obj:
                return jsonify({"success": False, "message": "Event not found"}), 404
            
            event_obj.faculty_id = faculty.faculty_id
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Faculty {faculty.user.full_name} assigned to event {event_obj.event_name} as {role}"
            })
        
        else:
            return jsonify({"success": False, "message": "Invalid assignment type"}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error assigning faculty: {e}"}), 500

@app.route("/api/current-assignments", methods=["GET"])
def get_current_assignments():
    """Get current faculty assignments"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        assignments = []
        
        # Get all classes (both assigned and unassigned)
        all_classes = Class.query.all()
        
        for class_obj in all_classes:
            if class_obj.faculty_id:
                # Class has faculty assigned
                faculty = Faculty.query.get(class_obj.faculty_id)
                if faculty:
                    user = User.query.get(faculty.user_id)
                    faculty_name = user.full_name if user else "Unknown Faculty"
                    faculty_id = faculty.faculty_id
                else:
                    faculty_name = "Unknown Faculty"
                    faculty_id = None
            else:
                # Class has no faculty assigned
                faculty_name = None
                faculty_id = None
            
            assignments.append({
                "type": "class",
                "id": class_obj.class_id,
                "name": class_obj.class_name,
                "code": class_obj.edpcode,
                "faculty_id": faculty_id,
                "faculty_name": faculty_name,
                "role": "Instructor" if faculty_name else None,
                "room": class_obj.room,
                "time": f"{class_obj.start_time.strftime('%H:%M')} - {class_obj.end_time.strftime('%H:%M')}"
            })
        
        # Get event assignments
        event_assignments = db.session.query(Event, Faculty, User).join(
            Faculty, Event.faculty_id == Faculty.faculty_id
        ).join(
            User, Faculty.user_id == User.user_id
        ).all()
        
        for event_obj, faculty, user in event_assignments:
            assignments.append({
                "type": "event",
                "id": event_obj.event_id,
                "name": event_obj.event_name,
                "code": event_obj.event_name,
                "faculty_id": faculty.faculty_id,
                "faculty_name": user.full_name,
                "role": "Instructor",
                "room": event_obj.room,
                "time": f"{event_obj.start_time.strftime('%H:%M')} - {event_obj.end_time.strftime('%H:%M')}",
                "date": event_obj.event_date.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            "success": True,
            "assignments": assignments
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching assignments: {e}"}), 500

@app.route("/api/edit-assignment", methods=["POST"])
def edit_assignment():
    """Edit faculty assignment for a class or event"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    user_role = session.get("role")
    if user_role not in ["admin"]:
        return jsonify({"success": False, "message": "Insufficient permissions"}), 403
    
    try:
        data = request.get_json()
        assignment_type = data.get("assignment_type")  # "class" or "event"
        assignment_id = data.get("assignment_id")
        new_faculty_user_id = data.get("new_faculty_id")
        new_role = data.get("new_role", "instructor")
        
        if not all([assignment_type, assignment_id, new_faculty_user_id]):
            return jsonify({"success": False, "message": "Assignment type, ID, and new faculty required"}), 400
        
        # Get new faculty record using user_id
        new_faculty = Faculty.query.filter_by(user_id=new_faculty_user_id).first()
        if not new_faculty:
            return jsonify({"success": False, "message": "New faculty not found"}), 404
        
        if assignment_type == "class":
            # Update class assignment
            class_obj = Class.query.get(assignment_id)
            if not class_obj:
                return jsonify({"success": False, "message": "Class not found"}), 404
            
            class_obj.faculty_id = new_faculty.faculty_id
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Class {class_obj.class_name} reassigned to {new_faculty.user.full_name} as {new_role}"
            })
            
        elif assignment_type == "event":
            # Update event assignment
            event_obj = Event.query.get(assignment_id)
            if not event_obj:
                return jsonify({"success": False, "message": "Event not found"}), 404
            
            event_obj.faculty_id = new_faculty.faculty_id
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Event {event_obj.event_name} reassigned to {new_faculty.user.full_name} as {new_role}"
            })
        
        else:
            return jsonify({"success": False, "message": "Invalid assignment type"}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error editing assignment: {e}"}), 500

@app.route("/reports-analytics")
def reports_analytics_module():
    """Reports & Analytics Module - Main interface for reporting and analytics"""
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Allow admin and faculty to access this module
    user_role = session.get("role")
    if user_role not in ["admin", "faculty"]:
        return redirect(url_for("dashboard"))
    
    return render_template("reports_analytics.html")

@app.route("/api/reports/stats", methods=["GET"])
def get_reports_stats():
    """Get statistics for reports dashboard"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Calculate overall attendance rate
        total_attendance = Attendance.query.count()
        present_attendance = Attendance.query.filter_by(attendance_status='present').count()
        overall_rate = round((present_attendance / total_attendance * 100), 1) if total_attendance > 0 else 0
        
        # Get other statistics
        active_classes = Class.query.count()
        total_students = Student.query.count()
        reports_generated = 0  # This would be tracked in a reports table in a full implementation
        
        stats = {
            "overall_rate": overall_rate,
            "active_classes": active_classes,
            "total_students": total_students,
            "reports_generated": reports_generated
        }
        
        return jsonify({"success": True, "stats": stats})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching stats: {e}"}), 500

@app.route("/api/reports/class-summary", methods=["POST"])
def generate_class_summary():
    """Generate class attendance summary report"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        class_id = data.get("class_id")
        range_type = data.get("range", "month")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        # Build query for attendance data
        query = db.session.query(
            Class.class_name,
            Class.edpcode,
            db.func.count(Attendance.attendance_id).label('total_attendance'),
            db.func.sum(db.case([(Attendance.attendance_status == 'present', 1)], else_=0)).label('present_count')
        ).join(
            StudentClass, Class.class_id == StudentClass.class_id
        ).join(
            Attendance, StudentClass.studentclass_id == Attendance.studentclass_id
        )
        
        # Apply filters
        if class_id:
            query = query.filter(Class.class_id == class_id)
        
        if start_date and end_date:
            query = query.filter(Attendance.attendance_date.between(start_date, end_date))
        elif range_type == "week":
            week_ago = datetime.utcnow() - timedelta(weeks=1)
            query = query.filter(Attendance.attendance_date >= week_ago)
        elif range_type == "month":
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.filter(Attendance.attendance_date >= month_ago)
        
        results = query.group_by(Class.class_id, Class.class_name, Class.edpcode).all()
        
        # Process results
        class_performance = []
        total_classes = len(results)
        total_attendance_sum = 0
        total_present_sum = 0
        
        for result in results:
            attendance_rate = round((result.present_count / result.total_attendance * 100), 1) if result.total_attendance > 0 else 0
            class_performance.append({
                "name": result.class_name,
                "code": result.edpcode,
                "total": result.total_attendance,
                "present": result.present_count,
                "rate": attendance_rate
            })
            total_attendance_sum += result.total_attendance
            total_present_sum += result.present_count
        
        # Calculate overall statistics
        average_attendance = round((total_present_sum / total_attendance_sum * 100), 1) if total_attendance_sum > 0 else 0
        
        # Get total students count
        if class_id:
            total_students = StudentClass.query.filter_by(class_id=class_id).count()
        else:
            total_students = Student.query.count()
        
        summary_data = {
            "total_classes": total_classes,
            "average_attendance": average_attendance,
            "total_students": total_students,
            "class_performance": class_performance
        }
        
        return jsonify({"success": True, "data": summary_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error generating class summary: {e}"}), 500

@app.route("/api/reports/event-summary", methods=["POST"])
def generate_event_summary():
    """Generate event attendance summary report"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        event_type = data.get("event_type")
        range_type = data.get("range", "month")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        # For now, return mock data since we don't have Event model yet
        # In a full implementation, this would query actual event attendance data
        events_data = [
            {
                "name": "Midterm Examination",
                "type": "exam",
                "date": "2025-01-15",
                "total": 150,
                "present": 135,
                "rate": 90
            },
            {
                "name": "Final Project Presentation",
                "type": "presentation", 
                "date": "2025-01-10",
                "total": 45,
                "present": 42,
                "rate": 93
            }
        ]
        
        summary_data = {
            "events": events_data,
            "total_events": len(events_data),
            "average_attendance": 91.5
        }
        
        return jsonify({"success": True, "data": summary_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error generating event summary: {e}"}), 500

@app.route("/api/reports/absence-analysis", methods=["POST"])
def generate_absence_analysis():
    """Generate absence patterns analysis"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        analysis_type = data.get("analysis_type", "student")
        time_period = data.get("time_period", "month")
        threshold = int(data.get("threshold", 20))
        
        # Calculate absence data
        if time_period == "month":
            date_filter = datetime.utcnow() - timedelta(days=30)
        elif time_period == "semester":
            date_filter = datetime.utcnow() - timedelta(days=120)
        else:  # year
            date_filter = datetime.utcnow() - timedelta(days=365)
        
        # Get absence statistics
        absence_query = db.session.query(
            db.func.date(Attendance.attendance_date).label('date'),
            db.func.count(Attendance.attendance_id).label('total'),
            db.func.sum(db.case([(Attendance.attendance_status == 'absent', 1)], else_=0)).label('absent_count')
        ).filter(
            Attendance.attendance_date >= date_filter
        ).group_by(db.func.date(Attendance.attendance_date)).all()
        
        # Process data for chart
        chart_labels = []
        chart_data = []
        patterns = []
        findings = []
        
        for record in absence_query:
            chart_labels.append(record.date.strftime('%Y-%m-%d'))
            absence_rate = round((record.absent_count / record.total * 100), 1) if record.total > 0 else 0
            chart_data.append(absence_rate)
            
            if absence_rate > threshold:
                patterns.append({
                    "title": f"High Absence Rate on {record.date.strftime('%B %d')}",
                    "description": f"Absence rate reached {absence_rate}% ({record.absent_count}/{record.total})",
                    "impact": "Significant impact on learning outcomes"
                })
        
        # Generate findings based on analysis type
        if analysis_type == "student":
            findings.append({
                "category": "Student-Level Analysis",
                "description": "Analysis of individual student absence patterns",
                "details": [
                    f"Students with absence rate above {threshold}% threshold identified",
                    "Patterns suggest need for individual intervention",
                    "Correlation with academic performance noted"
                ]
            })
        elif analysis_type == "class":
            findings.append({
                "category": "Class-Level Analysis", 
                "description": "Analysis of class-wide absence patterns",
                "details": [
                    "Certain classes show consistently higher absence rates",
                    "Time-of-day correlation detected",
                    "Subject-specific patterns identified"
                ]
            })
        
        analysis_data = {
            "chart_labels": chart_labels[-30:],  # Last 30 days
            "chart_data": chart_data[-30:],
            "patterns": patterns,
            "findings": findings
        }
        
        return jsonify({"success": True, "data": analysis_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error generating absence analysis: {e}"}), 500

@app.route("/api/reports/monthly-graphs", methods=["POST"])
def generate_monthly_graphs():
    """Generate monthly attendance graphs"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        graph_type = data.get("graph_type", "line")
        data_view = data.get("data_view", "overall")
        time_range = data.get("time_range", "6months")
        
        # Generate sample data for graphs
        months = ['August', 'September', 'October', 'November', 'December', 'January']
        attendance_rates = [85, 87, 82, 89, 91, 88]
        
        primary_chart_data = {
            "type": graph_type,
            "data": {
                "labels": months,
                "datasets": [{
                    "label": "Attendance Rate (%)",
                    "data": attendance_rates,
                    "borderColor": "rgb(99, 102, 241)",
                    "backgroundColor": "rgba(99, 102, 241, 0.1)"
                }]
            }
        }
        
        comparison_chart_data = {
            "type": "bar",
            "data": {
                "labels": months,
                "datasets": [{
                    "label": "Present",
                    "data": [1200, 1250, 1180, 1300, 1350, 1280],
                    "backgroundColor": "rgba(34, 197, 94, 0.8)"
                }, {
                    "label": "Absent", 
                    "data": [200, 180, 220, 150, 130, 170],
                    "backgroundColor": "rgba(239, 68, 68, 0.8)"
                }]
            }
        }
        
        statistics = [
            {"label": "Highest Rate", "value": "91%"},
            {"label": "Lowest Rate", "value": "82%"},
            {"label": "Average", "value": "87%"}
        ]
        
        graphs_data = {
            "primary_chart": primary_chart_data,
            "comparison_chart": comparison_chart_data,
            "statistics": statistics
        }
        
        return jsonify({"success": True, "data": graphs_data})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error generating monthly graphs: {e}"}), 500

@app.route("/api/reports/export", methods=["POST"])
def export_report():
    """Export reports in various formats"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        report_type = data.get("report_type", "attendance-summary")
        format_type = data.get("format", "pdf")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        class_filter = data.get("class_filter")
        department_filter = data.get("department_filter")
        
        # In a real implementation, you would:
        # 1. Generate the actual report data
        # 2. Create the file in the specified format
        # 3. Save it to a downloads directory
        # 4. Return the download URL
        
        filename = f"{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        
        return jsonify({
            "success": True,
            "message": f"Report exported successfully as {format_type.upper()}",
            "filename": filename,
            "download_url": f"/downloads/{filename}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error exporting report: {e}"}), 500

@app.route("/api/reports/export-history", methods=["GET"])
def get_export_history():
    """Get export history"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Mock export history data
        # In a real implementation, this would come from a database table
        history = [
            {
                "id": "1",
                "name": "Monthly Attendance Report",
                "format": "PDF",
                "date": "2025-01-18 10:30 AM"
            },
            {
                "id": "2", 
                "name": "Class Summary Report",
                "format": "Excel",
                "date": "2025-01-17 02:15 PM"
            }
        ]
        
        return jsonify({"success": True, "history": history})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching export history: {e}"}), 500

@app.route("/api/courses/<int:dept_id>", methods=["GET"])
def get_courses_by_department(dept_id):
    """Get courses filtered by department"""
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    try:
        courses = Course.query.filter_by(dept_id=dept_id).all()
        courses_data = [{"id": c.course_id, "name": c.course_name} for c in courses]
        return jsonify({"success": True, "courses": courses_data})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching courses: {e}"}), 500



def process_and_save_image(student_id, image_data):
    """Process base64 image data and save multiple training images (for face capture in dashboard)"""
    try:
        # Decode base64 image data
        if image_data.startswith('data:image'):
            # Remove the data:image/jpeg;base64, prefix
            image_data = image_data.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)
        
        # Open image with PIL
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Ensure destination folder exists
        dest = path("data", "faces", student_id)
        os.makedirs(dest, exist_ok=True)

        # Convert PIL image to OpenCV format for face detection
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Initialize face cascade for cropping
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        
        saved_count = 0
        
        if len(faces) > 0:
            # Use the largest detected face
            x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
            
            # Extract face region with some padding
            padding = int(max(w, h) * 0.2)
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(cv_image.shape[1], x + w + padding)
            y2 = min(cv_image.shape[0], y + h + padding)
            
            face_roi = gray[y1:y2, x1:x2]
            
            # Create multiple versions of the image for better training
            variations = [
                face_roi,  # Original
                cv2.equalizeHist(face_roi),  # Histogram equalization
                cv2.GaussianBlur(face_roi, (3, 3), 0),  # Slight blur
                cv2.bilateralFilter(face_roi, 9, 75, 75),  # Noise reduction
            ]
            
            # Add brightness variations
            for brightness in [-20, 0, 20]:
                adjusted = cv2.convertScaleAbs(face_roi, alpha=1.0, beta=brightness)
                variations.append(adjusted)
            
            # Save all variations
            for i, variation in enumerate(variations):
                if saved_count >= 20:  # Limit to 20 images
                    break

                # Resize to standard size
                variation = cv2.resize(variation, (200, 200))
                
                # Save image
                filename = f"{saved_count + 1}.jpg"
                filepath = os.path.join(dest, filename)
                cv2.imwrite(filepath, variation)
                saved_count += 1
        
        else:
            # No face detected, save the whole image resized
            # Convert back to grayscale and resize
            full_image = cv2.resize(gray, (200, 200))
            filename = "1.jpg"
            filepath = os.path.join(dest, filename)
            cv2.imwrite(filepath, full_image)
            saved_count = 1
        
        return True, saved_count, "Images processed and saved successfully"
        
    except Exception as e:
        return False, 0, f"Error processing image: {str(e)}"


# Old register_capture route removed - now using in-browser camera capture

@app.route("/train")
def train():
    ok, msg = train_lbph()
    status = 200 if ok else 400
    return msg, status

@app.route("/face_capture", methods=["POST"])
def face_capture():
    """Handle face image capture from dashboard"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first."}), 401
    
    student_id = request.form.get("student_id", "").strip()
    image_data = request.form.get("image_data", "").strip()
    
    if not student_id or not image_data:
        return jsonify({"success": False, "message": "Missing student ID or image data."}), 400
    
    # Verify this is the logged-in user
    user = User.query.get(session["user_id"])
    if not user or user.username != student_id:
        return jsonify({"success": False, "message": "You can only register your own face."}), 403
    
    # Process and save the image
    success, image_count, message = process_and_save_image(student_id, image_data)
    
    if not success:
        return jsonify({"success": False, "message": message}), 500
    
    # Update user's face_registered status
    user.face_registered = True
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Face registered successfully with {image_count} training images!",
        "image_count": image_count
    })

@app.route("/capture/<class_code>")
def capture(class_code):
    """
    Live recognition + attendance logging.
    Open this URL in a browser on the same machine running Flask:
      http://127.0.0.1:5000/capture/CS101
    The server will open a webcam window (press Q to end).
    """
    # --- model files check & load ---
    mpath, lpath = model_paths()
    if not (os.path.exists(mpath) and os.path.exists(lpath)):
        return "Model not found. Train first at /train.", 400

    # create recognizer and load model
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(mpath)
    except Exception as e:
        return f"OpenCV LBPH not available or model load failed: {e}", 500

    # load labels JSON (JSON keys may be strings)
    with open(lpath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    labels = {}
    for k, v in raw.items():
        try:
            labels[int(k)] = v
        except:
            labels[k] = v

    # --- ensure class exists in DB ---
    clazz = Class.query.filter_by(code=class_code).first()
    if not clazz:
        clazz = Class(code=class_code, name=class_code)
        db.session.add(clazz)
        db.session.commit()

    # --- open camera ---
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "No camera detected on this machine.", 500

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    recognized_ids = set()   # store student IDs (strings) already logged this session
    accept_threshold = 70    # LBPH: lower = stricter. Tune 60-80.

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100,100))

            for (x,y,w,h) in faces:
                roi = gray[y:y+h, x:x+w]
                try:
                    roi = cv2.resize(roi, (200,200))
                    label_id, conf = recognizer.predict(roi)
                except Exception:
                    label_id, conf = None, 999.0

                sid = labels.get(label_id) if label_id is not None else None

                # If recognized with acceptable confidence and not logged already, log it
                if sid and conf < accept_threshold and sid not in recognized_ids:
                    stu = User.query.filter_by(username=sid, role="student").first()
                    if not stu:
                        stu = User(role="student", username=sid, password="x")
                        db.session.add(stu); db.session.commit()
                    db.session.add(Attendance(student_id=stu.id, class_id=clazz.id, ts=datetime.utcnow()))
                    db.session.commit()
                    recognized_ids.add(sid)

                # draw results on frame
                color = (0,255,0) if (sid and conf < accept_threshold) else (0,0,255)
                cv2.rectangle(frame, (x,y), (x+w, y+h), color, 2)
                label_text = f"{sid if sid else 'Unknown'} ({conf:.1f})"
                cv2.putText(frame, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

            # HUD
            cv2.putText(frame, f"Class: {class_code}  Recognized: {len(recognized_ids)}  (Q to end)",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

            cv2.imshow(f"Attendance - {class_code} - press Q to end", frame)
            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return f"Session ended. Logged {len(recognized_ids)} unique students for {class_code}."

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(idno=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.user_id
            session["role"] = user.role
            session["just_logged_in"] = True
            session["user_name"] = user.full_name
            return redirect(url_for("dashboard"))
        return "Invalid Student/Faculty ID or password", 401
    # GET -> render login form
    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ROLE-BASED DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Get user information
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    # Check if just logged in for success notification
    just_logged_in = session.pop("just_logged_in", False)
    
    # Prepare user data for template
    user_data = {
        "id": user.user_id,
        "username": user.idno,
        "full_name": user.full_name,
        "email": None,  # Not in new schema
        "role": user.role,
        "year_level": user.student.year_level if user.student else None,
        "course": user.student.course.course_name if user.student and user.student.course else None,
        "face_registered": user.student.face_registered if user.student else False,
        "created_at": user.created_at,
        "just_logged_in": just_logged_in
    }
    
    role = session.get("role")
    if role == "admin":
        # Get stats for admin dashboard
        stats = {
            "total_users": User.query.count(),
            "total_students": User.query.filter_by(role="student").count(),
            "total_faculty": User.query.filter_by(role="faculty").count(),
            "face_registered": db.session.query(Student).filter(Student.attendance_image.isnot(None)).count()
        }
        return render_template("dashboard_admin.html", user=user_data, stats=stats)
    if role == "faculty":
        return render_template("dashboard_faculty.html", user=user_data)
    if role == "student":
        return render_template("dashboard_student.html", user=user_data)
    return "Unknown role", 400


# ---------------------
# Faculty utilities
# ---------------------
def require_login_role(role_required):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != role_required:
                return "Forbidden", 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


# ---------------------
# Faculty: Attendance pages
# ---------------------
@app.route("/attendance/logs")
@require_login_role("faculty")
def attendance_logs():
    # Basic recent attendance records joined for display
    records = (
        db.session.query(Attendance, StudentClass, Class, Student, User)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .join(Student, StudentClass.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .order_by(Attendance.attendance_date.desc())
        .limit(200)
        .all()
    )
    return render_template("faculty/logs.html", records=records)


@app.route("/attendance/filter")
@require_login_role("faculty")
def attendance_filter():
    class_code = request.args.get("class", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    q = (
        db.session.query(Attendance, StudentClass, Class, Student, User)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .join(Student, StudentClass.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
    )
    if class_code:
        q = q.filter(Class.edpcode == class_code)
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            q = q.filter(Attendance.attendance_date >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt2 = datetime.fromisoformat(end_date)
            q = q.filter(Attendance.attendance_date <= dt2)
        except Exception:
            pass
    q = q.order_by(Attendance.attendance_date.desc()).limit(1000)
    records = q.all()
    return render_template("faculty/filter.html", records=records, class_code=class_code, start_date=start_date, end_date=end_date)


@app.route("/attendance/edit", methods=["GET", "POST"])
@require_login_role("faculty")
def attendance_edit():
    if request.method == "POST":
        att_id = request.form.get("attendance_id")
        new_status = request.form.get("attendance_status", "").strip()
        if att_id and new_status:
            att = Attendance.query.get(int(att_id))
            if att:
                att.attendance_status = new_status
                db.session.commit()
        return redirect(url_for("attendance_edit"))

    # GET
    records = (
        db.session.query(Attendance, StudentClass, Class, Student, User)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .join(Student, StudentClass.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .order_by(Attendance.attendance_date.desc())
        .limit(200)
        .all()
    )
    return render_template("faculty/edit.html", records=records)


@app.route("/classes/events")
@require_login_role("faculty")
def classes_events():
    # Show events created by this faculty
    user = User.query.get(session.get("user_id"))
    faculty = Faculty.query.filter_by(user_id=user.user_id).first()
    events = Event.query.filter_by(faculty_id=faculty.faculty_id).order_by(Event.event_date.desc()).all() if faculty else []
    return render_template("faculty/events.html", events=events)


# ---------------------
# Exports
# ---------------------
def _attendance_query_for_export():
    return (
        db.session.query(Attendance, StudentClass, Class, Student, User)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .join(Student, StudentClass.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .order_by(Attendance.attendance_date.desc())
    )


@app.route("/attendance/export/csv")
@require_login_role("faculty")
def export_attendance_csv():
    import csv
    from flask import Response

    rows = _attendance_query_for_export().all()
    def generate():
        yield "attendance_id,attendance_date,status,class_code,class_name,student_id,student_name\n"
        for att, sc, clz, stu, usr in rows:
            student_name = f"{usr.firstname} {usr.lastname}"
            yield f"{att.attendance_id},{att.attendance_date.isoformat()},{att.attendance_status},{clz.edpcode},{clz.class_name},{usr.idno}," + student_name + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=attendance.csv"})


@app.route("/attendance/export/pdf")
@require_login_role("faculty")
def export_attendance_pdf():
    # Simple fallback: return CSV but with .pdf name for now
    resp = export_attendance_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=attendance.pdf"
    return resp


@app.route("/attendance/export/excel")
@require_login_role("faculty")
def export_attendance_excel():
    # Simple fallback to CSV labeled as .xlsx for initial functionality
    resp = export_attendance_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=attendance.xlsx"
    return resp


# ---------------------
# Faculty: Page-specific Export Routes
# ---------------------

# Logs page exports
@app.route("/attendance/logs/export/csv")
@require_login_role("faculty")
def export_logs_csv():
    import csv
    from flask import Response

    rows = _attendance_query_for_export().limit(200).all()
    def generate():
        yield "attendance_id,attendance_date,status,class_code,class_name,student_id,student_name\n"
        for att, sc, clz, stu, usr in rows:
            student_name = f"{usr.firstname} {usr.lastname}"
            yield f"{att.attendance_id},{att.attendance_date.isoformat()},{att.attendance_status},{clz.edpcode},{clz.class_name},{usr.idno}," + student_name + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=attendance_logs.csv"})


@app.route("/attendance/logs/export/pdf")
@require_login_role("faculty")
def export_logs_pdf():
    resp = export_logs_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=attendance_logs.pdf"
    return resp


@app.route("/attendance/logs/export/excel")
@require_login_role("faculty")
def export_logs_excel():
    resp = export_logs_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=attendance_logs.xlsx"
    return resp


# Filter page exports (with filter parameters)
@app.route("/attendance/filter/export/csv")
@require_login_role("faculty")
def export_filter_csv():
    import csv
    from flask import Response

    class_code = request.args.get("class", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    q = _attendance_query_for_export()
    if class_code:
        q = q.filter(Class.edpcode == class_code)
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            q = q.filter(Attendance.attendance_date >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt2 = datetime.fromisoformat(end_date)
            q = q.filter(Attendance.attendance_date <= dt2)
        except Exception:
            pass
    
    rows = q.limit(1000).all()
    
    def generate():
        yield "attendance_id,attendance_date,status,class_code,class_name,student_id,student_name\n"
        for att, sc, clz, stu, usr in rows:
            student_name = f"{usr.firstname} {usr.lastname}"
            yield f"{att.attendance_id},{att.attendance_date.isoformat()},{att.attendance_status},{clz.edpcode},{clz.class_name},{usr.idno}," + student_name + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=filtered_attendance.csv"})


@app.route("/attendance/filter/export/pdf")
@require_login_role("faculty")
def export_filter_pdf():
    resp = export_filter_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=filtered_attendance.pdf"
    return resp


@app.route("/attendance/filter/export/excel")
@require_login_role("faculty")
def export_filter_excel():
    resp = export_filter_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=filtered_attendance.xlsx"
    return resp


# Edit page exports
@app.route("/attendance/edit/export/csv")
@require_login_role("faculty")
def export_edit_csv():
    import csv
    from flask import Response

    rows = _attendance_query_for_export().limit(200).all()
    def generate():
        yield "attendance_id,attendance_date,status,class_code,class_name,student_id,student_name\n"
        for att, sc, clz, stu, usr in rows:
            student_name = f"{usr.firstname} {usr.lastname}"
            yield f"{att.attendance_id},{att.attendance_date.isoformat()},{att.attendance_status},{clz.edpcode},{clz.class_name},{usr.idno}," + student_name + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=edit_attendance.csv"})


@app.route("/attendance/edit/export/pdf")
@require_login_role("faculty")
def export_edit_pdf():
    resp = export_edit_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=edit_attendance.pdf"
    return resp


@app.route("/attendance/edit/export/excel")
@require_login_role("faculty")
def export_edit_excel():
    resp = export_edit_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=edit_attendance.xlsx"
    return resp


# Events page exports
@app.route("/classes/events/export/csv")
@require_login_role("faculty")
def export_events_csv():
    import csv
    from flask import Response

    # Get events for this faculty
    user = User.query.get(session.get("user_id"))
    faculty = Faculty.query.filter_by(user_id=user.user_id).first()
    events = Event.query.filter_by(faculty_id=faculty.faculty_id).order_by(Event.event_date.desc()).all() if faculty else []
    
    def generate():
        yield "event_id,event_name,description,event_date,start_time,end_time,room\n"
        for event in events:
            yield f"{event.event_id},{event.event_name},{event.desc or ''},{event.event_date.isoformat()},{event.start_time},{event.end_time},{event.room}\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=events.csv"})


@app.route("/classes/events/export/pdf")
@require_login_role("faculty")
def export_events_pdf():
    resp = export_events_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=events.pdf"
    return resp


@app.route("/classes/events/export/excel")
@require_login_role("faculty")
def export_events_excel():
    resp = export_events_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=events.xlsx"
    return resp


# Reports page exports
@app.route("/reports/export/csv")
@require_login_role("faculty")
def export_reports_csv():
    import csv
    from flask import Response

    class_filter = request.args.get("class", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Get class summaries
    q = (
        db.session.query(Class, db.func.count(Attendance.attendance_id).label('total'))
        .join(StudentClass, Class.class_id == StudentClass.class_id)
        .join(Attendance, StudentClass.studentclass_id == Attendance.studentclass_id)
    )
    
    if class_filter:
        q = q.filter(Class.class_name == class_filter)
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            q = q.filter(Attendance.attendance_date >= dt)
        except Exception:
            pass
    if end_date:
        try:
            dt2 = datetime.fromisoformat(end_date)
            q = q.filter(Attendance.attendance_date <= dt2)
        except Exception:
            pass
    
    q = q.group_by(Class.class_id, Class.class_name, Class.edpcode)
    class_summaries = q.all()
    
    def generate():
        yield "class_name,edp_code,total_attendance_entries\n"
        for class_obj, total in class_summaries:
            yield f"{class_obj.class_name},{class_obj.edpcode},{total}\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=reports_analytics.csv"})


@app.route("/reports/export/pdf")
@require_login_role("faculty")
def export_reports_pdf():
    resp = export_reports_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=reports_analytics.pdf"
    return resp


@app.route("/reports/export/excel")
@require_login_role("faculty")
def export_reports_excel():
    resp = export_reports_csv()
    resp.headers["Content-Disposition"] = "attachment; filename=reports_analytics.xlsx"
    return resp


# ---------------------
# Faculty: Reports & Analytics
# ---------------------
@app.route("/reports/overview")
@require_login_role("faculty")
def reports_overview():
    """Display the reports overview page with links to different report types"""
    # Get user information for the template
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    # Prepare user data for template
    user_data = {
        "id": user.user_id,
        "username": user.idno,
        "full_name": user.full_name,
        "email": None,  # Not in new schema
        "role": user.role,
        "year_level": user.student.year_level if user.student else None,
        "course": user.student.course.course_name if user.student and user.student.course else None,
        "face_registered": user.student.face_registered if user.student else False,
        "created_at": user.created_at,
    }
    
    return render_template("faculty/reports_overview.html", user=user_data)


@app.route("/reports/class-summaries")
@require_login_role("faculty")
def reports_class_summaries():
    """Display class summaries report"""
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    user_data = {
        "id": user.user_id,
        "username": user.idno,
        "full_name": user.full_name,
        "email": None,
        "role": user.role,
        "year_level": user.student.year_level if user.student else None,
        "course": user.student.course.course_name if user.student and user.student.course else None,
        "face_registered": user.student.face_registered if user.student else False,
        "created_at": user.created_at,
    }
    
    return render_template("faculty/class_summaries.html", user=user_data)


@app.route("/reports/absence-patterns")
@require_login_role("faculty")
def reports_absence_patterns():
    """Display absence patterns report"""
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    user_data = {
        "id": user.user_id,
        "username": user.idno,
        "full_name": user.full_name,
        "email": None,
        "role": user.role,
        "year_level": user.student.year_level if user.student else None,
        "course": user.student.course.course_name if user.student and user.student.course else None,
        "face_registered": user.student.face_registered if user.student else False,
        "created_at": user.created_at,
    }
    
    return render_template("faculty/absence_patterns.html", user=user_data)


@app.route("/reports/monthly-graphs")
@require_login_role("faculty")
def reports_monthly_graphs():
    """Display monthly graphs report"""
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("login"))
    
    user_data = {
        "id": user.user_id,
        "username": user.idno,
        "full_name": user.full_name,
        "email": None,
        "role": user.role,
        "year_level": user.student.year_level if user.student else None,
        "course": user.student.course.course_name if user.student and user.student.course else None,
        "face_registered": user.student.face_registered if user.student else False,
        "created_at": user.created_at,
    }
    
    return render_template("faculty/monthly_graphs.html", user=user_data)


# ---------------------
# API Routes for Reports
# ---------------------

@app.route("/api/classes/list")
@require_login_role("faculty")
def api_classes_list():
    """API endpoint to get list of classes for filter dropdown"""
    try:
        classes = Class.query.all()
        events = Event.query.all()
        
        class_list = []
        for cls in classes:
            class_list.append({
                "class_name": cls.class_name,
                "edpcode": cls.edpcode
            })
        
        for event in events:
            class_list.append({
                "event_name": event.event_name,
                "edpcode": event.event_name
            })
        
        return jsonify(class_list)
    except Exception as e:
        return jsonify([]), 500


@app.route("/api/reports/class-summaries")
@require_login_role("faculty")
def api_reports_class_summaries():
    """API endpoint for class summaries data"""
    try:
        class_filter = request.args.get("class", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()

        # Get class summaries
        q = (
            db.session.query(Class, db.func.count(Attendance.attendance_id).label('total'))
            .join(StudentClass, Class.class_id == StudentClass.class_id)
            .join(Attendance, StudentClass.studentclass_id == Attendance.studentclass_id)
        )
        
        if class_filter:
            q = q.filter(Class.class_name == class_filter)
        if start_date:
            try:
                dt = datetime.fromisoformat(start_date)
                q = q.filter(Attendance.attendance_date >= dt)
            except Exception:
                pass
        if end_date:
            try:
                dt2 = datetime.fromisoformat(end_date)
                q = q.filter(Attendance.attendance_date <= dt2)
            except Exception:
                pass
        
        q = q.group_by(Class.class_id, Class.class_name, Class.edpcode)
        class_summaries = q.all()
        
        result = []
        for class_obj, total in class_summaries:
            result.append({
                "class_name": class_obj.class_name,
                "edpcode": class_obj.edpcode,
                "total": total
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify([]), 500


@app.route("/api/reports/absence-patterns")
@require_login_role("faculty")
def api_reports_absence_patterns():
    """API endpoint for absence patterns data"""
    try:
        class_filter = request.args.get("class", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()

        # Get absence data by date
        q = (
            db.session.query(
                db.func.date(Attendance.attendance_date).label('date'),
                db.func.count(Attendance.attendance_id).label('count')
            )
            .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
            .join(Class, StudentClass.class_id == Class.class_id)
            .filter(Attendance.attendance_status == 'Absent')
        )
        
        if class_filter:
            q = q.filter(Class.class_name == class_filter)
        if start_date:
            try:
                dt = datetime.fromisoformat(start_date)
                q = q.filter(Attendance.attendance_date >= dt)
            except Exception:
                pass
        if end_date:
            try:
                dt2 = datetime.fromisoformat(end_date)
                q = q.filter(Attendance.attendance_date <= dt2)
            except Exception:
                pass
        
        q = q.group_by(db.func.date(Attendance.attendance_date)).order_by(db.func.date(Attendance.attendance_date))
        absence_data = q.all()
        
        labels = []
        values = []
        for date_obj, count in absence_data:
            labels.append(date_obj.strftime('%Y-%m-%d'))
            values.append(count)
        
        return jsonify({
            "labels": labels,
            "values": values
        })
    except Exception as e:
        return jsonify({
            "labels": [],
            "values": []
        }), 500


@app.route("/api/reports/monthly-graphs")
@require_login_role("faculty")
def api_reports_monthly_graphs():
    """API endpoint for monthly graphs data"""
    try:
        class_filter = request.args.get("class", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()

        # Get monthly attendance data
        q = (
            db.session.query(
                db.func.strftime('%Y-%m', Attendance.attendance_date).label('month'),
                db.func.count(Attendance.attendance_id).label('count')
            )
            .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
            .join(Class, StudentClass.class_id == Class.class_id)
        )
        
        if class_filter:
            q = q.filter(Class.class_name == class_filter)
        if start_date:
            try:
                dt = datetime.fromisoformat(start_date)
                q = q.filter(Attendance.attendance_date >= dt)
            except Exception:
                pass
        if end_date:
            try:
                dt2 = datetime.fromisoformat(end_date)
                q = q.filter(Attendance.attendance_date <= dt2)
            except Exception:
                pass
        
        q = q.group_by(db.func.strftime('%Y-%m', Attendance.attendance_date)).order_by(db.func.strftime('%Y-%m', Attendance.attendance_date))
        monthly_data = q.all()
        
        labels = []
        values = []
        for month, count in monthly_data:
            labels.append(month)
            values.append(count)
        
        return jsonify({
            "labels": labels,
            "values": values
        })
    except Exception as e:
        return jsonify({
            "labels": [],
            "values": []
        }), 500



# ---------------------
# Student-specific decorators and utilities
# ---------------------
def require_student_login():
    """Decorator to require student login and access to own data only"""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != "student":
                return "Forbidden - Student access only", 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

def get_current_student():
    """Get current logged-in student object"""
    if "user_id" not in session or session.get("role") != "student":
        return None
    
    user = User.query.get(session["user_id"])
    if not user or not user.student:
        return None
    
    return user.student

# ---------------------
# Student Profile Management
# ---------------------
@app.route("/student/profile")
@require_student_login()
def student_profile():
    """Student profile view and edit page"""
    user = User.query.get(session["user_id"])
    return render_template("student/profile.html", user=user)

@app.route("/student/profile/update", methods=["POST"])
@require_student_login()
def update_student_profile():
    """Update student profile information"""
    user = User.query.get(session["user_id"])
    
    # Get form data
    firstname = request.form.get("firstname", "").strip()
    lastname = request.form.get("lastname", "").strip()
    
    if not firstname or not lastname:
        return jsonify({"success": False, "message": "First name and last name are required"}), 400
    
    # Update user information
    user.firstname = firstname
    user.lastname = lastname
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating profile: {str(e)}"}), 500

@app.route("/student/password/change", methods=["POST"])
@require_student_login()
def change_student_password():
    """Change student password"""
    user = User.query.get(session["user_id"])
    
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    
    # Validate current password
    if not user.check_password(current_password):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400
    
    # Validate new password
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters"}), 400
    
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match"}), 400
    
    try:
        user.set_password(new_password)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error changing password: {str(e)}"}), 500

# ---------------------
# Student Face Registration
# ---------------------
@app.route("/student/face-registration")
@require_student_login()
def student_face_registration():
    """Face registration page for students"""
    student = get_current_student()
    return render_template("student/face_registration.html", student=student)

@app.route("/student/face-registration/capture", methods=["POST"])
@require_student_login()
def capture_student_face():
    """Capture and save student face for registration"""
    student = get_current_student()
    if not student:
        return jsonify({"success": False, "message": "Student not found"}), 404
    
    try:
        # Get image data from request
        image_data = request.json.get("image_data")
        if not image_data:
            return jsonify({"success": False, "message": "No image data provided"}), 400
        
        # Process and save the image
        success, message = process_and_save_image(str(student.student_id), image_data)
        
        if success:
            # Update student record
            student.attendance_image = f"{student.student_id}/face.jpg"
            db.session.commit()
            
            # Retrain the model
            train_success, train_message = train_lbph()
            if not train_success:
                print(f"Warning: Model training failed: {train_message}")
            
            return jsonify({"success": True, "message": "Face registered successfully"})
        else:
            return jsonify({"success": False, "message": message}), 500
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error registering face: {str(e)}"}), 500

# ---------------------
# Student Attendance Tracking
# ---------------------
@app.route("/student/attendance")
@require_student_login()
def student_attendance_view():
    """Student attendance history and logs"""
    student = get_current_student()
    if not student:
        return redirect(url_for("login"))
    
    # Get attendance records for this student
    attendance_records = (
        db.session.query(Attendance, StudentClass, Class)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .filter(StudentClass.student_id == student.student_id)
        .order_by(Attendance.attendance_date.desc())
        .limit(100)
        .all()
    )
    
    return render_template("student/attendance.html", 
                         student=student, 
                         attendance_records=attendance_records)

@app.route("/student/attendance/log", methods=["POST"])
@require_student_login()
def log_student_attendance():
    """Log attendance for a student (called by face recognition)"""
    student = get_current_student()
    if not student:
        return jsonify({"success": False, "message": "Student not found"}), 404
    
    class_id = request.json.get("class_id")
    if not class_id:
        return jsonify({"success": False, "message": "Class ID required"}), 400
    
    # Check if student is enrolled in this class
    student_class = StudentClass.query.filter_by(
        student_id=student.student_id,
        class_id=class_id
    ).first()
    
    if not student_class:
        return jsonify({"success": False, "message": "Student not enrolled in this class"}), 403
    
    # Check for duplicate attendance today
    today = datetime.now().date()
    existing_attendance = Attendance.query.filter(
        Attendance.studentclass_id == student_class.studentclass_id,
        Attendance.attendance_date >= datetime.combine(today, datetime.min.time()),
        Attendance.attendance_date < datetime.combine(today, datetime.max.time())
    ).first()
    
    if existing_attendance:
        return jsonify({"success": False, "message": "Attendance already logged for today"}), 409
    
    # Log new attendance
    try:
        attendance = Attendance(
            attendance_date=datetime.now(),
            attendance_status="present",
            studentclass_id=student_class.studentclass_id
        )
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Attendance logged successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error logging attendance: {str(e)}"}), 500

# ---------------------
# Student Class Management
# ---------------------
@app.route("/student/classes")
@require_student_login()
def student_classes():
    """View enrolled classes and schedules"""
    student = get_current_student()
    if not student:
        return redirect(url_for("login"))
    
    # Get enrolled classes with schedule information
    enrolled_classes = (
        db.session.query(Class, StudentClass, Faculty, User)
        .join(StudentClass, Class.class_id == StudentClass.class_id)
        .left_join(Faculty, Class.faculty_id == Faculty.faculty_id)
        .left_join(User, Faculty.user_id == User.user_id)
        .filter(StudentClass.student_id == student.student_id)
        .all()
    )
    
    return render_template("student/classes.html", 
                         student=student, 
                         enrolled_classes=enrolled_classes)

@app.route("/student/events")
@require_student_login()
def student_events():
    """View available events"""
    student = get_current_student()
    if not student:
        return redirect(url_for("login"))
    
    # Get current and upcoming events
    current_time = datetime.now()
    events = Event.query.filter(Event.event_date >= current_time.date()).order_by(Event.event_date).all()
    
    return render_template("student/events.html", 
                         student=student, 
                         events=events)

# ---------------------
# Student Reports & Analytics
# ---------------------
@app.route("/student/reports")
@require_student_login()
def student_reports():
    """Student personal reports and analytics"""
    student = get_current_student()
    if not student:
        return redirect(url_for("login"))
    
    # Calculate attendance statistics
    total_classes = (
        db.session.query(StudentClass)
        .filter(StudentClass.student_id == student.student_id)
        .count()
    )
    
    attended_classes = (
        db.session.query(Attendance)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .filter(StudentClass.student_id == student.student_id)
        .filter(Attendance.attendance_status == "present")
        .count()
    )
    
    attendance_rate = (attended_classes / total_classes * 100) if total_classes > 0 else 0
    
    # Get monthly attendance data for charts
    from sqlalchemy import func, extract
    monthly_data = (
        db.session.query(
            extract('month', Attendance.attendance_date).label('month'),
            func.count(Attendance.attendance_id).label('count')
        )
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .filter(StudentClass.student_id == student.student_id)
        .filter(Attendance.attendance_status == "present")
        .filter(extract('year', Attendance.attendance_date) == datetime.now().year)
        .group_by(extract('month', Attendance.attendance_date))
        .all()
    )
    
    stats = {
        "total_classes": total_classes,
        "attended_classes": attended_classes,
        "attendance_rate": round(attendance_rate, 2),
        "monthly_data": monthly_data
    }
    
    return render_template("student/reports.html", 
                         student=student, 
                         stats=stats)

@app.route("/student/reports/export/<format>")
@require_student_login()
def export_student_report(format):
    """Export student attendance report in various formats"""
    student = get_current_student()
    if not student:
        return redirect(url_for("login"))
    
    # Get attendance data
    attendance_data = (
        db.session.query(Attendance, StudentClass, Class)
        .join(StudentClass, Attendance.studentclass_id == StudentClass.studentclass_id)
        .join(Class, StudentClass.class_id == Class.class_id)
        .filter(StudentClass.student_id == student.student_id)
        .order_by(Attendance.attendance_date.desc())
        .all()
    )
    
    if format.lower() == "csv":
        return export_attendance_csv(student, attendance_data)
    elif format.lower() == "pdf":
        return export_attendance_pdf(student, attendance_data)
    elif format.lower() == "excel":
        return export_attendance_excel(student, attendance_data)
    else:
        return "Invalid format", 400

def export_attendance_csv(student, attendance_data):
    """Export attendance data as CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Date', 'Class', 'Status', 'Time'])
    
    # Write data
    for attendance, student_class, class_obj in attendance_data:
        writer.writerow([
            attendance.attendance_date.strftime('%Y-%m-%d'),
            class_obj.class_name,
            attendance.attendance_status,
            attendance.attendance_date.strftime('%H:%M:%S')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{student.student_id}.csv'
    
    return response

def export_attendance_pdf(student, attendance_data):
    """Export attendance data as PDF"""
    # This would require reportlab or similar library
    # For now, return a simple text response
    return "PDF export functionality to be implemented", 501

def export_attendance_excel(student, attendance_data):
    """Export attendance data as Excel"""
    # This would require openpyxl or similar library
    # For now, return a simple text response
    return "Excel export functionality to be implemented", 501

if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print('\nShutting down FaceCheck server...')
        # Clean up any OpenCV windows
        try:
            cv2.destroyAllWindows()
        except:
            pass
        sys.exit(0)
    
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("Starting FaceCheck server...")
        print("Press CTRL+C to stop the server")
        # Run server with proper threading and signal handling
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"\nServer error: {e}")
    finally:
        # Cleanup
        try:
            cv2.destroyAllWindows()
        except:
            pass
        print("FaceCheck server shutdown complete")
