import sqlite3

# Check the database structure
conn = sqlite3.connect('library.db')
cursor = conn.cursor()

print("Checking bookings table structure:")
cursor.execute('PRAGMA table_info(bookings)')
columns = cursor.fetchall()
for col in columns:
    print(col)

print("\nChecking if created_at column exists:")
column_names = [column[1] for column in columns]
if 'created_at' in column_names:
    print("✓ created_at column exists")
else:
    print("✗ created_at column missing")

conn.close()