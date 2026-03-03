from flask import Flask, render_template, request, redirect, session, url_for,flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
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
   try:
      cursor.execute("ALTER TABLE users ADD COLUMN resume_path TEXT")
   except:
      pass

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

    # Clear any previous session (prevents role leakage)
    session.clear()

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return "Please enter email and password"

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        # User not found
        if user is None:
            return "Invalid credentials"

        # Incorrect password
        if not check_password_hash(user["password"], password):
            return "Invalid credentials"

        # Account deactivated
        if user["is_active"] == 0:
            return "Account is deactivated by admin"

        # Successful login
        session["user_id"] = user["id"]
        session["role"] = user["role"]

        # Explicit role-based routing
        if user["role"] == "admin":
            return redirect("/admin_dashboard")

        if user["role"] == "company":
            return redirect("/company_dashboard")

        if user["role"] == "student":
            return redirect("/student_dashboard")

        # Fallback safety (should never happen)
        session.clear()
        return "Invalid role assigned"

    return render_template("login.html")


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





@app.route("/admin_view_students")
def admin_all_students():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    if search:
        students = conn.execute("""
            SELECT * FROM users
            WHERE role='student'
            AND (name LIKE ? OR CAST(id AS TEXT) LIKE ?)
        """, (f"%{search}%", f"%{search}%")).fetchall()
    else:
        students = conn.execute("""
            SELECT * FROM users WHERE role='student'
        """).fetchall()

    conn.close()

    return render_template(
        "admin_students.html",
        students=students,
        search=search
    )




@app.route("/admin_view_drives")
def admin_view_drives():
   if "user_id" not in session or session.get("role") != "admin":
      return redirect("/login")

   search = request.args.get("search", "").strip()

   conn = get_db_connection()

   if search:
      drives = conn.execute("""
         SELECT drives.id,
                  drives.title,
                  drives.status,
                  drives.deadline,
                  users.name AS company_name
         FROM drives
         JOIN company_profiles ON drives.company_id = company_profiles.id
         JOIN users ON company_profiles.user_id = users.id
         WHERE drives.title LIKE ?
            OR users.name LIKE ?
      """, (f"%{search}%", f"%{search}%")).fetchall()
   else:
      drives = conn.execute("""
         SELECT drives.id,
                  drives.title,
                  drives.status,
                  drives.deadline,
                  users.name AS company_name
         FROM drives
         JOIN company_profiles ON drives.company_id = company_profiles.id
         JOIN users ON company_profiles.user_id = users.id
      """).fetchall()

   conn.close()

   return render_template(
      "admin_view_drives.html",
      drives=drives
   )


    

@app.route("/admin_view_students")
def admin_students():
   if "user_id" not in session or session.get("role") != "admin":
      return redirect("/login")

   search = request.args.get("search", "").strip()

   conn = get_db_connection()

   if search:
      students = conn.execute("""
         SELECT * FROM users
         WHERE role='student'
         AND (
            name LIKE ?
            OR email LIKE ?
            OR CAST(id AS TEXT) LIKE ?
         )
      """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
   else:
      students = conn.execute("""
         SELECT * FROM users WHERE role='student'
      """).fetchall()

   conn.close()

   return render_template("admin_students.html", 
                        students=students, 
                        search=search)


@app.route("/admin_toggle_student/<int:student_id>")
def admin_toggle_student(student_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    student = conn.execute(
        "SELECT is_active FROM users WHERE id=? AND role='student'",
        (student_id,)
    ).fetchone()

    if student:
        new_status = 0 if student["is_active"] == 1 else 1

        conn.execute(
            "UPDATE users SET is_active=? WHERE id=?",
            (new_status, student_id)
        )
        conn.commit()

    conn.close()
    return redirect("/admin_view_students")




@app.route("/admin_toggle_company/<int:company_id>")
def admin_toggle_company(company_id):
   if "user_id" not in session or session.get("role") != "admin":
      return redirect("/login")

   conn = get_db_connection()

   company = conn.execute(
      "SELECT is_active FROM users WHERE id=? AND role='company'",
      (company_id,)
   ).fetchone()

   if company:
      new_status = 0 if company["is_active"] == 1 else 1
      conn.execute(
         "UPDATE users SET is_active=? WHERE id=?",
         (new_status, company_id)
      )
      conn.commit()

   conn.close()
   return redirect("/admin_view_companies")




@app.route("/admin_view_companies")
def admin_view_companies():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db_connection()

    if search:
        companies = conn.execute("""
            SELECT users.id, users.name, users.email, users.is_active,
                   company_profiles.approval_status
            FROM users
            JOIN company_profiles ON users.id = company_profiles.user_id
            WHERE users.role = 'company'
            AND users.name LIKE ?
        """, (f"%{search}%",)).fetchall()
    else:
        companies = conn.execute("""
            SELECT users.id, users.name, users.email, users.is_active,
                   company_profiles.approval_status
            FROM users
            JOIN company_profiles ON users.id = company_profiles.user_id
            WHERE users.role = 'company'
        """).fetchall()

    conn.close()

    return render_template(
        "admin_companies.html",
        companies=companies,
        search=search
    )






@app.route("/admin_all_applications")
def admin_all_applications():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    applications = conn.execute("""
        SELECT 
            users.name AS student_name,
            company_users.name AS company_name,
            drives.title AS drive_title,
            applications.status,
            applications.applied_on
        FROM applications
        JOIN users ON applications.student_id = users.id
        JOIN drives ON applications.drive_id = drives.id
        JOIN company_profiles ON drives.company_id = company_profiles.id
        JOIN users AS company_users ON company_profiles.user_id = company_users.id
    """).fetchall()

    conn.close()

    return render_template("admin_all_applications.html", 
                           applications=applications)




@app.route("/approve_company/<int:user_id>")
def admin_approve_company(user_id):

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



@app.route("/admin_reject_company/<int:user_id>")
def admin_reject_company(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        UPDATE company_profiles
        SET approval_status = 'rejected'
        WHERE user_id = ?
    """, (company_id,))

    conn.commit()
    conn.close()

    return redirect("/admin_view_companies")




@app.route("/admin_reject_drive/<int:drive_id>")
def admin_reject_drive(drive_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        UPDATE drives
        SET status = 'rejected'
        WHERE id = ?
    """, (drive_id,))

    conn.commit()
    conn.close()

    return redirect("/admin_view_drives")





@app.route("/admin_activate_student/<int:user_id>")
def admin_activate_student(user_id):

   if "user_id" not in session or session.get("role") != "admin":
      return redirect("/login")

   conn = get_db_connection()

   conn.execute("""
      UPDATE users
      SET is_active = 1
      WHERE id = ?
   """, (user_id,))

   conn.commit()
   conn.close()

   flash("Student activated", "success")
   return redirect("/admin_view_students")




@app.route("/admin_deactivate_student/<int:user_id>")
def admin_deactivate_student(user_id):

    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        UPDATE users
        SET is_active = 0
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    flash("Student deactivated", "warning")
    return redirect("/admin_view_students")







@app.route("/admin_activate_company/<int:user_id>")
def admin_activate_company(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        UPDATE users
        SET is_active = 1
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    flash("Company activated successfully", "success")
    return redirect("/admin_view_companies")





@app.route("/admin_deactivate_company/<int:user_id>")
def admin_deactivate_company(user_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db_connection()

    conn.execute("""
        UPDATE users
        SET is_active = 0
        WHERE id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    flash("Company deactivated successfully", "warning")
    return redirect("/admin_view_companies")



@app.route("/edit_drive/<int:drive_id>", methods=["GET", "POST"])
def edit_drive(drive_id):
    if "user_id" not in session or session.get("role") != "company":
        return redirect("/login")

    conn = get_db_connection()

    drive = conn.execute("""
      SELECT d.*
      FROM drives d
      JOIN company_profiles cp ON d.company_id = cp.id
      WHERE d.id = ? AND cp.user_id = ?
   """, (drive_id, session["user_id"])).fetchone()

    if not drive:
        conn.close()
        return "Drive not found or unauthorized access"

    if drive["status"] == "closed":
        conn.close()
        return "Cannot edit a closed drive"

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        deadline = request.form["deadline"]

        conn.execute("""
            UPDATE drives
            SET title = ?, description = ?, deadline = ?, status = 'pending'
            WHERE id = ?
        """, (title, description, deadline, drive_id))

        conn.commit()
        conn.close()

        return redirect("/company_dashboard")

    conn.close()
    return render_template("edit_drive.html", drive=drive)







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



@app.route("/view_applicants/<int:drive_id>")
def view_applicants(drive_id):

   if "user_id" not in session or session.get("role") != "company":
      return "Unauthorized Access"

   conn = get_db_connection()

   # Verify this drive belongs to logged-in company
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
      return "Drive not found or unauthorized access"

   applicants = conn.execute("""
      SELECT applications.id AS application_id,
            applications.status,
            users.name,
            users.email,
            users.resume_path
      FROM applications
      JOIN users ON applications.student_id = users.id
      WHERE applications.drive_id = ?
   """, (drive_id,)).fetchall()

   conn.close()

   return render_template("view_applicants.html",
                        applicants=applicants)

   conn.close()

   return render_template("view_applicants.html",
                        applicants=applicants)



@app.route("/admin_approve_drive/<int:drive_id>")
def admin_approve_drive(drive_id):

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
   flash("Drive approved successfully", "success")
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

   if "user_id" not in session or session.get("role") != "student":
      return redirect("/login")

   conn = get_db_connection()

   # Checking if student is still active
   user = conn.execute(
      "SELECT is_active FROM users WHERE id=?",
      (session["user_id"],)
   ).fetchone()

   if not user or user["is_active"] == 0:
      conn.close()
      session.clear()
      return "Account has been deactivated"

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






@app.route("/student_profile", methods=["GET", "POST"])
def student_profile():
   if "user_id" not in session or session.get("role") != "student":
      return redirect("/login")

   conn = get_db_connection()

   if request.method == "POST":
      name = request.form["name"]

      file = request.files.get("resume")

      resume_path = None

      if file and file.filename != "":
         filename = f"resume_{session['user_id']}.pdf"
         save_path = os.path.join("static", filename)
         file.save(save_path)
         resume_path = save_path

         conn.execute(
               "UPDATE users SET name=?, resume_path=? WHERE id=?",
               (name, resume_path, session["user_id"])
         )
      else:
         conn.execute(
               "UPDATE users SET name=? WHERE id=?",
               (name, session["user_id"])
         )

      conn.commit()

   student = conn.execute(
      "SELECT * FROM users WHERE id=?",
      (session["user_id"],)
   ).fetchone()

   conn.close()

   return render_template("student_profile.html", student=student)



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
    return render_template("home.html")

if __name__ == "__main__":
   init_db()
   app.run(debug=True)