from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
DATABASE = 'library.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            max_seats INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seat_number TEXT NOT NULL,
            status TEXT DEFAULT 'available'
        )
    ''')
    
    # Check if bookings table exists and has the created_at column
    cursor.execute("PRAGMA table_info(bookings)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if not columns:
        # Create bookings table if it doesn't exist
        cursor.execute('''
            CREATE TABLE bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                shift_id INTEGER,
                seat_id INTEGER,
                booking_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (shift_id) REFERENCES shifts (id),
                FOREIGN KEY (seat_id) REFERENCES seats (id)
            )
        ''')
    elif 'created_at' not in column_names:
        # Add created_at column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            # Column might already exist, ignore error
            pass
    
    # Insert sample data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM shifts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO shifts (name, start_time, end_time, max_seats) VALUES (?, ?, ?, ?)",
                      ("Morning Shift", "08:00", "12:00", 20))
        cursor.execute("INSERT INTO shifts (name, start_time, end_time, max_seats) VALUES (?, ?, ?, ?)",
                      ("Afternoon Shift", "12:00", "16:00", 20))
        cursor.execute("INSERT INTO shifts (name, start_time, end_time, max_seats) VALUES (?, ?, ?, ?)",
                      ("Evening Shift", "16:00", "20:00", 20))
        
        # Create sample seats
        for i in range(1, 21):
            cursor.execute("INSERT INTO seats (seat_number, status) VALUES (?, ?)", 
                          (f"Seat-{i}", "available"))
    
    conn.commit()
    conn.close()

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'msg': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_seats_update')
def handle_seats_update_request():
    seats_data = get_seats_data()
    emit('seats_update', seats_data)

@socketio.on('request_bookings_update')
def handle_bookings_update_request():
    bookings_data = get_bookings_data()
    emit('bookings_update', bookings_data)

@socketio.on('request_stats_update')
def handle_stats_update_request():
    stats_data = get_stats_data()
    emit('stats_update', stats_data)

# Helper functions to get data
def get_seats_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.id, s.seat_number, s.status, 
               st.name as student_name, sh.name as shift_name
        FROM seats s
        LEFT JOIN bookings b ON s.id = b.seat_id
        LEFT JOIN students st ON b.student_id = st.id
        LEFT JOIN shifts sh ON b.shift_id = sh.id
    ''')
    
    seats = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary format
    seat_list = []
    for seat in seats:
        seat_list.append({
            'id': seat[0],
            'seat_number': seat[1],
            'status': seat[2],
            'student_name': seat[3],
            'shift_name': seat[4]
        })
    
    return seat_list

def get_bookings_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get today's date for filtering
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if created_at column exists
    cursor.execute("PRAGMA table_info(bookings)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'created_at' in column_names:
        cursor.execute('''
            SELECT b.id, st.name as student_name, st.phone as student_phone, sh.name as shift_name, 
                   s.seat_number, b.booking_date, b.created_at
            FROM bookings b
            JOIN students st ON b.student_id = st.id
            JOIN shifts sh ON b.shift_id = sh.id
            JOIN seats s ON b.seat_id = s.id
            WHERE b.booking_date >= ?
            ORDER BY b.created_at DESC
        ''', (today,))
    else:
        cursor.execute('''
            SELECT b.id, st.name as student_name, st.phone as student_phone, sh.name as shift_name, 
                   s.seat_number, b.booking_date, datetime('now') as created_at
            FROM bookings b
            JOIN students st ON b.student_id = st.id
            JOIN shifts sh ON b.shift_id = sh.id
            JOIN seats s ON b.seat_id = s.id
            WHERE b.booking_date >= ?
        ''', (today,))
    
    bookings = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary format
    booking_list = []
    for booking in bookings:
        booking_list.append({
            'id': booking[0],
            'student_name': booking[1],
            'student_phone': booking[2] if booking[2] else 'N/A',
            'shift_name': booking[3],
            'seat_number': booking[4],
            'booking_date': booking[5],
            'created_at': booking[6]
        })
    
    return booking_list

def get_stats_data():
    conn = get_db_connection()
    
    # Get actual bookings count (only current date or future dates)
    today = datetime.now().strftime('%Y-%m-%d')
    bookings_result = conn.execute('''
        SELECT COUNT(*) as count 
        FROM bookings 
        WHERE booking_date >= ?
    ''', (today,)).fetchone()
    bookings_count = bookings_result[0] if bookings_result else 0
    
    # Get students with active bookings (only current date or future dates)
    students_result = conn.execute('''
        SELECT COUNT(DISTINCT st.id) as count
        FROM students st
        JOIN bookings b ON st.id = b.student_id
        WHERE b.booking_date >= ?
    ''', (today,)).fetchone()
    students_count = students_result[0] if students_result else 0
    
    seats_count = conn.execute('SELECT COUNT(*) as count FROM seats').fetchone()[0]
    shifts_count = conn.execute('SELECT COUNT(*) as count FROM shifts').fetchone()[0]
    
    # Get occupied seats (only for current or future bookings)
    occupied_result = conn.execute('''
        SELECT COUNT(DISTINCT s.id) as count
        FROM seats s
        JOIN bookings b ON s.id = b.seat_id
        WHERE b.booking_date >= ?
    ''', (today,)).fetchone()
    occupied_seats = occupied_result[0] if occupied_result else 0
    
    conn.close()
    
    return {
        'students': students_count,
        'seats': seats_count,
        'bookings': bookings_count,
        'shifts': shifts_count,
        'occupied_seats': occupied_seats,
        'available_seats': seats_count - occupied_seats
    }

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/seats')
def get_seats():
    return jsonify(get_seats_data())

@app.route('/api/shifts')
def get_shifts():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM shifts')
    shifts = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary format
    shift_list = []
    for shift in shifts:
        shift_list.append({
            'id': shift[0],
            'name': shift[1],
            'start_time': shift[2],
            'end_time': shift[3],
            'max_seats': shift[4]
        })
    
    return jsonify(shift_list)

@app.route('/api/students')
def get_students():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students')
    students = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary format
    student_list = []
    for student in students:
        student_list.append({
            'id': student[0],
            'name': student[1],
            'email': student[2],
            'phone': student[3]
        })
    
    return jsonify(student_list)

@app.route('/api/bookings')
def get_bookings():
    return jsonify(get_bookings_data())

@app.route('/api/stats')
def get_stats():
    return jsonify(get_stats_data())

@app.route('/api/book-seat', methods=['POST'])
def book_seat():
    data = request.get_json()
    student_name = data.get('student_name')
    student_email = data.get('student_email')
    student_phone = data.get('student_phone')
    shift_id = data.get('shift_id')
    seat_id = data.get('seat_id')
    booking_date = data.get('booking_date')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if student exists, if not create
        cursor.execute("SELECT id FROM students WHERE email = ?", (student_email,))
        student = cursor.fetchone()
        
        if student:
            student_id = student[0]
        else:
            cursor.execute("INSERT INTO students (name, email, phone) VALUES (?, ?, ?)",
                          (student_name, student_email, student_phone))
            student_id = cursor.lastrowid
        
        # Check if seat is already booked for this shift and date
        cursor.execute("""
            SELECT b.id 
            FROM bookings b
            JOIN seats s ON b.seat_id = s.id
            WHERE b.shift_id = ? AND b.seat_id = ? AND b.booking_date = ?
        """, (shift_id, seat_id, booking_date))
        
        existing_booking = cursor.fetchone()
        if existing_booking:
            return jsonify({'success': False, 'message': 'This seat is already booked for the selected shift and date.'})
        
        # Check if created_at column exists
        cursor.execute("PRAGMA table_info(bookings)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'created_at' in column_names:
            # Book the seat with created_at
            cursor.execute("INSERT INTO bookings (student_id, shift_id, seat_id, booking_date) VALUES (?, ?, ?, ?)",
                          (student_id, shift_id, seat_id, booking_date))
        else:
            # Book the seat without created_at (older schema)
            cursor.execute("INSERT INTO bookings (student_id, shift_id, seat_id, booking_date) VALUES (?, ?, ?, ?)",
                          (student_id, shift_id, seat_id, booking_date))
        
        # Update seat status
        cursor.execute("UPDATE seats SET status = 'occupied' WHERE id = ?", (seat_id,))
        
        conn.commit()
        
        # Emit real-time updates
        seats_data = get_seats_data()
        bookings_data = get_bookings_data()
        stats_data = get_stats_data()
        
        socketio.emit('seats_update', seats_data)
        socketio.emit('bookings_update', bookings_data)
        socketio.emit('stats_update', stats_data)
        
        # Send notification to all clients
        notification = {
            'type': 'booking',
            'message': f'New booking: {student_name} booked {seat_id} for shift {shift_id}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Seat booked successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

@app.route('/api/cancel-booking', methods=['POST'])
def cancel_booking():
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Get booking details before deleting
        cursor.execute("""
            SELECT s.id as seat_id, st.name as student_name
            FROM bookings b
            JOIN seats s ON b.seat_id = s.id
            JOIN students st ON b.student_id = st.id
            WHERE b.id = ?
        """, (booking_id,))
        
        booking = cursor.fetchone()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found.'})
        
        seat_id, student_name = booking
        
        # Delete the booking
        cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        
        # Update seat status to available
        cursor.execute("UPDATE seats SET status = 'available' WHERE id = ?", (seat_id,))
        
        conn.commit()
        
        # Emit real-time updates
        seats_data = get_seats_data()
        bookings_data = get_bookings_data()
        stats_data = get_stats_data()
        
        socketio.emit('seats_update', seats_data)
        socketio.emit('bookings_update', bookings_data)
        socketio.emit('stats_update', stats_data)
        
        # Send notification to all clients
        notification = {
            'type': 'cancellation',
            'message': f'Booking cancelled: {student_name} cancelled their booking',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Booking cancelled successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

@app.route('/api/add-shift', methods=['POST'])
def add_shift():
    data = request.get_json()
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    max_seats = data.get('max_seats')
    
    if not name or not start_time or not end_time or not max_seats:
        return jsonify({'success': False, 'message': 'All fields are required.'})
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO shifts (name, start_time, end_time, max_seats) 
            VALUES (?, ?, ?, ?)
        """, (name, start_time, end_time, int(max_seats)))
        
        conn.commit()
        
        # Emit real-time updates
        shifts_data = get_shifts_data()
        socketio.emit('shifts_update', shifts_data)
        
        # Send notification
        notification = {
            'type': 'info',
            'message': f'New shift added: {name}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Shift added successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

@app.route('/api/add-seat', methods=['POST'])
def add_seat():
    data = request.get_json()
    seat_number = data.get('seat_number')
    
    if not seat_number:
        return jsonify({'success': False, 'message': 'Seat number is required.'})
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if seat already exists
        cursor.execute("SELECT id FROM seats WHERE seat_number = ?", (seat_number,))
        existing_seat = cursor.fetchone()
        
        if existing_seat:
            return jsonify({'success': False, 'message': 'A seat with this number already exists.'})
        
        cursor.execute("""
            INSERT INTO seats (seat_number, status) 
            VALUES (?, 'available')
        """, (seat_number,))
        
        conn.commit()
        
        # Emit real-time updates
        seats_data = get_seats_data()
        stats_data = get_stats_data()
        
        socketio.emit('seats_update', seats_data)
        socketio.emit('stats_update', stats_data)
        
        # Send notification
        notification = {
            'type': 'info',
            'message': f'New seat added: {seat_number}',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Seat added successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

@app.route('/api/delete-shift', methods=['POST'])
def delete_shift():
    data = request.get_json()
    shift_id = data.get('shift_id')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if there are bookings for this shift
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE shift_id = ?", (shift_id,))
        booking_count = cursor.fetchone()[0]
        
        if booking_count > 0:
            return jsonify({'success': False, 'message': 'Cannot delete shift with existing bookings. Please cancel all bookings first.'})
        
        # Delete the shift
        cursor.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        
        conn.commit()
        
        # Emit real-time updates
        shifts_data = get_shifts_data()
        socketio.emit('shifts_update', shifts_data)
        
        # Send notification
        notification = {
            'type': 'info',
            'message': f'Shift deleted',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Shift deleted successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

@app.route('/api/delete-seat', methods=['POST'])
def delete_seat():
    data = request.get_json()
    seat_id = data.get('seat_id')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if seat is occupied
        cursor.execute("SELECT status FROM seats WHERE id = ?", (seat_id,))
        seat = cursor.fetchone()
        
        if not seat:
            return jsonify({'success': False, 'message': 'Seat not found.'})
        
        if seat[0] == 'occupied':
            return jsonify({'success': False, 'message': 'Cannot delete an occupied seat. Please cancel the booking first.'})
        
        # Check if there are bookings for this seat
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE seat_id = ?", (seat_id,))
        booking_count = cursor.fetchone()[0]
        
        if booking_count > 0:
            return jsonify({'success': False, 'message': 'Cannot delete seat with existing bookings. Please cancel all bookings first.'})
        
        # Delete the seat
        cursor.execute("DELETE FROM seats WHERE id = ?", (seat_id,))
        
        conn.commit()
        
        # Emit real-time updates
        seats_data = get_seats_data()
        stats_data = get_stats_data()
        
        socketio.emit('seats_update', seats_data)
        socketio.emit('stats_update', stats_data)
        
        # Send notification
        notification = {
            'type': 'info',
            'message': f'Seat deleted',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        socketio.emit('notification', notification)
        
        result = {'success': True, 'message': 'Seat deleted successfully!'}
    except Exception as e:
        conn.rollback()
        result = {'success': False, 'message': str(e)}
    finally:
        conn.close()
    
    return jsonify(result)

# Helper function to get shifts data
def get_shifts_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM shifts')
    shifts = cursor.fetchall()
    conn.close()
    
    # Convert to dictionary format
    shift_list = []
    for shift in shifts:
        shift_list.append({
            'id': shift[0],
            'name': shift[1],
            'start_time': shift[2],
            'end_time': shift[3],
            'max_seats': shift[4]
        })
    
    return shift_list

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, port=5003)