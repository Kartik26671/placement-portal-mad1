# Placement Portal Web Application

## Overview

The **Placement Portal Web Application** is a web-based system designed to manage placement activities between **students, companies, and the institute placement cell**.

The application provides a centralized platform where companies can create placement drives, students can apply to them, and administrators can monitor and manage the entire recruitment workflow.

The system is built using the **Flask web framework**, **SQLite database**, and **Bootstrap-based UI**.

---

## Features

### Admin

* View overall system dashboard
* Approve or reject company registrations
* Approve or reject placement drives
* View students, companies, drives, and applications
* Monitor placement activity

### Company

* Register and create company profile
* Login after admin approval
* Create and manage placement drives
* View applicants for each drive
* Review student resumes
* Update application status (Applied / Shortlisted / Selected / Rejected)

### Student

* Register and create student profile
* Upload resume
* View available placement drives
* Apply for drives
* Track application status

---

## Technology Stack

Backend:

* Flask (Python Web Framework)

Database:

* SQLite

Frontend:

* HTML
* Bootstrap
* Jinja2 Templates

Other Tools:

* Git & GitHub (version control)
* Google Drive (video demo hosting)

---

## Database Structure

The system uses four main database tables:

### Users

Stores login credentials and roles (Admin, Company, Student).

### Company Profiles

Contains company information such as:

* Company Name
* HR Contact
* Website
* Approval Status

### Drives

Stores placement drive details including:

* Job Title
* Description
* Eligibility
* Application Deadline
* Status

### Applications

Tracks student applications to drives including:

* Student ID
* Drive ID
* Application Date
* Status

---

## Project Structure

```
MAD1_PROJECT
│
├── app.py                  # Main Flask application
├── placement.db            # SQLite database
├── seed_data.py            # Script to populate demo data
├── update_demo_data.py     # Script to update sample data
├── README.md               # Project documentation
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── resumes/
│       └── sample resumes
│
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── company_dashboard.html
    ├── student_dashboard.html
    └── other templates
```

---

## How to Run the Project

### 1. Clone the repository

```
git clone https://github.com/Kartik26671/placement-portal-mad1
```

### 2. Navigate to project folder

```
cd placement-portal-mad1
```

### 3. Install dependencies

```
pip install flask
```

### 4. Run the application

```
python app.py
```

### 5. Open in browser

```
http://127.0.0.1:5000
```

---

## Demo Video

The project demonstration video is available at:

Google Drive Link:
https://drive.google.com/file/d/1Ctw0Tl8c4ZFAiWWuc5RQBLW4idzP7Eqw/view?usp=drive_link

## Author

**Kartik Vishwakarma**
IIT Madras – BS in Data Science
Course: Modern Application Development I
