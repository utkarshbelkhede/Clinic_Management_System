from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
# google api
from apiclient.discovery import build
from sqlalchemy.orm import relationship
# gettz will get the time zonE
from dateutil.tz import gettz

import pickle
import secrets
import string

#credentials = pickle.load(open("static/token.pkl", "rb"))
service = build("calendar", "v3", credentials=credentials)


# using random.choices()
# generating random strings
def id_generator():
    res = ''.join(secrets.choice(string.ascii_uppercase + string.digits)
                  for i in range(8))
    return str(res)


# google calender create event
def create_event(start_time, summary, duration=1, description=None, location=None):
    end_time = start_time + timedelta(hours=duration)

    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.strftime("%Y-%m-%dT%H:%M:%S") + '+05:30',
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            'timeZone': 'Asia/Kolkata',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 2},
            ],
        },
    }
    return service.events().insert(calendarId='primary', body=event).execute()


# create a flask instance
app = Flask(__name__)
# add database
password = 'Password'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:" + password + "@127.0.0.1:3306/clinic"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# initilize the database
db = SQLAlchemy(app)


# creating patient model
class patient(db.Model):
    __tablename__ = 'patient'
    patient_id = db.Column(db.String(10), primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    contact = db.Column(db.String(10))
    address = db.Column(db.String(200))
    appointments = relationship(
        "appointments",
        back_populates='patient',
        cascade="all, delete, delete-orphan"
    )

    # Create a string
    def __repr__(self):
        return f"Patient ID:{self.patient_id} \nFirst Name:{self.first_name} \nMiddle Name:{self.middle_name} \nLast Name:{self.last_name}"


# creating appointments model
class appointments(db.Model):
    __tablename__ = 'appointments'
    appointment_id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.patient_id'), nullable=False)
    date_time = db.Column(db.DateTime)
    patient = relationship(
        "patient",
        back_populates='appointments'
    )

    # Create a string
    def __repr__(self):
        return f"Appointment No:{self.appointment_no} \nPatient ID: {self.patient_id} \nDateTime:{self.date_time}"


# creating patient_work model
class pat_work(db.Model):
    work_id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.patient_id'), nullable=False)
    appointment_no = db.Column(db.String(10), db.ForeignKey('appointments.appointment_id'), nullable=False)
    work_done = db.Column(db.String(1000), nullable=False)
    tooth_no = db.Column(db.String(30))
    fees = db.Column(db.Float(10, 2), default=0)

    # Create a string
    def __repr__(self):
        return f"Work ID:{self.work_id} \nPatient ID:{self.patient_id} \nAppointment No:{self.appointment_no} \nFees:{self.fees}"


# creating payments model
class payments(db.Model):
    payment_id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.patient_id'), nullable=False)
    date_time = db.Column(db.DateTime)

    # Create a string
    def __repr__(self):
        return f"Patient ID:{self.patient_id} \nPayment ID:{self.payment_id} \nDateTime:{self.date_time}"


# property decorator this is route exposed on class
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        age = request.form['age']
        contact = request.form['contact']
        address = request.form['address']
        gender = request.form['gender']
        patient_id = id_generator()

        add_patient = patient(patient_id=patient_id, first_name=first_name, middle_name=middle_name,
                              last_name=last_name, age=age, contact=contact, address=address, gender=gender)
        db.session.add(add_patient)
        db.session.commit()

    all_patient = patient.query.order_by(patient.first_name).all()

    return render_template('patient.html', all_patient=all_patient)


@app.route('/search', methods=['GET', 'POST'])
def pat_search():
    search_x = request.form['live_search_patient']
    if search_x != "":
        search_char = "%{}%".format(search_x)
        all_patient = patient.query.filter(
            patient.first_name.like(search_char) + patient.middle_name.like(search_char) + patient.last_name.like(
                search_char)).all()
    else:
        all_patient = patient.query.order_by(patient.first_name).all()

    return render_template('patient.html', all_patient=all_patient)


@app.route('/delete/<patient_id>')
def delete_patient(patient_id):
    del_patient = patient.query.filter_by(patient_id=patient_id).first()
    db.session.delete(del_patient)
    db.session.commit()

    return redirect("/")


@app.route('/set_opd/<patient_id>')
def set_opd(patient_id):
    appointment_id = id_generator()
    date_time = datetime.utcnow()
    add_opd = appointments(appointment_id=appointment_id, patient_id=patient_id, date_time=date_time)

    db.session.add(add_opd)
    db.session.commit()

    eve_patient = patient.query.filter_by(patient_id=patient_id).first()
    patient_name = eve_patient.first_name + " " + eve_patient.last_name + "'s" + " " + "Appointment"
    create_event(datetime.now(tz=gettz('Asia/Kolkata')), patient_name)

    return redirect("/")


@app.route('/schedule_appointment/<patient_id>', methods=['GET', 'POST'])
def set_appointment(patient_id):
    appointment_id = id_generator()
    date_time = request.form['schedule_appointment']
    date_time = date_time + ":00"

    # convert string to date time format
    date_time = datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S")

    pat_id = patient_id
    add_opd = appointments(appointment_id=appointment_id, patient_id=pat_id, date_time=date_time)

    db.session.add(add_opd)
    db.session.commit()

    eve_patient = patient.query.filter_by(patient_id=patient_id).first()
    patient_name = eve_patient.first_name + " " + eve_patient.last_name + "'s" + " " + "Appointment"
    create_event(date_time, patient_name)

    return redirect("/")


@app.route('/update_patient/<patient_id>', methods=['GET', 'POST'])
def update_patient(patient_id):
    updt_pat = patient.query.filter_by(patient_id=patient_id).first()

    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        age = request.form['age']
        contact = request.form['contact']
        address = request.form['address']
        gender = request.form['gender']

        updt_pat.first_name = first_name
        updt_pat.middle_name = middle_name
        updt_pat.last_name = last_name
        updt_pat.age = age
        updt_pat.contact = contact
        updt_pat.address = address
        updt_pat.gender = gender

        db.session.add(updt_pat)
        db.session.commit()

        return redirect("/")

    return render_template('update_patient.html', updt_pat=updt_pat)


@app.route('/select_update_patient', methods=['GET', 'POST'])
def select_update_pat():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        view_pat = patient.query.filter_by(patient_id=patient_id).first()

    return jsonify({'htmlresponse': render_template('update_patient.html', updt_pat=view_pat)})


@app.route('/view_patient', methods=['GET', 'POST'])
def view_patient():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        view_pat = patient.query.filter_by(patient_id=patient_id).first()

    return jsonify({'htmlresponse': render_template('view_patient.html', view_pat=view_pat)})


if __name__ == "__main__":
    app.run(debug=True)  # port=8080
