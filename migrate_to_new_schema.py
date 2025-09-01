#!/usr/bin/env python3
"""
Database Migration Script
Updates the existing FaceCheck database to match the new schema from the database dictionary.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def backup_database():
    """Create a backup of the current database"""
    db_path = "instance/facerecognition.db"
    backup_path = f"instance/facerecognition_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    else:
        print("⚠️  No existing database found to backup")
        return None

def create_new_schema():
    """Create the new database schema based on the database dictionary"""
    
    # Connect to database
    conn = sqlite3.connect("instance/facerecognition.db")
    cursor = conn.cursor()
    
    print("🔄 Creating new database schema...")
    
    # Drop existing tables if they exist (in reverse dependency order)
    tables_to_drop = [
        'event_attendance', 'event', 'attendance', 'student_class', 'class_day', 
        'class', 'faculty', 'student', 'user', 'course', 'day', 'department'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"   Dropped table: {table}")
        except Exception as e:
            print(f"   Error dropping {table}: {e}")
    
    # Create new tables based on the database dictionary
    
    # 1. Department Table
    cursor.execute("""
        CREATE TABLE department (
            dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name VARCHAR(50) NOT NULL
        )
    """)
    print("   ✅ Created department table")
    
    # 2. User Table
    cursor.execute("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            idno VARCHAR(20) NOT NULL UNIQUE,
            firstname VARCHAR(50) NOT NULL,
            lastname VARCHAR(50) NOT NULL,
            role VARCHAR(10) NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active BIT NOT NULL DEFAULT 1,
            dept_id INTEGER,
            FOREIGN KEY (dept_id) REFERENCES department(dept_id)
        )
    """)
    print("   ✅ Created user table")
    
    # 3. Course Table
    cursor.execute("""
        CREATE TABLE course (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name VARCHAR(100) NOT NULL
        )
    """)
    print("   ✅ Created course table")
    
    # 4. Student Table
    cursor.execute("""
        CREATE TABLE student (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_level VARCHAR(20) NOT NULL,
            attendance_image VARCHAR(255),
            course_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (course_id) REFERENCES course(course_id),
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    """)
    print("   ✅ Created student table")
    
    # 5. Faculty Table
    cursor.execute("""
        CREATE TABLE faculty (
            faculty_id INTEGER PRIMARY KEY AUTOINCREMENT,
            position VARCHAR(30) NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    """)
    print("   ✅ Created faculty table")
    
    # 6. Day Table
    cursor.execute("""
        CREATE TABLE day (
            day_id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_name VARCHAR(10) NOT NULL
        )
    """)
    print("   ✅ Created day table")
    
    # 7. Class Table
    cursor.execute("""
        CREATE TABLE class (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name VARCHAR(20) NOT NULL,
            edpcode VARCHAR(20) NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            room VARCHAR(10) NOT NULL,
            faculty_id INTEGER NOT NULL,
            FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
        )
    """)
    print("   ✅ Created class table")
    
    # 8. ClassDay Table (junction table for class and day)
    cursor.execute("""
        CREATE TABLE class_day (
            class_id INTEGER NOT NULL,
            day_id INTEGER NOT NULL,
            PRIMARY KEY (class_id, day_id),
            FOREIGN KEY (class_id) REFERENCES class(class_id),
            FOREIGN KEY (day_id) REFERENCES day(day_id)
        )
    """)
    print("   ✅ Created class_day table")
    
    # 9. StudentClass Table (junction table for student and class)
    cursor.execute("""
        CREATE TABLE student_class (
            studentclass_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES student(student_id),
            FOREIGN KEY (class_id) REFERENCES class(class_id)
        )
    """)
    print("   ✅ Created student_class table")
    
    # 10. Attendance Table
    cursor.execute("""
        CREATE TABLE attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_date DATETIME NOT NULL,
            attendance_status VARCHAR(10) NOT NULL,
            studentclass_id INTEGER NOT NULL,
            FOREIGN KEY (studentclass_id) REFERENCES student_class(studentclass_id)
        )
    """)
    print("   ✅ Created attendance table")
    
    # 11. Event Table
    cursor.execute("""
        CREATE TABLE event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name VARCHAR(20) NOT NULL,
            desc TEXT,
            event_date DATETIME NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            room VARCHAR(20) NOT NULL,
            faculty_id INTEGER NOT NULL,
            FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
        )
    """)
    print("   ✅ Created event table")
    
    # 12. EventAttendance Table
    cursor.execute("""
        CREATE TABLE event_attendance (
            event_attend_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_time DATETIME NOT NULL,
            status VARCHAR(10) NOT NULL,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (event_id) REFERENCES event(event_id),
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    """)
    print("   ✅ Created event_attendance table")
    
    # Insert default data
    print("🔄 Inserting default data...")
    
    # Insert default departments
    departments = [
        (1, "Computer Science"),
        (2, "Mathematics"),
        (3, "Engineering"),
        (4, "Business Administration"),
        (5, "Arts and Sciences")
    ]
    cursor.executemany("INSERT INTO department (dept_id, dept_name) VALUES (?, ?)", departments)
    print("   ✅ Inserted default departments")
    
    # Insert default days
    days = [
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday")
    ]
    cursor.executemany("INSERT INTO day (day_id, day_name) VALUES (?, ?)", days)
    print("   ✅ Inserted default days")
    
    # Insert default courses
    courses = [
        (1, "Bachelor of Science in Computer Science"),
        (2, "Bachelor of Science in Information Technology"),
        (3, "Bachelor of Science in Mathematics"),
        (4, "Bachelor of Science in Engineering"),
        (5, "Bachelor of Business Administration")
    ]
    cursor.executemany("INSERT INTO course (course_id, course_name) VALUES (?, ?)", courses)
    print("   ✅ Inserted default courses")
    
    # Insert default admin user
    from werkzeug.security import generate_password_hash
    admin_password = generate_password_hash("admin")
    
    cursor.execute("""
        INSERT INTO user (user_id, idno, firstname, lastname, role, password, created_at, is_active, dept_id)
        VALUES (1, 'admin', 'System', 'Administrator', 'admin', ?, CURRENT_TIMESTAMP, 1, 1)
    """, (admin_password,))
    print("   ✅ Inserted default admin user")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("✅ New database schema created successfully!")

def migrate_existing_data():
    """Migrate data from old schema to new schema if backup exists"""
    backup_files = [f for f in os.listdir("instance") if f.startswith("facerecognition_backup_")]
    
    if not backup_files:
        print("⚠️  No backup files found for data migration")
        return
    
    # Use the most recent backup
    latest_backup = sorted(backup_files)[-1]
    backup_path = f"instance/{latest_backup}"
    
    print(f"🔄 Attempting to migrate data from: {backup_path}")
    
    try:
        # Connect to backup database
        backup_conn = sqlite3.connect(backup_path)
        backup_cursor = backup_conn.cursor()
        
        # Connect to new database
        new_conn = sqlite3.connect("instance/facerecognition.db")
        new_cursor = new_conn.cursor()
        
        # Check if old tables exist in backup
        backup_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        old_tables = [row[0] for row in backup_cursor.fetchall()]
        
        migrated_count = 0
        
        # Migrate users if old user table exists
        if 'user' in old_tables:
            try:
                backup_cursor.execute("SELECT id, username, full_name, email, role, password_hash, created_at FROM user")
                old_users = backup_cursor.fetchall()
                
                for user in old_users:
                    user_id, username, full_name, email, role, password_hash, created_at = user
                    
                    # Split full_name into firstname and lastname
                    if full_name:
                        name_parts = full_name.split(' ', 1)
                        firstname = name_parts[0] if name_parts else "Unknown"
                        lastname = name_parts[1] if len(name_parts) > 1 else ""
                    else:
                        firstname = "Unknown"
                        lastname = "User"
                    
                    # Insert into new user table
                    new_cursor.execute("""
                        INSERT INTO user (user_id, idno, firstname, lastname, role, password, created_at, is_active, dept_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
                    """, (user_id, username, firstname, lastname, role, password_hash or "password", created_at))
                    
                    migrated_count += 1
                
                print(f"   ✅ Migrated {migrated_count} users")
                
            except Exception as e:
                print(f"   ⚠️  Error migrating users: {e}")
        
        # Migrate classes if old class table exists
        if 'class' in old_tables:
            try:
                backup_cursor.execute("SELECT id, code, name FROM class")
                old_classes = backup_cursor.fetchall()
                
                for class_data in old_classes:
                    class_id, code, name = class_data
                    
                    # Insert into new class table (will need faculty_id later)
                    new_cursor.execute("""
                        INSERT INTO class (class_id, class_name, edpcode, start_time, end_time, room, faculty_id)
                        VALUES (?, ?, ?, '08:00', '09:00', 'TBA', 1)
                    """, (class_id, name, code))
                
                print(f"   ✅ Migrated {len(old_classes)} classes")
                
            except Exception as e:
                print(f"   ⚠️  Error migrating classes: {e}")
        
        # Migrate attendance if old attendance table exists
        if 'attendance' in old_tables:
            try:
                backup_cursor.execute("SELECT id, student_id, class_id, ts, status FROM attendance")
                old_attendance = backup_cursor.fetchall()
                
                for attendance in old_attendance:
                    attendance_id, student_id, class_id, ts, status = attendance
                    
                    # Create student_class entry if it doesn't exist
                    new_cursor.execute("""
                        INSERT OR IGNORE INTO student_class (student_id, class_id)
                        VALUES (?, ?)
                    """, (student_id, class_id))
                    
                    # Get the studentclass_id
                    new_cursor.execute("SELECT studentclass_id FROM student_class WHERE student_id = ? AND class_id = ?", (student_id, class_id))
                    studentclass_id = new_cursor.fetchone()[0]
                    
                    # Insert into new attendance table
                    new_cursor.execute("""
                        INSERT INTO attendance (attendance_id, attendance_date, attendance_status, studentclass_id)
                        VALUES (?, ?, ?, ?)
                    """, (attendance_id, ts, status, studentclass_id))
                
                print(f"   ✅ Migrated {len(old_attendance)} attendance records")
                
            except Exception as e:
                print(f"   ⚠️  Error migrating attendance: {e}")
        
        backup_conn.close()
        new_conn.commit()
        new_conn.close()
        
        print("✅ Data migration completed!")
        
    except Exception as e:
        print(f"❌ Error during data migration: {e}")

def main():
    """Main migration function"""
    print("🚀 Starting FaceCheck Database Migration")
    print("=" * 50)
    
    # Ensure instance directory exists
    os.makedirs("instance", exist_ok=True)
    
    # Step 1: Backup existing database
    backup_path = backup_database()
    
    # Step 2: Create new schema
    create_new_schema()
    
    # Step 3: Migrate existing data if backup exists
    if backup_path:
        migrate_existing_data()
    
    print("=" * 50)
    print("🎉 Migration completed successfully!")
    print("\n📋 Next steps:")
    print("1. Update your Flask models in app.py to match the new schema")
    print("2. Test the application with the new database structure")
    print("3. Update any hardcoded queries in your application")
    print("\n⚠️  Important: The old database has been backed up. Keep it safe!")

if __name__ == "__main__":
    main()
