# Aarav Library - Seat Booking System

A web application for managing library seat bookings with shift-wise allocation. Built with HTML, Tailwind CSS, JavaScript, Python (Flask), and SQLite.

## Features

- **User Interface**:
  - Book seats for specific shifts
  - Visual seat layout with color-coded availability
  - View current bookings
  - Real-time updates using WebSockets
  - Real-time notifications
  - Dashboard statistics

- **Admin Panel**:
  - Dashboard with real-time statistics
  - Manage seats and shifts (Add, Edit, Delete)
  - View and manage all bookings
  - Cancel bookings in real-time
  - Real-time notifications

## Real-time Features

- **WebSocket Integration**: Real-time updates for seat availability, bookings, and statistics
- **Live Notifications**: Instant notifications for bookings, cancellations, and system updates
- **Auto-refresh**: Automatic data updates without manual refresh
- **Concurrent User Support**: Multiple users see the same real-time data

## New CRUD Functionality

- **Add Seats**: Create new seats in the library
- **Delete Seats**: Remove available seats (occupied seats must be cancelled first)
- **Add Shifts**: Create new time shifts for booking
- **Delete Shifts**: Remove shifts (shifts with bookings cannot be deleted)
- **Edit Functionality**: (Coming soon) Edit existing seats and shifts

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Run the Flask application:
   ```
   python app.py
   ```

2. Open your browser and go to `http://localhost:5003` for the user interface
3. For the admin panel, go to `http://localhost:5003/admin`
   - Default admin password: `admin123`

## Project Structure

```
library/
│
├── app.py              # Flask application with WebSocket support
├── requirements.txt    # Python dependencies
├── library.db          # SQLite database (created automatically)
└── templates/
    ├── index.html      # User interface with real-time features
    └── admin.html      # Admin panel with real-time features
```

## Technology Stack

- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Backend**: Python Flask with Flask-SocketIO
- **Database**: SQLite
- **Real-time Communication**: WebSocket (Socket.IO)

## Default Data

The application comes with sample data:
- 3 shifts (Morning, Afternoon, Evening)
- 20 seats (Seat-1 to Seat-20)

## API Endpoints

- `GET /api/seats` - Get all seats with status
- `GET /api/shifts` - Get all shifts
- `GET /api/students` - Get all students
- `GET /api/bookings` - Get all bookings
- `GET /api/stats` - Get system statistics
- `POST /api/book-seat` - Book a seat
- `POST /api/cancel-booking` - Cancel a booking
- `POST /api/add-shift` - Add a new shift
- `POST /api/add-seat` - Add a new seat
- `POST /api/delete-shift` - Delete a shift
- `POST /api/delete-seat` - Delete a seat

## WebSocket Events

- `seats_update` - Real-time seat status updates
- `bookings_update` - Real-time booking updates
- `stats_update` - Real-time statistics updates
- `shifts_update` - Real-time shifts updates
- `notification` - Real-time notifications
- `connect`/`disconnect` - Connection status

## Future Enhancements

- User authentication system
- Booking history with search and filter
- Email/SMS notifications
- Payment integration
- Advanced reporting and analytics
- Mobile-responsive design
- Seat reservation timer
- Multiple library branches support
- Edit functionality for shifts and seats

## License

This project is open-source and available under the MIT License.