from flask import  render_template, url_for, flash, redirect, request
from DAS.forms import (RegistrationForm, LoginForm, AppointmentForm, DoctorsRegistration, ServiceForm, RequestResetForm, ResetPasswordForm, UpdateAccountForm)
from DAS.models import User, Doctor,Patient, Service, Appointment
from flask_bcrypt import Bcrypt
from flask_login import login_user, current_user, logout_user, login_required
import uuid
import os
import secrets
from sqlalchemy.orm import joinedload
from datetime import datetime
from DAS import app, mail, db
from  flask_mail import Message

bcrypt = Bcrypt(app)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = RegistrationForm()
    if form.validate_on_submit():
        encrpted_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user_id = str(uuid.uuid4())
        user = User(id=user_id, FirstName=form.FirstName.data, LastName=form.LastName.data, phone_number = form.phone_number.data, email=form.email.data, user_type= form.user_type.data, password=encrpted_pwd)
        db.session.add(user)
        db.session.commit()
        
        if form.user_type.data == 'Patient':
            patient = Patient(Patient_id=user.id, firstName=form.FirstName.data, lastName=form.LastName.data, phone_number = form.phone_number.data, email=form.email.data, user_type= form.user_type.data)
            db.session.add(patient)
            db.session.commit()
        else:
            return redirect(url_for('doctors'))
        
        flash(f'An account has been created for {form.FirstName.data} you can now log in' , 'success')
        return redirect(url_for('login'))
    return render_template('registration.html',title='register', form=form)

@app.route('/doctors_registration', methods=['GET', 'POST'])
def doctors():
    form = DoctorsRegistration()
    if form.validate_on_submit():        
        doc = User.query.filter_by(email=form.email.data).first()
        validate_doc = Doctor.query.filter_by(license_number = form.license_number.data).first()
        if validate_doc:
            flash('an account with that licence number as already been created', 'danger')
            return redirect(url_for('doctors'))
        doctor = Doctor(Doctor_id=doc.id, firstName=doc.FirstName, lastName=doc.LastName, license_number=form.license_number.data, clinic_name=form.clinic_name.data, clinic_address=form.clinic_address.data, email=form.email.data, working_hours=form.working_hours.data, Short_description=form.Short_description.data, specialization=form.Specialisation.data, qualification=form.Qualification.data, profile_pic='default.jpg')
        db.session.add(doctor)
        db.session.commit()
        flash(f'Your details have been updated succesfully' , 'success')
        return redirect(url_for('login'))
        
    return render_template('doctors.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = LoginForm()
    if form.validate_on_submit():
        user =User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if user.user_type == 'Doctor':
                flash(f'Welcome Doctor {form.email.data}!', 'success')
                doctor = Doctor.query.filter_by(email = current_user.email).first()
                Services = doctor.services
                if len(Services) == 0:
                    flash(f"Doctor {current_user.FirstName} you do not have any services yet please add a service to make your profile complete", "info")
                    return redirect(url_for('service'))
            else:
                flash(f'Welcome {form.email.data}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('account'))
        else:
            flash(f'Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)


@app.route('/appointment_request', methods=['GET', 'POST'])
@login_required
def appointment():
    form = AppointmentForm()
    doctors = Doctor.query.all()
    form.email.data = current_user.email        
    return render_template('appointment.html', form=form)


@app.route('/user_account', methods=['GET', 'POST'])
def user_account():
    profile_pic = url_for('static', filename='profile_pics/' + current_user.profile_pic)
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if current_user.user_type == 'Patient':
            current_user.FirstName = form.FirstName.data
            current_user.LastName = form.LastName.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your account has been updated!', 'success')
            return redirect(url_for('account'))
    return render_template('user_account.html', profile_pic=profile_pic, user=current_user, form=form)


@app.route('/doc_services', methods=['GET', 'POST'])
def doc_services():
    doctor = Doctor.query.filter_by(email = current_user.email).first()
    services = doctor.services
    return render_template('doc_services.html', services=services, doctor=doctor)



#doc appointment email sending
def send_appointment_email(doctor, info):
    msg = Message('Appointment request',sender= 'noreply.healthconnect@gmail.com' ,recipients=[doctor.email])
    msg.body = f''' You have a new appointment request from {info['client_name']} for {info['service']} on {info['appointment_date']} at {info['appointment_time']} visit {url_for('account', _external=True)} to accept or reject the appointment request'''
    
    mail.send(msg)

def send_approved_appointment_email(user, info):
    msg = Message('Appointment request approval',sender= 'noreply.healthconnect@gmail.com' ,recipients=[user])
    msg.body = f''' your appointment request for {info['service']} on {info['appointment_date']} at {info['appointment_time']} has been approved by your doctor please visit your dashboard to view the appointment details
    
    click here to view your appointment details {url_for('account', _external=True)}'''
    
    mail.send(msg)
    
def send_rejected_appointment_email(user, info):
    msg = Message('Appointment request status',sender= 'noreply.healthconnect@gmail.com' ,recipients=[user])
    msg.body = f''' your appointment request for {info['service']} on {info['appointment_date']} at {info['appointment_time']} has been rejected by your doctor please visit {url_for('account', _external=True)} to view the appointment details'''
    
    mail.send(msg)
    
def send_cancelled_appointment_email(user, info):
    msg = Message('Appointment request cancelling',sender= 'noreply.healthconnect@gmail.com', recipients=[user])
    msg.body = f''' an appointment by {current_user.FirstName}  for {info['service']} on {info['appointment_date']} at {info['appointment_time']} has been cancelled please visit {url_for('account', _external=True)} to view the appointment details'''
    mail.send(msg)
    

#appointment and related 

@app.route('/appointment/<Doc_id>', methods=['GET', 'POST'])
@login_required
def appointment_request(Doc_id):
    doctor = Doctor.query.get_or_404(Doc_id)
    client_id = current_user.id
    form = AppointmentForm()
    form.email.data = current_user.email
    form.service.choices = [(service.service_name, service.service_name) for service in doctor.services]
    form.doctor_name.data = doctor.firstName + ' ' + doctor.lastName
    
    if form.validate_on_submit():
        appoint_id = str(uuid.uuid4())
        appointment = Appointment(appointment_id=appoint_id, Doctor_id=Doc_id, client_id= client_id, service= form.service.data, appointment_date= form.appointment_date.data, appointment_time=str(form.appointment_time.data), client_email=form.email.data)
        db.session.add(appointment)
        db.session.commit()
        flash(f'Your appointment has been scheduled succesfully an email will be sent to your doctor' , 'success')
        
        info = {'client_name': current_user.FirstName + ' ' + current_user.LastName,
                'service': form.service.data,
                'appointment_date': form.appointment_date.data, 
                'appointment_time': form.appointment_time.data}
        
        send_appointment_email(doctor , info)
        
    return render_template('appointment.html', doctor=doctor, form=form)

@app.route('/appointment_status_approve/<appointment_id>', methods=['GET', 'POST'])
def appointment_status_approve(appointment_id):
    appointments = Appointment.query.filter_by(Doctor_id = current_user.id).all()
    approved = Appointment.query.get_or_404(appointment_id)
    approved.status = 'Approved'
    db.session.commit()
    
    user = approved.client_email
      
    info = {'service': approved.service,
            'appointment_date': approved.appointment_date, 
            'appointment_time': approved.appointment_time}
    
    flash(f'Your appointment has been approved succesfully email will be send to patient' , 'info')
    send_approved_appointment_email(user, info)
    
    return render_template('account.html', appointments=appointments)

@app.route('/appointment_status_reject/<appointment_id>', methods=['GET', 'POST'])
def appointment_status_reject(appointment_id):
    appointments = Appointment.query.filter_by(Doctor_id = current_user.id).all()
    rejected = Appointment.query.get_or_404(appointment_id)
    rejected.status = 'Rejected'
    db.session.commit()  

    user = rejected.client_email 

    info = {'service': rejected.service,
            'appointment_date': rejected.appointment_date, 
            'appointment_time': rejected.appointment_time}
       
    flash(f'Your appointment has been rejected succesfully email will be send to patient' , 'info')
    
    send_rejected_appointment_email(user, info)
    

    return render_template('account.html', appointments=appointments)

@app.route('/cancel_appointment/<appointment_id>', methods=['GET', 'POST'])
def cancel_appointment(appointment_id):
    appointments = Appointment.query.filter_by(client_id = current_user.id).options(joinedload(Appointment.doctor)).all()
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'Cancelled'
    db.session.commit()
    flash(f'Your appointment has been cancelled succesfully' , 'success')
    
    user = appointment.doctor.email
    info = {'service': appointment.service,
            'appointment_date': appointment.appointment_date, 
            'appointment_time': appointment.appointment_time}
    
    send_cancelled_appointment_email(user, info)
    
    return render_template('account.html', appointments=appointments)

@app.route('/doctor_list', methods=['GET', 'POST'])
def doctor_list():
    doctors = Doctor.query.all()
    return render_template('doctor_list.html', doctors = doctors)

@app.route('/services', methods=['POST', 'GET'])
def service():
    form = ServiceForm()
    if form.validate_on_submit():
        flash(f'Your service "{form.services.data}" has been updated succesfully' , 'success')
        service_id  = str(uuid.uuid4())
        service = Service(service_id = service_id, doctor_id = current_user.id, service_name = form.services.data)
        db.session.add(service)
        db.session.commit()
          
    return render_template('services.html', form=form)

@app.route('/account', methods=['POST', 'GET'])
@login_required
def account():
    if current_user.user_type == 'Doctor':
        appointments = Appointment.query.filter_by(Doctor_id = current_user.id).all()
    else:
        appointments = Appointment.query.filter_by(client_id = current_user.id).all()
    return render_template('account.html', appointments=appointments, user=current_user)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    form_picture.save(picture_path)
    return picture_fn

#resetting password route 

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',sender= 'noreply.healthconnect@gmail.com' ,recipients=[user.email])
    pass

    msg.body = f'''To reset your password, visit the following link: {url_for('reset_token', token=token, _external=True)} 
    if you did not make this request then simply ignore this email and no changes will be made'''
    
    mail.send(msg)

@app.route('/reset_password', methods=['POST', 'GET'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user =User.query.filter_by(email=form.email.data).first()
        try:
            send_reset_email(user)
        except:
            flash('An error occured while sending the email', 'danger')
            return redirect(url_for('reset_request'))
        
        flash('An email has been sent with instructions to reset your password', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title ='reset password', form=form)

@app.route('/reset_password/<token>', methods=['POST', 'GET'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        encrpted_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = encrpted_pwd
        db.session.commit()
        flash(f'Your password has been updated! you can now log in' , 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title ='reset password', form=form)