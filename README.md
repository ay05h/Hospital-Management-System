# Hospital Management System

A web-based Hospital Management System built with Flask and PostgreSQL. It supports patient and doctor registration, appointment booking, medical records, inventory management, and basic admin features.

## Features

- User authentication for Admin, Doctor, and Patient
- Patient and Doctor registration
- Book, view, and cancel appointments
- Update patient and doctor profiles
- Change passwords
- View lab reports and prescriptions
- Admin inventory view and supplier information
- Account deactivation for patients

## Technologies

- Python 3
- Flask
- PostgreSQL
- HTML / CSS / JavaScript
- psycopg2

## Project Structure

- app.py — Main Flask application
- Home.ipynb — Database setup and example SQL for table creation
- templates/ — Jinja2 HTML templates
- static/
  - css/ — styles.css
  - js/ — app.js
- LICENSE, README.md

## Quick Start

1. Clone the repository

   ```powershell
   git clone <repo-url>
   cd "Hospital-Management-System"
   ```

2. Create and activate a virtual environment (Windows)

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # or .\venv\Scripts\activate for cmd
   ```

3. Install dependencies

   ```powershell
   pip install flask psycopg2-binary
   ```

4. Configure PostgreSQL

   - Create a database and user.
   - Run the SQL/table setup in `Home.ipynb` or execute equivalent SQL to create required tables.
   - Update database connection settings in `app.py` if necessary.

5. Run the application
   ```powershell
   python app.py
   ```
   Open http://localhost:5000 in your browser.

## Notes

- Review `Home.ipynb` for schema and example data insertion.
- Update connection credentials in `app.py` before running.
- For production, configure a proper WSGI server and secure database credentials with environment variables.

## License

This project is licensed under the MIT License. See LICENSE for details.

## Author

Ayush Kumar Rai
