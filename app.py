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
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'), nullable=False)
    
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
    # Welcome page -> role selection first
    return render_template("role_selection.html")

@app.route("/admin")
def admin():
    return jsonify({
        "users": User.query.count(),
        "classes": Class.query.count(),
        "attendance": Attendance.query.count()
    })

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

@app.route("/register/<role>", methods=["GET", "POST"])
def register(role):
    # Validate role parameter
    if role not in ['student', 'faculty']:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        # Debug: Log received data
        print(f"🔍 Registration request for role: {role}")
        print(f"📋 Received form data:")
        for key, value in request.form.items():
            print(f"  {key}: {value}")
        
        # Get form data
        firstname = request.form.get("firstname", "").strip()
        lastname = request.form.get("lastname", "").strip()
        username = request.form.get("username", "").strip()  # Can be student_id or faculty_id
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        # Role-specific fields
        if role == "student":
            year_level = request.form.get("year_level", "").strip()
            dept_id = request.form.get("dept_id", "").strip()
            course_id = request.form.get("course_id", "").strip()
            required_fields = [firstname, lastname, username, year_level, dept_id, course_id, password]
            print(f"📚 Student fields: year_level={year_level}, dept_id={dept_id}, course_id={course_id}")
        else:  # faculty
            dept_id = request.form.get("dept_id", "").strip()
            position = request.form.get("position", "").strip()
            required_fields = [firstname, lastname, username, dept_id, position, password]
            print(f"👨‍🏫 Faculty fields: dept_id={dept_id}, position={position}")
            print(f"🔍 Faculty form data check:")
            print(f"  - dept_id from form: '{dept_id}' (type: {type(dept_id)})")
            print(f"  - position from form: '{position}' (type: {type(position)})")
            print(f"  - All form keys: {list(request.form.keys())}")
        
        print(f"✅ Required fields validation: {required_fields}")
        print(f"🔍 All fields filled: {all(required_fields)}")
        
        # Validation
        if not all(required_fields):
            return jsonify({"success": False, "message": "All fields are required."}), 400
        
        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400
        
        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400

        # Check if username already exists
        existing_user = User.query.filter_by(idno=username).first()
        if existing_user:
            return jsonify({
                "success": False, 
                "message": f"{'Student ID' if role == 'student' else 'Faculty ID'} '{username}' is already registered. Please use a different ID or contact admin if this is your ID."
            }), 400

        try:
            # Create new user
            new_user = User(
                idno=username,
                firstname=firstname,
                lastname=lastname,
                role=role,
                dept_id=int(dept_id)  # Use selected dept for both students and faculty
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.flush()  # Get the user_id
            
            # Create role-specific records
            if role == "student":
                # Create student record with course_id
                new_student = Student(
                    year_level=year_level,
                    course_id=int(course_id),
                    user_id=new_user.user_id
                )
                db.session.add(new_student)
                
            else:  # faculty
                # Create faculty record
                print(f"👨‍🏫 Creating faculty record:")
                print(f"  - position: '{position}'")
                print(f"  - user_id: {new_user.user_id}")
                new_faculty = Faculty(
                    position=position,
                    user_id=new_user.user_id
                )
                db.session.add(new_faculty)
                print(f"✅ Faculty record added to session")
            
            db.session.commit()

            full_name = f"{firstname} {lastname}"
            role_display = "Student" if role == "student" else "Faculty"
            return jsonify({
                "success": True,
                "message": f"Welcome {full_name}! Your {role_display.lower()} account has been created successfully.",
                "username": username,
                "role": role_display,
                "next_step": "Complete face registration in your dashboard after login."
            })

        except Exception as e:
            db.session.rollback()
            print(f"❌ Registration error: {e}")  # Debug logging
            import traceback
            traceback.print_exc()  # Print full traceback
            return jsonify({
                "success": False,
                "message": f"Registration failed due to a system error. Please try again or contact admin. Error: {str(e)}"
            }), 500

    return render_template("register.html", role=role)

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
        return render_template("dashboard_admin.html", user=user_data)
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


# Reports
@app.route("/attendance/reports")
@require_login_role("faculty")
def attendance_reports():
    return render_template("faculty/reports.html")


@app.route("/reports/class-summaries")
@require_login_role("faculty")
def reports_class_summaries():
    # Basic aggregates per class
    from sqlalchemy import func
    data = (
        db.session.query(Class.class_name, Class.edpcode, func.count(Attendance.attendance_id))
        .join(StudentClass, StudentClass.class_id == Class.class_id)
        .join(Attendance, Attendance.studentclass_id == StudentClass.studentclass_id)
        .group_by(Class.class_id)
        .all()
    )
    return render_template("faculty/class_summaries.html", rows=data)


@app.route("/reports/absence-patterns")
@require_login_role("faculty")
def reports_absence_patterns():
    return render_template("faculty/absence_patterns.html")


@app.route("/reports/monthly-graphs")
@require_login_role("faculty")
def reports_monthly_graphs():
    return render_template("faculty/monthly_graphs.html")


@app.route("/reports/export/<fmt>")
@require_login_role("faculty")
def export_analytics(fmt):
    # Reuse attendance CSV for all for now
    return export_attendance_csv()


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
