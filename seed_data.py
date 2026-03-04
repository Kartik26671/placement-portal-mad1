import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("placement.db")
cursor = conn.cursor()

# -----------------------------
# Fake Students (users table)
# -----------------------------

for i in range(1, 120):

    name = f"Student{i}"
    email = f"student{i}@mail.com"
    password = "hashed_password"
    role = "student"

    cursor.execute("""
    INSERT INTO users (name,email,password,role,is_active)
    VALUES (?,?,?,?,?)
    """,(name,email,password,role,1))


# -----------------------------
# Fake Company Users
# -----------------------------

company_user_ids = []

for i in range(1,25):

    name = f"HR{i}"
    email = f"hr{i}@company.com"
    password = "hashed_password"
    role = "company"

    cursor.execute("""
    INSERT INTO users (name,email,password,role,is_active)
    VALUES (?,?,?,?,?)
    """,(name,email,password,role,1))

    company_user_ids.append(cursor.lastrowid)


# -----------------------------
# Company Profiles
# -----------------------------

company_profile_ids = []

for i,user_id in enumerate(company_user_ids):

    company_name = f"Company{i+1}"
    hr_contact = "9999999999"
    website = "https://company.com"

    cursor.execute("""
    INSERT INTO company_profiles (user_id,company_name,hr_contact,website,approval_status)
    VALUES (?,?,?,?,?)
    """,(user_id,company_name,hr_contact,website,"approved"))

    company_profile_ids.append(cursor.lastrowid)


# -----------------------------
# Drives
# -----------------------------

drive_ids = []

for i in range(1,50):

    company_id = random.choice(company_profile_ids)

    title = f"Software Engineer {i}"
    description = "Hiring developers"
    eligibility = "CSE/IT, CGPA > 7"

    deadline = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO drives (company_id,title,description,eligibility,deadline,status)
    VALUES (?,?,?,?,?,?)
    """,(company_id,title,description,eligibility,deadline,"approved"))

    drive_ids.append(cursor.lastrowid)


# -----------------------------
# Applications
# -----------------------------

student_ids = []

cursor.execute("SELECT id FROM users WHERE role='student'")
rows = cursor.fetchall()

for r in rows:
    student_ids.append(r[0])

for i in range(300):

    student_id = random.choice(student_ids)
    drive_id = random.choice(drive_ids)

    status = random.choice(["Applied","Shortlisted","Rejected","Selected"])

    applied_on = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute("""
        INSERT INTO applications (student_id,drive_id,status,applied_on)
        VALUES (?,?,?,?)
        """,(student_id,drive_id,status,applied_on))
    except:
        pass


conn.commit()
conn.close()

print("Fake data inserted successfully")