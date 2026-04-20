# CommLog.py

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import html5
from wtforms import HiddenField, IntegerField, StringField, BooleanField, SelectField, TextAreaField, FieldList, FormField, validators, ValidationError
from .. import db
from sqlalchemy import text

from ..models import CommLog, CommLogItem

class CommLogItemForm(FlaskForm):
    id = HiddenField()
    comm_log_id = HiddenField()
    item_line = IntegerField("Item Line")
    date = DateField("Date", format='%Y-%m-%d',validators=[DataRequired()])
    contact = StringField("Contact")
    method = SelectField("Method", 
                        choices=[('Phone', 'Phone'), 
                                 ('Meeting', 'Meeting'),
                                 ('Online Meeting', 'Online Meeting'),
                                 ('Email', 'Email'),
                                 ], 
                        validators=[DataRequired()])
    note = TextAreaField("Note")

    class Meta:
        csrf = False

class CommLogForm(FlaskForm):
    id = HiddenField()
    status = SelectField("Status", 
                        choices=[('Active', 'Active'), 
                                 ('Inactive', 'Inactive'),
                                 ('Prospect', 'Prospect'),
                                 ], 
                        validators=[DataRequired()])


    customer = StringField("Company Name",validators=[DataRequired()])
    owner = StringField("Account Owner")
    application = StringField("Application")
    address = StringField("Address")
    city = StringField("City")
    state = StringField("State")
    zip = StringField("Zip")

    contact1 = StringField("Contact 1")
    title1 = StringField("Title 1")
    email1 = StringField("Email 1")
    phone1 = StringField("Phone 1")
    office1 = StringField("Office 1")
    cnote1 = TextAreaField("Note 1")

    contact2 = StringField("Contact 2")
    title2 = StringField("Title 2")
    email2 = StringField("Email 2")
    phone2 = StringField("Phone 2")
    office2 = StringField("Office 2")
    cnote2 = TextAreaField("Note 2")

    contact3 = StringField("Contact 3")
    title3 = StringField("Title 3")
    email3 = StringField("Email 3")
    phone3 = StringField("Phone 3")
    office3 = StringField("Office 3")
    cnote3 = TextAreaField("Note 3")

    contact4 = StringField("Contact 4")
    title4 = StringField("Title 4")
    email4 = StringField("Email 4")
    phone4 = StringField("Phone 4")
    office4 = StringField("Office 4")
    cnote4 = TextAreaField("Note 4")

    contact5 = StringField("Contact 5")
    title5 = StringField("Title 5")
    email5 = StringField("Email 5")
    phone5 = StringField("Phone 5")
    office5 = StringField("Office 5")
    cnote5 = TextAreaField("Note 5")


    launch_date = DateField("Launch Date", format='%Y-%m-%d', validators=[Optional()])

    remark = TextAreaField("Remark")
  
    items = FieldList(FormField(CommLogItemForm, default=CommLogItem), min_entries=0)




  
