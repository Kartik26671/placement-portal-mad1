from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

def get_db_connection():
   conn = sqlite3.connect("placement.db")
   conn.row_factory = sqlite3.Row
   return conn



@app.route("/init_db")
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company_name TEXT,
        hr_contact TEXT,
        website TEXT,
        approval_status TEXT DEFAULT 'pending',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        title TEXT,
        description TEXT,
        eligibility TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY(company_id) REFERENCES company_profiles(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        drive_id INTEGER,
        status TEXT DEFAULT 'Applied',
        applied_on TEXT,
        UNIQUE(student_id, drive_id),
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(drive_id) REFERENCES drives(id)
    )
    """)

    conn.commit()
    conn.close()
    return "Database Created"

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (name, email, password, role))
            if role == "company":
               user_id = cursor.lastrowid
               cursor.execute("""
                  INSERT INTO company_profiles (user_id, approval_status)
                  VALUES (?, ?)
               """, (user_id, "pending"))
            conn.commit()
        except:
            return "User already exists"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin_dashboard")
            elif user["role"] == "company":
                return redirect("/company_dashboard")
            else:
                return redirect("/student_dashboard")

        return "Invalid Credentials"

    return render_template("login.html")


from werkzeug.security import generate_password_hash


@app.route("/admin_dashboard")
def admin_dashboard():

   # Checking login
   if "user_id" not in session:
      return redirect("/login")

   # Checking role
   if session.get("role") != "admin":
      return "Unauthorized Access"

   conn = get_db_connection()

   # Get pending companies
   pending_companies = conn.execute("""
      SELECT users.id, users.name, users.email
      FROM users
      JOIN company_profiles
      ON users.id = company_profiles.user_id
      WHERE company_profiles.approval_status = 'pending'
   """).fetchall()

   pending_drives = conn.execute("""
   SELECT drives.id, drives.title, users.name
   FROM drives
   JOIN company_profiles ON drives.company_id = company_profiles.id
   JOIN users ON company_profiles.user_id = users.id
   WHERE drives.status = 'pending'
   """).fetchall()


   total_students = conn.execute("""
      SELECT COUNT(*) FROM users WHERE role = 'student'
   """).fetchone()[0]

   total_companies = conn.execute("""
      SELECT COUNT(*) FROM users WHERE role = 'company'
   """).fetchone()[0]

   total_drives = conn.execute("""
      SELECT COUNT(*) FROM drives
   """).fetchone()[0]

   total_applications = conn.execute("""
      SELECT COUNT(*) FROM applications
   """).fetchone()[0]


   conn.close()

   return render_template(
      "admin_dashboard.html",
      pending_companies=pending_companies,
      pending_drives=pending_drives,
      total_students=total_students,
      total_companies=total_companies,
      total_drives=total_drives,
      total_applications=total_applications
   )





@app.route("/approve_company/<int:user_id>")
def approve_company(user_id):

   if "user_id" not in session or session.get("role") != "admin":
      return "Unauthorized Access"

   conn = get_db_connection()

   conn.execute("""
      UPDATE company_profiles
      SET approval_status = 'approved'
      WHERE user_id = ?
   """, (user_id,))

   conn.commit()
   conn.close()

   return redirect("/admin_dashboard")






@app.route("/company_dashboard")
def company_dashboard():

   if "user_id" not in session:
      return redirect("/login")

   if session.get("role") != "company":
      return "Unauthorized Access"

   conn = get_db_connection()

   # Get company profile
   company = conn.execute("""
      SELECT company_profiles.id,
            users.name,
            company_profiles.approval_status
      FROM company_profiles
      JOIN users ON company_profiles.user_id = users.id
      WHERE users.id = ?
   """, (session["user_id"],)).fetchone()

   if company["approval_status"] != "approved":
      conn.close()
      return "Waiting for Admin Approval"

   # Get drives created by this company
   drives = conn.execute("""
      SELECT drives.id,
            drives.title,
            drives.status,
            COUNT(applications.id) as applicant_count
      FROM drives
      LEFT JOIN applications ON drives.id = applications.drive_id
      WHERE drives.company_id = ?
      GROUP BY drives.id
   """, (company["id"],)).fetchall()

   conn.close()

   return render_template(
      "company_dashboard.html",
      company=company,
      drives=drives
   )





@app.route("/create_drive", methods=["GET", "POST"])
def create_drive():

   if "user_id" not in session:
      return redirect("/login")

   if session.get("role") != "company":
      return "Unauthorized Access"

   if request.method == "POST":

      title = request.form["title"]
      description = request.form["description"]
      eligibility = request.form["eligibility"]
      deadline = request.form["deadline"]

      conn = get_db_connection()

      # Get company_profile id
      company = conn.execute("""
         SELECT id FROM company_profiles
         WHERE user_id = ?
      """, (session["user_id"],)).fetchone()

      conn.execute("""
         INSERT INTO drives (company_id, title, description, eligibility, deadline, status)
         VALUES (?, ?, ?, ?, ?, ?)
      """, (company["id"], title, description, eligibility, deadline, "pending"))

      conn.commit()
      conn.close()

      return "Drive Created (Waiting for Admin Approval)"

   return render_template("create_drive.html")



@app.route("/view_applicants")
def view_applicants():

   if "user_id" not in session or session.get("role") != "company":
      return "Unauthorized Access"

   conn = get_db_connection()

   # Get company profile id
   company = conn.execute("""
      SELECT id FROM company_profiles
      WHERE user_id = ?
   """, (session["user_id"],)).fetchone()

   # Get applicants
   applicants = conn.execute("""
      SELECT applications.id,
            users.name,
            drives.title,
            applications.status
      FROM applications
      JOIN users ON applications.student_id = users.id
      JOIN drives ON applications.drive_id = drives.id
      WHERE drives.company_id = ?
   """, (company["id"],)).fetchall()

   conn.close()

   return render_template("view_applicants.html",
                        applicants=applicants)



@app.route("/approve_drive/<int:drive_id>")
def approve_drive(drive_id):

    if "user_id" not in session or session.get("role") != "admin":
        return "Unauthorized Access"

    conn = get_db_connection()

    conn.execute("""
        UPDATE drives
        SET status = 'approved'
        WHERE id = ?
    """, (drive_id,))

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")





@app.route("/close_drive/<int:drive_id>")
def close_drive(drive_id):

    if "user_id" not in session or session.get("role") != "company":
        return "Unauthorized Access"

    conn = get_db_connection()

    company = conn.execute("""
        SELECT id FROM company_profiles
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    drive = conn.execute("""
        SELECT * FROM drives
        WHERE id = ? AND company_id = ?
    """, (drive_id, company["id"])).fetchone()

    if not drive:
        conn.close()
        return "Invalid Drive"

    conn.execute("""
        UPDATE drives
        SET status = 'closed'
        WHERE id = ?
    """, (drive_id,))

    conn.commit()
    conn.close()

    return redirect("/company_dashboard")






@app.route("/update_status/<int:app_id>/<status>")
def update_status(app_id, status):

    if "user_id" not in session or session.get("role") != "company":
        return "Unauthorized Access"

    conn = get_db_connection()

    conn.execute("""
        UPDATE applications
        SET status = ?
        WHERE id = ?
    """, (status, app_id))

    conn.commit()
    conn.close()

    return redirect("/view_applicants")





@app.route("/student_dashboard")
def student_dashboard():

   if "user_id" not in session:
      return redirect("/login")

   if session.get("role") != "student":
      return "Unauthorized Access"

   conn = get_db_connection()

   approved_drives = conn.execute("""
      SELECT drives.id, drives.title, drives.description, drives.eligibility, drives.deadline, users.name
      FROM drives
      JOIN company_profiles ON drives.company_id = company_profiles.id
      JOIN users ON company_profiles.user_id = users.id
      WHERE drives.status = 'approved'
   """).fetchall()

   applications = conn.execute("""
      SELECT drives.title, applications.status
      FROM applications
      JOIN drives ON applications.drive_id = drives.id
      WHERE applications.student_id = ?
   """, (session["user_id"],)).fetchall()

   conn.close()

   return render_template("student_dashboard.html",
                        approved_drives=approved_drives,
                        applications=applications)



@app.route("/apply_drive/<int:drive_id>")
def apply_drive(drive_id):

   if "user_id" not in session or session.get("role") != "student":
      return "Unauthorized Access"

   conn = get_db_connection()

   try:
      drive = conn.execute("""
         SELECT status FROM drives WHERE id = ?
      """, (drive_id,)).fetchone()

      if drive["status"] != "approved":
         conn.close()
         return "This drive is not open for applications."


      conn.execute("""
         INSERT INTO applications (student_id, drive_id, applied_on)
         VALUES (?, ?, ?)
      """, (session["user_id"], drive_id, datetime.now().strftime("%Y-%m-%d")))
      conn.commit()
   except:
      conn.close()
      return "You have already applied to this drive."

   conn.close()

   return "Application Submitted Successfully"




@app.route("/")
def home():
    return "Placement Portal Running"

if __name__ == "__main__":
    app.run(debug=True)