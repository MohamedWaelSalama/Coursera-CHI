from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import mysql.connector
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'enter Your MYSQL password here',
}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "ay178538@gmail.com"
SENDER_PASSWORD = "fotwplarvdmgqlku"

def send_otp_email(receiver_email, otp_code):
    """Sends a freshly generated, unique 6-digit verification code to the user's email."""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Your Verification Code</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 40px 20px;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 480px; background: #ffffff; padding: 40px 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); text-align: center;">
            <tr>
                <td>
                    <h2 style="color: #1e293b; font-size: 24px; margin-top: 0; margin-bottom: 16px; font-weight: bold;">Verify Your Account</h2>
                    <p style="color: #475569; font-size: 15px; line-height: 1.5; margin-bottom: 24px;">
                        Enter the following verification code on the website to activate your account:
                    </p>
                    <div style="font-size: 32px; font-weight: bold; color: #3b82f6; letter-spacing: 6px; background: #f1f5f9; padding: 15px; border-radius: 8px; display: inline-block; margin-bottom: 24px;">
                        {otp_code}
                    </div>
                    <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">If you didn't request this, you can safely ignore this email.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'] = "Your Verification Code"
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")
        return False

def send_reset_email(receiver_email, token):
    reset_link = f"https://localhost:3000/api/reset-password/{token}"
    msg_body = f"Hello,\n\nPlease click on the following link to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
    msg = MIMEText(msg_body, 'plain', 'utf-8')
    msg['Subject'] = "Password Reset Request"
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"⚠️ Failed to send reset email: {e}")
        return False

def init_mysql_database():
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Students (
                Student_ID VARCHAR(50) NOT NULL,
                First_Name VARCHAR(100) NOT NULL,
                Last_Name VARCHAR(100) NOT NULL,
                Email VARCHAR(150) NOT NULL,
                Password VARCHAR(255) NOT NULL,
                Academic_Year VARCHAR(10) NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(255) DEFAULT NULL,
                reset_token VARCHAR(255) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Student_ID),
                UNIQUE KEY uq_student_email (Email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Administrators (
                Admin_ID VARCHAR(50) NOT NULL,
                Name VARCHAR(150) NOT NULL,
                Email VARCHAR(150) NOT NULL,
                Password VARCHAR(255) NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(255) DEFAULT NULL,
                reset_token VARCHAR(255) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (Admin_ID),
                UNIQUE KEY uq_admin_email (Email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

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

        # Seed default courses automatically if the table is empty
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

        conn.commit()
        cursor.close()
        conn.close()
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

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    role = data.get('role')
    email = data.get('Email')
    
    # Generates a completely new random 6-digit code dynamically on every registration request
    otp_code = str(random.randint(100000, 999999))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if role == 'Student':
            cursor.execute("""
                INSERT INTO Students (Student_ID, First_Name, Last_Name, Email, Password, Academic_Year, is_verified, verification_token) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get('Student_ID'), data.get('First_Name'), data.get('Last_Name'),
                  email, data.get('Password'), data.get('Academic_Year'), False, otp_code))
            
        elif role == 'Administrator':
            cursor.execute("""
                INSERT INTO Administrators (Admin_ID, Name, Email, Password, is_verified, verification_token) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data.get('Admin_ID'), data.get('Name'), email, data.get('Password'), False, otp_code))
        else:
            return jsonify({"success": False, "message": "Invalid role specified."}), 400
        
        conn.commit()
        
        email_sent = send_otp_email(email, otp_code)
        msg = "Registration successful! Please enter the 6-digit code sent to your email." if email_sent else "Registration successful, but failed to send email."
        
        return jsonify({"success": True, "message": msg, "email": email})

    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('Email')
    entered_otp = data.get('OTP')
    role = data.get('role')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if role == 'Student':
            cursor.execute("SELECT * FROM Students WHERE Email = %s", (email,))
            user = cursor.fetchone()
            if user and user['verification_token'] == entered_otp:
                cursor.execute("UPDATE Students SET is_verified = TRUE, verification_token = NULL WHERE Email = %s", (email,))
                conn.commit()
                return jsonify({"success": True, "redirect": "Option.html", "user": user})
        elif role == 'Administrator':
            cursor.execute("SELECT * FROM Administrators WHERE Email = %s", (email,))
            user = cursor.fetchone()
            if user and user['verification_token'] == entered_otp:
                cursor.execute("UPDATE Administrators SET is_verified = TRUE, verification_token = NULL WHERE Email = %s", (email,))
                conn.commit()
                return jsonify({"success": True, "redirect": "admin.html", "user": user})

        return jsonify({"success": False, "message": "Invalid verification code."}), 400
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
                if not user['is_verified']:
                    return jsonify({"success": False, "message": "Please verify your email first before logging in."}), 403
                return jsonify({"success": True, "message": "Login successful!", "user": user, "redirect": "Option.html"})
                
        elif role == 'Administrator':
            cursor.execute("SELECT * FROM Administrators WHERE Email = %s AND Password = %s", (email, password))
            user = cursor.fetchone()
            if user:
                if not user['is_verified']:
                    return jsonify({"success": False, "message": "Please verify your email first before logging in."}), 403
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
    """Fetches all registered students for the administrator dashboard."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Student_ID, First_Name, Last_Name, Email, Academic_Year, is_verified, created_at FROM Students")
        students = cursor.fetchall()
        return jsonify({"success": True, "students": students})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Deletes a student from the database."""
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
