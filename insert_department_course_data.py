#!/usr/bin/env python3
"""
Script to insert department and course data into the FaceCheck database
Based on the options in the registration form
"""

import sqlite3
import os
from datetime import datetime

def get_database_path():
    """Get the database path"""
    # Check if instance folder exists
    if os.path.exists("instance/facerecognition.db"):
        return "instance/facerecognition.db"
    elif os.path.exists("facerecognition.db"):
        return "facerecognition.db"
    else:
        raise FileNotFoundError("Database file not found. Please ensure the database exists.")

def insert_departments(cursor):
    """Insert department data"""
    print("📚 Inserting departments...")
    
    departments = [
        (1, 'College of Computer Studies'),
        (2, 'College of Engineering'),
        (3, 'College of Business & Management'),
        (4, 'College of Arts & Sciences'),
        (5, 'College of Nursing'),
        (6, 'College of Education'),
        (7, 'College of Medicine'),
        (8, 'College of Architecture'),
        (9, 'College of Tourism & Hospitality'),
        (10, 'College of Communication')
    ]
    
    for dept_id, dept_name in departments:
        try:
            cursor.execute(
                "INSERT INTO department (dept_id, dept_name) VALUES (?, ?)",
                (dept_id, dept_name)
            )
            print(f"   ✅ {dept_id}: {dept_name}")
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                print(f"   ⚠️  {dept_id}: {dept_name} (already exists)")
            else:
                print(f"   ❌ {dept_id}: {dept_name} - Error: {e}")
    
    print(f"📊 Total departments: {len(departments)}")

def insert_courses(cursor):
    """Insert course data"""
    print("\n🎓 Inserting courses...")
    
    courses = [
        # CCS - College of Computer Studies
        (1, 'Bachelor of Science in Computer Science'),
        (2, 'Bachelor of Science in Information Technology'),
        (3, 'Bachelor of Science in Information Systems'),
        (4, 'Bachelor of Science in Computer Science (Artificial Intelligence)'),
        (5, 'Bachelor of Science in Computer Science (Software Engineering)'),
        
        # COE - College of Engineering
        (6, 'Bachelor of Science in Civil Engineering'),
        (7, 'Bachelor of Science in Electrical Engineering'),
        (8, 'Bachelor of Science in Mechanical Engineering'),
        (9, 'Bachelor of Science in Industrial Engineering'),
        (10, 'Bachelor of Science in Chemical Engineering'),
        (11, 'Bachelor of Science in Computer Engineering'),
        (12, 'Bachelor of Science in Electronics Engineering'),
        (13, 'Bachelor of Science in Civil Engineering (Structural)'),
        (14, 'Bachelor of Science in Civil Engineering (Water Resources)'),
        
        # CBM - College of Business & Management
        (15, 'Bachelor of Science in Business Administration'),
        (16, 'Bachelor of Science in Accountancy'),
        (17, 'Bachelor of Science in Management Accounting'),
        (18, 'Bachelor of Science in Business Administration (Marketing)'),
        (19, 'Bachelor of Science in Business Administration (Finance)'),
        (20, 'Bachelor of Science in Business Administration (Human Resource Management)'),
        (21, 'Bachelor of Science in Business Administration (Operations Management)'),
        (22, 'Bachelor of Science in Business Administration (International Business)'),
        
        # CAS - College of Arts & Sciences
        (23, 'Bachelor of Science in Mathematics'),
        (24, 'Bachelor of Science in Psychology'),
        (25, 'Bachelor of Science in Biology'),
        (26, 'Bachelor of Science in Chemistry'),
        (27, 'Bachelor of Science in Physics'),
        (28, 'Bachelor of Science in Statistics'),
        (29, 'Bachelor of Science in Mathematics (Statistics)'),
        (30, 'Bachelor of Science in Psychology (Clinical)'),
        (31, 'Bachelor of Science in Biology (Microbiology)'),
        
        # CON - College of Nursing
        (32, 'Bachelor of Science in Nursing'),
        
        # COED - College of Education
        (33, 'Bachelor of Secondary Education'),
        (34, 'Bachelor of Elementary Education'),
        (35, 'Bachelor of Secondary Education (Mathematics)'),
        (36, 'Bachelor of Secondary Education (English)'),
        (37, 'Bachelor of Secondary Education (Science)'),
        (38, 'Bachelor of Secondary Education (Social Studies)'),
        (39, 'Bachelor of Elementary Education (General Education)'),
        (40, 'Bachelor of Elementary Education (Special Education)'),
        
        # COM - College of Medicine
        (41, 'Doctor of Medicine'),
        (42, 'Bachelor of Science in Pharmaceutical Sciences'),
        (43, 'Bachelor of Science in Medical Technology'),
        (44, 'Bachelor of Science in Radiologic Technology'),
        
        # COA - College of Architecture
        (45, 'Bachelor of Science in Architecture'),
        (46, 'Bachelor of Science in Interior Design'),
        (47, 'Bachelor of Science in Urban Design'),
        
        # COT - College of Tourism & Hospitality
        (48, 'Bachelor of Science in Tourism Management'),
        (49, 'Bachelor of Science in Hospitality Management'),
        (50, 'Bachelor of Science in Tourism Management (Travel Management)'),
        (51, 'Bachelor of Science in Hospitality Management (Hotel & Restaurant Management)'),
        
        # COC - College of Communication
        (52, 'Bachelor of Science in Communication'),
        (53, 'Bachelor of Science in Journalism'),
        (54, 'Bachelor of Science in Broadcasting'),
        (55, 'Bachelor of Science in Communication (Public Relations)')
    ]
    
    for course_id, course_name in courses:
        try:
            cursor.execute(
                "INSERT INTO course (course_id, course_name) VALUES (?, ?)",
                (course_id, course_name)
            )
            print(f"   ✅ {course_id:2d}: {course_name}")
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                print(f"   ⚠️  {course_id:2d}: {course_name} (already exists)")
            else:
                print(f"   ❌ {course_id:2d}: {course_name} - Error: {e}")
    
    print(f"📊 Total courses: {len(courses)}")

def main():
    """Main function"""
    print("�� FaceCheck Database Data Insertion")
    print("=" * 50)
    
    try:
        # Get database path
        db_path = get_database_path()
        print(f"�� Database: {db_path}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Insert departments first
        insert_departments(cursor)
        
        # Insert courses
        insert_courses(cursor)
        
        # Commit changes
        conn.commit()
        print("\n✅ All data inserted successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM department")
        dept_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM course")
        course_count = cursor.fetchone()[0]
        
        print(f"\n📊 Database Summary:")
        print(f"   • Departments: {dept_count}")
        print(f"   • Courses: {course_count}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("💡 Please ensure the database file exists and run this script from the project root.")
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()
            print("\n🔒 Database connection closed.")

if __name__ == "__main__":
    main()
