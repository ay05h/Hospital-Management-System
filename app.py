import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2 import Error, IntegrityError
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
def get_db_connection():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="hospital_management",
            user="admin",
            password="ayush111"
        )
        print("Database connected successfully.")
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def home():
    return render_template('login.html')


def role_required(role):
    def wrapper(func):
        def decorated_view(*args, **kwargs):
            if session.get('role') != role:
                flash('Unauthorized access!')
                return redirect(url_for('home'))
            return func(*args, **kwargs)
        decorated_view.__name__ = func.__name__  
        return decorated_view
    return wrapper


#=====================Login  ===========================================================================
@app.route('/login', methods=['POST'])
def login():
    phone = request.form['phone']
    password = request.form['password']
    role = request.form['role']
    print(role)
    if role == 'Admin' :
        print("hello")
        if phone == "1234567899" and password == "ayush22111":
            session['role'] = 'Admin'
            print("Redirecting to Admin Landing") 
            return redirect(url_for('admin_landing'))
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed.')
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute(
        "SELECT UserID, PasswordHash FROM UserAccount WHERE PhoneNumber=%s AND Role=%s AND Status='Active'",
        (phone, role)
    )
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result and check_password_hash(result[1], password):
        session['user_id'] = result[0]
        session['role'] = role
        flash(f'Welcome, {role}!')
        if role == 'Patient':
            return redirect(url_for('patient_landing'))
        elif role == 'Doctor':
            return redirect(url_for('doctor_landing'))
        
    else:
        flash('Invalid credentials.')
        return redirect(url_for('home'))
#=====================Admin page ===========================================================================  
@app.route('/admin_landing')
@role_required('Admin')
def admin_landing():
    print(session)
    return render_template('AdminLogin.html')

#=====================Patient And Doctor Registration  ===========================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            role = request.form['role']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            dob = request.form['dob']
            gender = request.form['gender']
            email = request.form['email']
            phone = request.form['phone']
            password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

            street = request.form['street']
            city = request.form['city']
            state = request.form['state']
            zipcode = request.form['zipcode']

            insurance_provider = request.form.get('insurance_provider')
            policy_number = request.form.get('policy_number')

            connection = get_db_connection()
            if not connection:
                flash('Failed to connect to the database.')
                return redirect(url_for('home'))

            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO Address (Street, City, State, ZipCode) VALUES (%s, %s, %s, %s) RETURNING AddressID",
                (street, city, state, zipcode)
            )
            address_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO UserAccount (PhoneNumber, PasswordHash, Role) VALUES (%s, %s, %s) RETURNING UserID",
                (phone, password, role)
            )
            user_id = cursor.fetchone()[0]
            insurance_id = None
            if insurance_provider and policy_number:
                cursor.execute(
                    "INSERT INTO Insurance (InsuranceProviderName, PolicyNumber) VALUES (%s, %s) RETURNING InsuranceID",
                    (insurance_provider, policy_number)
                )
                insurance_id = cursor.fetchone()[0]

            if role == 'Patient':
                emergency_contact = request.form['emergency_contact']
                cursor.execute(
                    "INSERT INTO Patient (UserID, FirstName, LastName, DateOfBirth, Gender, AddressID, Email, EmergencyContact, InsuranceID) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (user_id, first_name, last_name, dob, gender, address_id, email, emergency_contact, insurance_id)
                )

            elif role == 'Doctor':
                specialization = request.form['specialization']
                department = request.form['department']

                if specialization:
                    cursor.execute(
                        "INSERT INTO Doctor (UserID, FirstName, LastName, SpecializationID, AddressID, Email) VALUES (%s, %s, %s, %s, %s, %s)",
                        (user_id, first_name, last_name, specialization, address_id, email)
                    )
                else:
                    flash('Invalid Specialization or Department.')
                    return redirect(url_for('register'))

            connection.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('home'))

        except IntegrityError as e:
            flash('Duplicate entry detected. Please try again.')
            connection.rollback()
        except Error as e:
            flash(f'Registration failed: {str(e)}')
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

    return render_template('register.html')
#=====================API for dynamic Specialiasation & Department ===========================================================================
@app.route('/api/departments', methods=['GET'])
def get_departments():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT DepartmentID, DepartmentName FROM Department")
    departments = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify([{'id': dept[0], 'name': dept[1]} for dept in departments])

@app.route('/api/specializations', methods=['GET'])
def get_specializations():
    department_id = request.args.get('departmentID')
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT SpecializationID, SpecializationName FROM Specialization WHERE DepartmentID=%s", (department_id,))
    specializations = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify([{'id': spec[0], 'name': spec[1]} for spec in specializations])


#=====================Patient Landing Page  ===========================================================================
@app.route('/patient_landing')
@role_required('Patient')
def patient_landing():
    user_id = session.get('user_id')
    connection = get_db_connection()
    
    if not connection:
        flash('Database connection failed.')
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute("""
        SELECT ua.UserID, ua.PhoneNumber, ua.Role, 
               p.PatientID, p.FirstName, p.LastName, p.DateOfBirth, 
               p.Gender, p.Email, p.EmergencyContact, 
               a.Street, a.City, a.State, a.ZipCode, 
               i.InsuranceProviderName, i.PolicyNumber 
        FROM UserAccount ua 
        JOIN Patient p ON ua.UserID = p.UserID 
        JOIN Address a ON p.AddressID = a.AddressID 
        LEFT JOIN Insurance i ON p.InsuranceID = i.InsuranceID 
        WHERE ua.UserID = %s
    """, (user_id,))
    
    patient_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if patient_info:
        return render_template('patient_landing.html', 
                               user_id=patient_info[0], 
                               role=patient_info[2], 
                               patient_id=patient_info[3],
                               first_name=patient_info[4], 
                               last_name=patient_info[5],
                               dob=patient_info[6], 
                               gender=patient_info[7],
                               email=patient_info[8], 
                               emergency_contact=patient_info[9],
                               address={'street': patient_info[10], 'city': patient_info[11], 'state': patient_info[12], 'zipcode': patient_info[13]},
                               insurance={'provider': patient_info[14], 'policy_number': patient_info[15]})
    else:
        flash('No patient information found.')
        return redirect(url_for('home'))

#=====================Doctor landing page ===========================================================================
@app.route('/doctor_landing')
@role_required('Doctor')
def doctor_landing():
    user_id = session.get('user_id')
    connection = get_db_connection()

    if not connection:
        flash('Database connection failed.')
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute("""
        SELECT ua.UserID, ua.PhoneNumber, ua.Role, 
               d.DoctorID, d.FirstName, d.LastName, 
               d.Email, s.SpecializationName, 
               dep.DepartmentName, 
               a.Street, a.City, a.State, a.ZipCode
        FROM UserAccount ua
        JOIN Doctor d ON ua.UserID = d.UserID
        JOIN Specialization s ON d.SpecializationID = s.SpecializationID
        JOIN Department dep ON s.DepartmentID = dep.DepartmentID
        JOIN Address a ON d.AddressID = a.AddressID
        WHERE ua.UserID = %s
    """, (user_id,))

    doctor_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if doctor_info:
        return render_template(
            'doctor_landing.html',
            user_id=doctor_info[0],
            contact_number=doctor_info[1],
            role=doctor_info[2],
            doctor_id=doctor_info[3],
            first_name=doctor_info[4],
            last_name=doctor_info[5],
            email=doctor_info[6],
            specialization=doctor_info[7],
            department=doctor_info[8],
            address={
                'street': doctor_info[9],
                'city': doctor_info[10],
                'state': doctor_info[11],
                'zipcode': doctor_info[12]
            }
        )
    else:
        flash('No doctor information found.')
        return redirect(url_for('home'))


#=====================Pateint Password change ===========================================================================
@app.route('/change_password', methods=['GET', 'POST'])
@role_required('Patient')
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user_id = session['user_id']
        if new_password != confirm_password:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT PasswordHash FROM UserAccount WHERE UserID = %s", (user_id,))
        result = cursor.fetchone()

        if not result or not check_password_hash(result[0], current_password):
            flash('Current password is incorrect!', 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('change_password'))

        new_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        cursor.execute("UPDATE UserAccount SET PasswordHash = %s WHERE UserID = %s", (new_password_hash, user_id))

        connection.commit()
        cursor.close()
        connection.close()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('patient_landing'))
    return render_template('change_password.html')

#=====================Doctor Password change ===========================================================================
@app.route('/doctor_password', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user_id = session['user_id']
        if new_password != confirm_password:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))
        connection = get_db_connection()
        print(user_id)
        cursor = connection.cursor()
        cursor.execute("SELECT PasswordHash FROM UserAccount WHERE UserID = %s", (user_id,))
        result = cursor.fetchone()

        if not result or not check_password_hash(result[0], current_password):
            flash('Current password is incorrect!', 'danger')
            cursor.close()
            connection.close()
            return redirect(url_for('change_password'))

        new_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        cursor.execute("UPDATE UserAccount SET PasswordHash = %s WHERE UserID = %s", (new_password_hash, user_id))

        connection.commit()
        cursor.close()
        connection.close()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('doctor_landing'))
    return render_template('doctor_pass.html')
#=====================Patient lab report  ===========================================================================
@app.route('/lab_reports')
@role_required('Patient')
def lab_reports():
    user_id = session['user_id']

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT PatientID FROM Patient WHERE UserID = %s", (user_id,))
    patient_id = cursor.fetchone()

    if not patient_id:
        flash("No patient record found.")
        return redirect(url_for('patient_landing'))

    patient_id = patient_id[0]

    query = """
        SELECT 
            TestDate, TestType, Results 
        FROM 
            LaboratoryTest 
        WHERE 
            PatientID = %s 
        ORDER BY 
            TestDate DESC
    """
    cursor.execute(query, (patient_id,))
    lab_reports = cursor.fetchall()

    cursor.close()
    connection.close()

    if not lab_reports:
        flash("No lab reports for you yet.")
        return render_template('lab_reports.html', reports=[])

    return render_template('lab_reports.html', reports=lab_reports)

#=====================Patient Prescription ===========================================================================

@app.route('/reports')
@role_required('Patient')
def reports():
    user_id = session['user_id']

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT PatientID FROM Patient WHERE UserID = %s", (user_id,))
    patient_id = cursor.fetchone()

    if not patient_id:
        flash("No patient record found.")
        return redirect(url_for('patient_landing'))

    patient_id = patient_id[0]

    query = """
        SELECT 
            COALESCE(m.RecordDate, p.DateIssued) AS ReportDate,
            m.Diagnosis, m.Prescription, m.TestResults,
            p.MedicationName, p.DosageInstructions
        FROM 
            MedicalRecord m
        FULL OUTER JOIN 
            PharmacyPrescription p 
        ON 
            m.AppointmentID = p.AppointmentID
        WHERE 
            m.PatientID = %s OR p.PatientID = %s
        ORDER BY 
            ReportDate DESC
    """
    cursor.execute(query, (patient_id, patient_id))
    reports = cursor.fetchall()

    cursor.close()
    connection.close()

    if not reports:
        flash("No reports for you yet.")
        return render_template('reports.html', reports=[])

    return render_template('reports.html', reports=reports)

#=====================Patient Profile Update ===========================================================================

@app.route('/update_profile', methods=['GET', 'POST'])
@role_required('Patient')
def update_profile():
    user_id = session['user_id']

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        email = request.form['email']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        emergency_contact = request.form['emergency_contact']
        insurance_provider = request.form.get('insurance_provider')
        policy_number = request.form.get('policy_number')

        try:
            connection = get_db_connection()
            if not connection:
                flash('Failed to connect to the database.')
                return redirect(url_for('patient_landing'))

            cursor = connection.cursor()

            cursor.execute("""
                UPDATE Patient
                SET FirstName = %s,
                    LastName = %s,
                    DateOfBirth = %s,
                    Gender = %s,
                    Email = %s,
                    EmergencyContact = %s
                WHERE UserID = %s
            """, (first_name, last_name, dob, gender, email, emergency_contact, user_id))

            cursor.execute("""
                UPDATE Address
                SET Street = %s,
                    City = %s,
                    State = %s,
                    ZipCode = %s
                WHERE AddressID = (
                    SELECT AddressID FROM Patient WHERE UserID = %s
                )
            """, (street, city, state, zipcode, user_id))

            if insurance_provider and policy_number:
                cursor.execute("""
                    UPDATE Insurance
                    SET InsuranceProviderName = %s,
                        PolicyNumber = %s
                    WHERE InsuranceID = (
                        SELECT InsuranceID FROM Patient WHERE UserID = %s
                    )
                """, (insurance_provider, policy_number, user_id))

            connection.commit()
            flash('Profile updated successfully!', 'success')

        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            connection.rollback()
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('patient_landing'))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            p.FirstName, p.LastName, p.DateOfBirth, p.Gender, 
            p.Email, p.EmergencyContact,
            a.Street, a.City, a.State, a.ZipCode,
            i.InsuranceProviderName, i.PolicyNumber 
        FROM UserAccount ua 
        JOIN Patient p ON ua.UserID = p.UserID 
        JOIN Address a ON p.AddressID = a.AddressID 
        LEFT JOIN Insurance i ON p.InsuranceID = i.InsuranceID 
        WHERE ua.UserID = %s
    """, (user_id,))
    
    patient_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if patient_info:
        return render_template('update_profile.html', 
                               first_name=patient_info[0], 
                               last_name=patient_info[1],
                               dob=patient_info[2], 
                               gender=patient_info[3],
                               email=patient_info[4], 
                               emergency_contact=patient_info[5],
                               address={'street': patient_info[6], 'city': patient_info[7], 'state': patient_info[8], 'zipcode': patient_info[9]},
                               insurance={'provider': patient_info[10], 'policy_number': patient_info[11]})
    else:
        flash('No patient information found.')
        return redirect(url_for('home'))
    
#=====================Patient Cancel Appointment =========================================================================== 
@app.route('/cancel_appointment', methods=['GET', 'POST'])
@role_required('Patient')
def cancel_appointment():
    user_id = session['user_id']
    if request.method == 'POST':
        appointment_id = request.form['appointment_id']
        try:
            connection = get_db_connection()
            if not connection:
                flash('Failed to connect to the database.')
                return redirect(url_for('patient_landing'))
            cursor = connection.cursor()
            cursor.execute(
            "UPDATE Appointment SET Status = 'Cancelled' WHERE AppointmentID = %s AND PatientID = (SELECT PatientID FROM Patient WHERE UserID = %s)",
            (appointment_id, user_id)
            )
            connection.commit()

        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
            return redirect(url_for('cancel_appointment'))

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT AppointmentID, DoctorID, AppointmentDate, StartTime, EndTime, Status FROM Appointment WHERE PatientID = (SELECT PatientID FROM Patient WHERE UserID = %s) AND Status = 'Scheduled'",
        (user_id,)
    )
    appointments = cursor.fetchall()
    cursor.close()
    connection.close()
    if not appointments:
        return render_template('cancel_appointment.html', appointments=[])

    return render_template('cancel_appointment.html', appointments=appointments)
 
    
#=====================Patient Book Appointment ===========================================================================

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        user_id = session['user_id']  
        doctor_id = request.json['doctor_id']
        appointment_date = request.json['appointment_date']
        start_time = request.json['start_time']
        end_time = (datetime.datetime.strptime(start_time, '%H:%M') + datetime.timedelta(minutes=30)).time()

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO Appointment (PatientID, DoctorID, AppointmentDate, StartTime, EndTime)
                VALUES ((SELECT PatientID FROM Patient WHERE UserID = %s), %s, %s, %s, %s)
            """, (user_id, doctor_id, appointment_date, start_time, end_time))
            connection.commit()
            flash('Appointment booked successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
            return redirect(url_for('book_appointment'))

    return render_template('book_appointment.html')


@app.route('/api/doctors/<int:department_id>', methods=['GET'])
def get_doctors(department_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT d.DoctorID, d.FirstName, d.LastName, s.SpecializationName
        FROM Doctor d
        JOIN Specialization s ON d.SpecializationID = s.SpecializationID
        JOIN UserAccount u ON d.UserID = u.UserID
        WHERE u.Status = 'Active' AND s.DepartmentID = %s
    """, (department_id,))
    doctors = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify([{'id': doc[0], 'name': f"{doc[1]} {doc[2]} ({doc[3]})"} for doc in doctors])

@app.route('/api/available_slots', methods=['GET'])
def get_available_slots():
    doctor_id = request.args.get('doctorID')
    appointment_date = request.args.get('date')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT StartTime, EndTime FROM Appointment 
        WHERE DoctorID = %s AND AppointmentDate = %s
    """, (doctor_id, appointment_date))

    booked_slots = cursor.fetchall()
    cursor.close()
    connection.close()

    start_of_day = datetime.datetime.combine(datetime.datetime.strptime(appointment_date, '%Y-%m-%d'), datetime.time(9, 0))
    end_of_day = datetime.datetime.combine(datetime.datetime.strptime(appointment_date, '%Y-%m-%d'), datetime.time(16, 30))

    available_slots = []
    current_time = start_of_day

    while current_time < end_of_day:
        slot_end_time = current_time + datetime.timedelta(minutes=30)
        if slot_end_time <= end_of_day:
            if not any(start <= current_time.time() < end or start < slot_end_time.time() <= end for start, end in booked_slots):
                available_slots.append(current_time.time())
        current_time += datetime.timedelta(minutes=30)

    return jsonify({'available_slots': [slot.strftime("%H:%M") for slot in available_slots]})


#=====================delete account===========================================================================
@app.route('/delete_account', methods=['POST'])
@role_required('Patient') 
def delete_account():
    user_id = session['user_id']

    connection = get_db_connection()
    if not connection:
        flash('Database connection failed.')
        return redirect(url_for('patient_landing'))

    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Appointment 
            SET Status = 'Cancelled' 
            WHERE PatientID = (
                SELECT PatientID FROM Patient WHERE UserID = %s
            ) AND Status = 'Scheduled'
        """, (user_id,))

        cursor.execute("""
            UPDATE UserAccount 
            SET Status = 'Deactivated' 
            WHERE UserID = %s
        """, (user_id,))

        connection.commit()
        flash('Your account has been deleted successfully.')
    except Error as e:
        flash(f'An error occurred: {str(e)}')
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
    session.clear()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('home'))



#=============================Doctor profile update ========================================================================================

    
@app.route('/doctor_update_profile', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_update_profile():
    user_id = session['user_id']

    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        street = request.form['street']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        specialization_id = request.form['specialization_id']

        try:
            cursor.execute(""" 
                UPDATE Doctor 
                SET FirstName = %s,
                    LastName = %s,
                    SpecializationID = %s,
                    Email = %s
                WHERE UserID = %s
            """, (first_name, last_name, specialization_id, email, user_id))

            cursor.execute("""
                UPDATE Address 
                SET Street = %s,
                    City = %s,
                    State = %s,
                    ZipCode = %s
                WHERE AddressID = (
                    SELECT AddressID FROM Doctor WHERE UserID = %s
                )
            """, (street, city, state, zipcode, user_id))

            connection.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
        return redirect(url_for('doctor_landing'))

    cursor.execute(""" 
        SELECT 
            d.FirstName, d.LastName, d.Email,
            s.SpecializationID, s.SpecializationName, 
            dept.DepartmentID, dept.DepartmentName,
            a.Street, a.City, a.State, a.ZipCode
        FROM Doctor d
        JOIN Specialization s ON d.SpecializationID = s.SpecializationID
        JOIN Department dept ON s.DepartmentID = dept.DepartmentID
        JOIN Address a ON d.AddressID = a.AddressID
        WHERE d.UserID = %s
    """, (user_id,))

    doctor_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if doctor_info:
        return render_template('doctor_update_profile.html', 
                               first_name=doctor_info[0], 
                               last_name=doctor_info[1], 
                               email=doctor_info[2],
                               specialization={
                                   'id': doctor_info[3], 
                                   'name': doctor_info[4]
                               },
                               department={
                                   'id': doctor_info[5], 
                                   'name': doctor_info[6]
                               },
                               address={
                                   'street': doctor_info[7], 
                                   'city': doctor_info[8], 
                                   'state': doctor_info[9], 
                                   'zipcode': doctor_info[10]
                               },
                               specialization_id=doctor_info[3],  
                               department_id=doctor_info[5]) 
    else:
        flash('No doctor information found.')
        return redirect(url_for('home'))
#=============================Doctor Appointment Veiw ========================================================================================
@app.route('/doctor_appointments', methods=['GET', 'POST'])
@role_required('Doctor')
def doctor_appointments():
    user_id = session['user_id']

    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == 'POST':
        filter_date = request.form['filter_date']
        cursor.execute("""
            SELECT 
                a.AppointmentID, p.FirstName, p.LastName, 
                a.AppointmentDate, a.StartTime, a.EndTime, a.Status
            FROM Appointment a
            JOIN Patient p ON a.PatientID = p.PatientID
            JOIN Doctor d ON a.DoctorID = d.DoctorID
            WHERE d.UserID = %s AND a.AppointmentDate = %s
            ORDER BY a.AppointmentDate, a.StartTime
        """, (user_id, filter_date))
    else:
        cursor.execute("""
            SELECT 
                a.AppointmentID, p.FirstName, p.LastName, 
                a.AppointmentDate, a.StartTime, a.EndTime, a.Status
            FROM Appointment a
            JOIN Patient p ON a.PatientID = p.PatientID
            JOIN Doctor d ON a.DoctorID = d.DoctorID
            WHERE d.UserID = %s AND a.Status = 'Scheduled'
            ORDER BY a.AppointmentDate, a.StartTime
        """, (user_id,))

    appointments = cursor.fetchall()
    cursor.close()
    connection.close()

    if request.method == 'POST':
        return render_template('doctor_appointments.html', appointments=appointments, filter_date=filter_date)

    return render_template('doctor_appointments.html', appointments=appointments)
#=============================Admin Inventory  ========================================================================================
@app.route('/admin_inventory', methods=['GET'])
@role_required('Admin')
def admin_inventory():
    connection = get_db_connection()
    cursor = connection.cursor()


    cursor.execute("""
        SELECT SupplierID, SupplierName, ContactPerson, PhoneNumber, Email
        FROM Supplier
    """)
    suppliers = cursor.fetchall()

    cursor.execute("""
        SELECT ItemID, ItemName, Category, QuantityInStock, ReorderLevel, SupplierID
        FROM InventoryItem
    """)
    inventory_items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('admin_inventory.html', suppliers=suppliers, inventory_items=inventory_items)



if __name__ == '__main__':
    app.run(debug=True)
