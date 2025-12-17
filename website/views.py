# views.py

import json
import os

from .models import User, Note
from . import db

from flask import Blueprint, render_template, request, flash, jsonify, redirect
from flask_login import login_required, current_user

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.fields.html5 import DateField

from .lib.Mailer import send_email
from .lib.Extensions import prepareForm, stashFormData

import datetime

class NoteSearchForm(FlaskForm) :
    email = StringField("E-mail")
    unreplied = BooleanField("Unreplied", default=True)
    date_from = DateField('Date From', format='%Y-%m-%d')
    date_to = DateField('Date To', format='%Y-%m-%d')
    class Meta:
        csrf = False

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    search_form = prepareForm(NoteSearchForm)
    notes = getNotes(search_form)

    # return render_template("home.html", user=current_user)    
    return render_template("home.html", user=current_user, search_form=search_form, notes=notes)

def getNotes(search_form):
    notes = {}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'query', 'note.sql'), 'r') as sql:
    # with open('website/query/note.sql', 'r') as sql:
        # CORRECTION 1: Remove semicolon to allow appending "AND" clauses
        query = sql.read().replace(';', '')

        statement = None
        search = {}
      
        if current_user.first_name == "ALL":
            if search_form.email.data:
                # CORRECTION 2: Use [user_p] instead of [user]
                query += " AND [user_p].[email] LIKE :email"
                search["email"] = "%" + search_form.email.data + "%"
            if search_form.unreplied.data:
                query += " AND [note_reply].[id] IS NULL"

            if search_form.date_from.data:
                # CORRECTION 3: Use [note_p] instead of [note]
                query += " AND [note_p].[date] >= :date_from"
                search["date_from"] = search_form.date_from.data
            if search_form.date_to.data:
                # CORRECTION 3: Use [note_p] instead of [note]
                query += " AND [note_p].[date] <= :date_to"
                search["date_to"] = search_form.date_to.data + datetime.timedelta(days=1)
                
            statement = db.session.execute(query, search)
        else:
            search["user_id"] = current_user.id
            # CORRECTION 3: Use [note_p] instead of [note]
            statement = db.session.execute(query + " AND [note_p].[user_id] = :user_id", search)

        note_datas = statement.fetchall()
        for note_row in note_datas:
            if (note_row["email"] in notes) == False:
                notes[note_row["email"]] = {}
            note_dict = notes[note_row["email"]]
            if (note_row["id"] in note_dict) == False:
                note_dict[note_row["id"]] = {"id": note_row["id"], "data": note_row["data"], "reply": []}
            note_dict_data = note_dict[note_row["id"]]
            if note_row["reply_id"]:
                note_dict_data["reply"].append({"reply_id": note_row["reply_id"], "reply_data": note_row["reply_data"]})

    return notes


@views.route('/save_note', methods=['POST'])
@login_required
def save_note():
    note = request.form.get('note')  # Gets the note from the HTML

    if len(note) < 1:
        flash('Note is too short!', category='error')
    else:
        new_note = Note(data=note, user_id=current_user.id)  # Providing the schema for the note
        db.session.add(new_note)  # Adding the note to the database
        db.session.commit()

        flash('Note added!', category='success')

        # Retrieve user's company name
        company_name = current_user.company_name

        # Send email notification with company name in subject and user email in body
        subject = f'New Note Added'
        # subject = f'[{company_name}] New Note Added'
        body = f'{current_user.email} added note in Pipeline:\n {note}'
        send_email(subject, body, 'danny.yun@prattco.com')

    return redirect("/")

@views.route('/reply', methods=['POST'])
@login_required
def reply():
    search_form = NoteSearchForm(
        email=request.form.get("email"),
        unreplied=request.form.get("unreplied"),
        date_from=request.form.get("date_from"),
        date_to=request.form.get("date_to")
    )
    stashFormData(search_form)
    for key, value in request.form.items():
        if key in ["email", "unreplied", "date_from", "date_to"]:
            continue
        ref_id = key[11:]
        # Check if the reply content is empty
        if not value.strip():  # Check if the content is empty or only contains whitespace
            flash('Please add reply content before submitting.', category='error')
            return redirect("/")
        note_reply = Note(data=value, ref_id=ref_id, user_id=current_user.id)
        db.session.add(note_reply)
        db.session.commit()

        originalNote = Note.query.get(ref_id)

        originalPostEmail = originalNote.user.email
        originalPostNote = originalNote.data

        mailContent = "Original Post:\n" + originalPostNote + "\n\nReply:\n" + value
        send_email('A reply has been posted to your note.', mailContent, originalPostEmail)

        flash('Reply added', category='success')
    flash('Click the note for a reply.', category='error')
    return redirect("/")

@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})