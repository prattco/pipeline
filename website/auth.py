# auth.py



import pandas as pd
import numpy as np
import io
import secrets
import urllib.parse
from . import db   ##means from __init__.py import db
from .models import User
from . import azurecred
from .lib.Mailer import send_email
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, session
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import create_engine,text, event, exc
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired
from wtforms import SubmitField

class InfoForm(FlaskForm):
    startdate = DateField('Start Date', format='%Y-%m-%d',validators=(DataRequired(),))
    enddate = DateField('End Date', format='%Y-%m-%d',validators=(DataRequired(),))
    submit = SubmitField('Submit')

auth = Blueprint('auth', __name__)

params = urllib.parse.quote_plus(
    f"DRIVER={{{azurecred.AZDBDRIVER}}};"
    f"SERVER={azurecred.AZDBSERVER};"
    f"DATABASE={azurecred.AZDBNAME};"
    f"UID={azurecred.AZDBUSER};"
    f"PWD={azurecred.AZDBPW};"
)
dsn = f"mssql+pyodbc:///?odbc_connect={params}"

engine = create_engine(dsn, pool_recycle=3600, pool_pre_ping=True)
conn = engine.connect()


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    if executemany:
        cursor.fast_executemany = True

# Read the SQL query from the file

# pipe line
with open('website/query/pline.sql', 'r') as qs:
    qrys = qs.read()
    result = conn.execute(qrys)
    df = result.fetchall()

dfp = pd.DataFrame(df, columns=result.keys()).sort_values(by=['id'])

with open('website/query/pline_lg.sql', 'r') as qs:
    qrys = qs.read()
    result = conn.execute(qrys)
    df = result.fetchall()

dfp_lg = pd.DataFrame(df, columns=result.keys()).sort_values(by=['id'])


# pipe line item
with open('website/query/pitem.sql', 'r') as qs:
    qrys = qs.read()
    result = conn.execute(qrys)
    df = result.fetchall()

dfi = pd.DataFrame(df, columns=result.keys()).sort_values(by=['pipe_line_id'])

with open('website/query/pitem_lg.sql', 'r') as qs:
    qrys = qs.read()
    result = conn.execute(qrys)
    df = result.fetchall()

dfi_lg = pd.DataFrame(df, columns=result.keys()).sort_values(by=['pipe_line_id'])

# Add this function to handle the operational errors and redirect the user
@auth.errorhandler(exc.OperationalError)
def handle_operational_error(error):
    # Redirect the user to a different page (e.g., home page) when the connection drops
    return redirect(url_for('views.home'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        company_name = request.form.get('companyName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            hashed_password = generate_password_hash(password1)
            new_user = User(email=email, first_name=first_name, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            # Send welcome email
            subject = "Welcome to Prattco Pipeline site!"
            body = ("Welcome to Prattco Pipeline stie!\n"
                    "Please contact the Site Admin (it@prattco.com)\n" 
                    "with your name, title, email, and company name, \n"
                    "so we can assign the right permission for you.")

            send_email(subject, body, email)

            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)

# change_password route
@auth.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        if 'verification_code' in session:
            verification_code = session['verification_code']
            session.pop('verification_code', None)
            # Check if the entered verification code matches the generated one
            entered_code = request.form.get('verification_code')
            if entered_code != verification_code:
                flash('Incorrect verification code.', category='error')
                return redirect(url_for('auth.change_password'))

            # Get the user based on the provided email
            email = session.get('reset_email')
            session.pop('reset_email', None)
            user = User.query.filter_by(email=email).first()
            if user:
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                if new_password == confirm_password:
                    # Update user's password in the database
                    user.password = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password updated successfully!', category='success')
                    return redirect(url_for('views.home'))  # Redirect to views.home
                else:
                    flash('New password and confirm password do not match.', category='error')
            else:
                flash('User not found.', category='error')
                return redirect(url_for('auth.login'))
        else:
            # Render the change_password.html template
            return render_template("change_password.html", user=current_user if current_user.is_authenticated else None)

    # If the request method is GET, render the change_password.html template
    return render_template("change_password.html", user=current_user if current_user.is_authenticated else None)

# request_verification_code route
@auth.route('/request-verification-code', methods=['POST'])
def request_verification_code():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a random verification code
            verification_code = secrets.token_hex(6)
            session['verification_code'] = verification_code
            session['reset_email'] = email

            # Send the verification code to the user's email
            send_email('Password Reset Verification Code', f'Your verification code is: {verification_code}', email)
            flash('A verification code has been sent to your email.', category='success')
        else:
            flash('User not found.', category='error')
    return redirect(url_for('auth.change_password'))


@auth.route('/report', methods=['GET', 'POST'])
@login_required
def pline():
    customer = str(current_user.first_name)
    if request.method == 'POST':
        if customer == 'ALL':
            data = dfp.copy() # important to copy so original df is not altered.
        elif customer == 'LG':
            data = dfp_lg.copy() #important to copy and lowercase for comparison.
        else:
            data = dfp[dfp['shared'].astype(str).str.lower() == ''].copy()
            
        titles = data.columns.tolist()
        titles_length = len(titles)
        return render_template("pline.html", tables=[data.to_html(index=False, header=True)],
                               titles=data.columns.values, titles_length=titles_length,
                               row_data=list(data.values.tolist()), user=current_user)
    return render_template("pline.html", user=current_user)

@auth.route('/download', methods=['POST'])
@login_required
def download():
    customer = str(current_user.first_name)
    if customer == 'ALL':
        data1 = dfp.copy()
        data2 = dfi.copy()
    elif customer == 'LG':
        data1 = dfp_lg.copy()
        data2 = dfi_lg.copy()
    else:
        data1 = dfp[dfp['shared'].astype(str).str.lower() == ''].copy()
        data2 = dfi[dfi['shared'].astype(str).str.lower() == ''].copy()

    # ==============================================================================
    # FIX: Strip timezone info from all datetime columns before export
    # ==============================================================================
    
    # Clean data1 (pipe_line)
    for col in data1.select_dtypes(include=['datetime', 'datetimetz']).columns:
        data1[col] = data1[col].dt.tz_localize(None)

    # Clean data2 (notes)
    for col in data2.select_dtypes(include=['datetime', 'datetimetz']).columns:
        data2[col] = data2[col].dt.tz_localize(None)

    # ==============================================================================

    # Create an Excel writer
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='openpyxl') as writer: 
        data1.to_excel(writer, sheet_name='pipe_line', index=False)
        data2.to_excel(writer, sheet_name='notes', index=False)

    excel_io.seek(0) 

    return send_file(excel_io, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name='pipeline.xlsx', as_attachment=True)
