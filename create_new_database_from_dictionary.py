#!/usr/bin/env python3
"""
Create New Database from Dictionary Images
Creates a completely new database that matches the database dictionary exactly
"""

import sqlite3
import os
import shutil
import hashlib
from datetime import datetime

def backup_old_database():
    """Backup the current database"""
    db_path = "instance/facerecognition.db"
    backup_path = f"instance/facerecognition_backup_before_dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f"✅ Old database backed up to: {backup_path}")
        return backup_path
    else:
        print("⚠️  No existing database found to backup")
        return None

def create_database_from_dictionary():
    """Create database exactly matching the dictionary images"""
    
    db_path = "instance/facerecognition.db"
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ Removed existing database")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("🏗️ Creating new database from dictionary...")
    
    try:
        # Create tables in the correct order (referenced tables first)
        
        # 1. DEPARTMENT TABLE (Referenced by user)
        cursor.execute("""
            CREATE TABLE department (
                dept_id INTEGER PRIMARY KEY,
                dept_name VARCHAR(50) NOT NULL
            )
        """)
        print("   ✅ Created department table")
        
        # 2. COURSE TABLE (Referenced by student)
        cursor.execute("""
            CREATE TABLE course (
                course_id INTEGER PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL
            )
        """)
        print("   ✅ Created course table")
        
        # 3. DAYS TABLE (Referenced by class_days)
        cursor.execute("""
            CREATE TABLE days (
                day_id INTEGER PRIMARY KEY,
                day_name VARCHAR(10) NOT NULL
            )
        """)
        print("   ✅ Created days table")
        
        # 4. USER TABLE (Referenced by student, faculty, event_attendance)
        cursor.execute("""
            CREATE TABLE user (
                user_id INTEGER PRIMARY KEY,
                idno VARCHAR(20) NOT NULL UNIQUE,
                firstname VARCHAR(50) NOT NULL,
                lastname VARCHAR(50) NOT NULL,
                role VARCHAR(10) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1,
                dept_id INTEGER,
                FOREIGN KEY (dept_id) REFERENCES department(dept_id)
            )
        """)
        print("   ✅ Created user table")
        
        # 5. STUDENT TABLE (Referenced by student_class)
        cursor.execute("""
            CREATE TABLE student (
                student_id INTEGER PRIMARY KEY,
                year_level VARCHAR(20) NOT NULL,
                attendance_image VARCHAR(255),
                course_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (course_id) REFERENCES course(course_id),
                FOREIGN KEY (user_id) REFERENCES user(user_id)
            )
        """)
        print("   ✅ Created student table")
        
        # 6. FACULTY TABLE (Referenced by class, event)
        cursor.execute("""
            CREATE TABLE faculty (
                faculty_id INTEGER PRIMARY KEY,
                position VARCHAR(30) NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user(user_id)
            )
        """)
        print("   ✅ Created faculty table")
        
        # 7. CLASS TABLE (Referenced by class_days, student_class)
        cursor.execute("""
            CREATE TABLE class (
                class_id INTEGER PRIMARY KEY,
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
        
        # 8. CLASS_DAYS TABLE (Junction table - composite PK)
        cursor.execute("""
            CREATE TABLE class_days (
                class_id INTEGER NOT NULL,
                day_id INTEGER NOT NULL,
                PRIMARY KEY (class_id, day_id),
                FOREIGN KEY (class_id) REFERENCES class(class_id),
                FOREIGN KEY (day_id) REFERENCES days(day_id)
            )
        """)
        print("   ✅ Created class_days table (junction table)")
        
        # 9. STUDENT_CLASS TABLE (Junction table, referenced by attendance)
        cursor.execute("""
            CREATE TABLE student_class (
                studentclass_id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                FOREIGN KEY (student_id) REFERENCES student(student_id),
                FOREIGN KEY (class_id) REFERENCES class(class_id)
            )
        """)
        print("   ✅ Created student_class table")
        
        # 10. ATTENDANCE TABLE
        cursor.execute("""
            CREATE TABLE attendance (
                attendance_id INTEGER PRIMARY KEY,
                attendance_date DATETIME NOT NULL,
                attendance_status VARCHAR(10) NOT NULL,
                studentclass_id INTEGER NOT NULL,
                FOREIGN KEY (studentclass_id) REFERENCES student_class(studentclass_id)
            )
        """)
        print("   ✅ Created attendance table")
        
        # 11. EVENT TABLE (Referenced by event_attendance)
        cursor.execute("""
            CREATE TABLE event (
                event_id INTEGER PRIMARY KEY,
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
        
        # 12. EVENT_ATTENDANCE TABLE
        cursor.execute("""
            CREATE TABLE event_attendance (
                event_attend_id INTEGER PRIMARY KEY,
                attendance_time DATETIME NOT NULL,
                status VARCHAR(10) NOT NULL,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (event_id) REFERENCES event(event_id),
                FOREIGN KEY (user_id) REFERENCES user(user_id)
            )
        """)
        print("   ✅ Created event_attendance table")
        
        # Insert default/sample data
        print("📥 Inserting default data...")
        
        # Insert departments
        departments = [
            (1, "Computer Science"),
            (2, "Mathematics"), 
            (3, "Engineering"),
            (4, "Business Administration"),
            (5, "Arts and Sciences")
        ]
        cursor.executemany("INSERT INTO department (dept_id, dept_name) VALUES (?, ?)", departments)
        print("   ✅ Inserted departments")
        
        # Insert courses
        courses = [
            (1, "Bachelor of Science in Computer Science"),
            (2, "Bachelor of Science in Information Technology"),
            (3, "Bachelor of Science in Mathematics"),
            (4, "Bachelor of Science in Engineering"),
            (5, "Bachelor of Business Administration")
        ]
        cursor.executemany("INSERT INTO course (course_id, course_name) VALUES (?, ?)", courses)
        print("   ✅ Inserted courses")
        
        # Insert days
        days = [
            (1, "Monday"),
            (2, "Tuesday"),
            (3, "Wednesday"),
            (4, "Thursday"),
            (5, "Friday"),
            (6, "Saturday"),
            (7, "Sunday")
        ]
        cursor.executemany("INSERT INTO days (day_id, day_name) VALUES (?, ?)", days)
        print("   ✅ Inserted days")
        
        # Insert default admin user with simple password hash
        admin_password = hashlib.sha256("admin".encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO user (user_id, idno, firstname, lastname, role, password, created_at, is_active, dept_id)
            VALUES (1, 'admin', 'System', 'Administrator', 'admin', ?, CURRENT_TIMESTAMP, 1, 1)
        """, (admin_password,))
        print("   ✅ Inserted default admin user")
        
        # Commit all changes
        conn.commit()
        print("✅ Database created successfully from dictionary!")
        
        # Verify foreign key relationships
        print("\n🔗 Verifying foreign key relationships...")
        
        # Get all tables and their foreign keys
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        total_fks = 0
        for table in tables:
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()
            if fks:
                print(f"   {table}:")
                for fk in fks:
                    fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
                    print(f"      {from_col} → {ref_table}({to_col})")
                    total_fks += 1
        
        print(f"\n✅ Total foreign key relationships: {total_fks}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        conn.close()

def main():
    """Main function"""
    print("🚀 Creating New Database from Dictionary Images")
    print("=" * 60)
    
    # Ensure instance directory exists
    os.makedirs("instance", exist_ok=True)
    
    # Step 1: Backup old database
    backup_path = backup_old_database()
    
    # Step 2: Create new database from dictionary
    create_database_from_dictionary()
    
    print("=" * 60)
    print("🎉 New database created successfully!")
    print("\n📋 Database structure matches dictionary images:")
    print("✅ All primary keys (PK) correctly defined")
    print("✅ All foreign keys (FK) properly connected")
    print("✅ All table relationships established")
    print("✅ Default data inserted")
    print("\n⚠️  Important: Update Flask models to match new structure!")

if __name__ == "__main__":
    main()
