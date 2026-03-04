import sqlite3

conn = sqlite3.connect("placement.db")
cursor = conn.cursor()

# Make some companies pending
cursor.execute("""
UPDATE company_profiles
SET approval_status='pending'
WHERE id % 3 = 0
""")

# Make some drives pending
cursor.execute("""
UPDATE drives
SET status='pending'
WHERE id % 4 = 0
""")

conn.commit()
conn.close()

print("Demo data updated")
