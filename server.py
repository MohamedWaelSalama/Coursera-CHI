from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2004-9-27',
}

def init_mysql_database():
    """Automatically creates the MySQL database and tables if they don't exist yet."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS coursera_chi_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()

        db_config_full = DB_CONFIG.copy()
        db_config_full['database'] = 'coursera_chi_db'
        conn = mysql.connector.connect(**db_config_full)
        cursor = conn.cursor()

        # Table 1: Students
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Students (
                Student_ID VARCHAR(50) NOT NULL,
                First_Name VARCHAR(100) NOT NULL,
                Last_Name VARCHAR(100) NOT NULL,
                Email VARCHAR(150) NOT NULL,
                Password VARCHAR(255) NOT NULL,
                Academic_Year VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Student_ID),
                UNIQUE KEY uq_student_email (Email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Table 1b: Administrators
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Administrators (
                Admin_ID VARCHAR(50) NOT NULL,
                Name VARCHAR(150) NOT NULL,
                Email VARCHAR(150) NOT NULL,
                Password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Admin_ID),
                UNIQUE KEY uq_admin_email (Email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Table 2: Courses Catalog
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Courses (
                Course_Code VARCHAR(20) NOT NULL,
                Course_Name VARCHAR(150) NOT NULL,
                Credit_Hours INT NOT NULL DEFAULT 3,
                Max_Capacity INT NOT NULL DEFAULT 45,
                Day VARCHAR(20) DEFAULT 'Sunday',
                Start_Time VARCHAR(20) DEFAULT '09:00 AM',
                End_Time VARCHAR(20) DEFAULT '10:30 AM',
                Location VARCHAR(50) DEFAULT 'Lec 101',
                PRIMARY KEY (Course_Code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Table 3: Student-Course Enrollments (Junction Table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Student_Courses (
                Enrollment_ID INT AUTO_INCREMENT PRIMARY KEY,
                Student_ID VARCHAR(50) NOT NULL,
                Course_Code VARCHAR(20) NOT NULL,
                Enrolled_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID) ON DELETE CASCADE,
                FOREIGN KEY (Course_Code) REFERENCES Courses(Course_Code) ON DELETE CASCADE,
                UNIQUE KEY uq_student_course (Student_ID, Course_Code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Seed default courses into MySQL if the table is empty
        cursor.execute("SELECT COUNT(*) FROM Courses")
        count = cursor.fetchone()[0]
        if count == 0:
            default_courses = [
                ("CS201", "Data Structures & Algorithms", 3, 50, "Sunday", "09:00 AM", "10:30 AM", "Lec 212"),
                ("MATH201", "Linear Algebra", 3, 60, "Sunday", "11:00 AM", "12:30 PM", "Lec 111"),
                ("CS304", "Database Systems", 4, 30, "Tuesday", "10:00 AM", "11:30 AM", "Lec 211"),
                ("CS205", "Computer Architecture", 3, 45, "Thursday", "01:00 PM", "02:30 PM", "Lec 312")
            ]
            cursor.executemany("""
                INSERT IGNORE INTO Courses (Course_Code, Course_Name, Credit_Hours, Max_Capacity, Day, Start_Time, End_Time, Location)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, default_courses)
            print("📦 Default courses seeded into MySQL successfully!")

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ MySQL Database and all tables verified successfully!")
    except Exception as err:
        print(f"⚠️ MySQL Initialization Error: {err}")

init_mysql_database()

def get_db_connection():
    config = DB_CONFIG.copy()
    config['database'] = 'coursera_chi_db'
    return mysql.connector.connect(**config)

@app.route('/')
def serve_root():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory('.', filename)

# ==================== Authentication APIs ====================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    role = data.get('role')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if role == 'Student':
            cursor.execute("""
                INSERT INTO Students (Student_ID, First_Name, Last_Name, Email, Password, Academic_Year) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data.get('Student_ID'), data.get('First_Name'), data.get('Last_Name'),
                  data.get('Email'), data.get('Password'), data.get('Academic_Year')))
            conn.commit()
            return jsonify({"success": True, "message": "Student registered successfully!"})
        elif role == 'Administrator':
            cursor.execute("""
                INSERT INTO Administrators (Admin_ID, Name, Email, Password) 
                VALUES (%s, %s, %s, %s)
            """, (data.get('Admin_ID'), data.get('Name'), data.get('Email'), data.get('Password')))
            conn.commit()
            return jsonify({"success": True, "message": "Administrator registered successfully!"})
        return jsonify({"success": False, "message": "Invalid role specified."}), 400
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    email = data.get('Email')
    password = data.get('Password')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if role == 'Student':
            cursor.execute("SELECT * FROM Students WHERE Email = %s AND Password = %s", (email, password))
            user = cursor.fetchone()
            if user:
                return jsonify({"success": True, "message": "Login successful!", "user": user, "redirect": "Option.html"})
        elif role == 'Administrator':
            cursor.execute("SELECT * FROM Administrators WHERE Email = %s AND Password = %s", (email, password))
            user = cursor.fetchone()
            if user:
                return jsonify({"success": True, "message": "Login successful!", "user": user, "redirect": "admin.html"})

        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

# ==================== Course Management APIs ====================
@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Courses")
        return jsonify({"success": True, "courses": cursor.fetchall()})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/courses', methods=['POST'])
def add_course():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Courses (Course_Code, Course_Name, Credit_Hours, Max_Capacity, Day, Start_Time, End_Time, Location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('Course_Code'), data.get('Course_Name'), data.get('Credit_Hours', 3),
            data.get('Max_Capacity', 45), data.get('Day', 'Sunday'),
            data.get('Start_Time', '09:00 AM'), data.get('End_Time', '10:30 AM'), data.get('Location', 'Lec 101')
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Course added successfully!"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/courses/<course_code>', methods=['DELETE'])
def delete_course(course_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Courses WHERE Course_Code = %s", (course_code,))
        conn.commit()
        return jsonify({"success": True, "message": "Course deleted successfully!"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

# ==================== Student & Enrollment APIs ====================
@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Student_ID, First_Name, Last_Name, Email, Academic_Year, created_at FROM Students")
        return jsonify({"success": True, "students": cursor.fetchall()})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Students WHERE Student_ID = %s", (student_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Student deleted successfully!"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/enroll', methods=['POST'])
def enroll_course():
    data = request.json
    student_id = data.get('Student_ID')
    course_code = data.get('Course_Code')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Student_Courses (Student_ID, Course_Code) VALUES (%s, %s)", (student_id, course_code))
        conn.commit()
        return jsonify({"success": True, "message": "Course registered successfully!"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/drop', methods=['POST'])
def drop_course():
    data = request.json
    student_id = data.get('Student_ID')
    course_code = data.get('Course_Code')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Student_Courses WHERE Student_ID = %s AND Course_Code = %s", (student_id, course_code))
        conn.commit()
        return jsonify({"success": True, "message": "Course dropped successfully!"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/students/<student_id>/courses', methods=['GET'])
def get_student_enrolled_courses(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.* FROM Courses c
            JOIN Student_Courses sc ON c.Course_Code = sc.Course_Code
            WHERE sc.Student_ID = %s
        """, (student_id,))
        return jsonify({"success": True, "courses": cursor.fetchall()})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

if __name__ == '__main__':
    print("🚀 Starting Server on https://localhost:3000")
    app.run(host='0.0.0.0', port=3000, ssl_context='adhoc', debug=True)