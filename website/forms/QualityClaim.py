# QualityClaim.py

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import html5
from wtforms import HiddenField, IntegerField, StringField, BooleanField, SelectField, TextAreaField, FieldList, FormField, validators, ValidationError
from .. import db
from sqlalchemy import text

from ..models import QualityClaim, QualityClaimItem

class QualityClaimItemForm(FlaskForm):
    id = HiddenField()
    quality_claim_id = HiddenField()
    item_line = IntegerField("Item Line")
    date = DateField("Date", format='%Y-%m-%d',validators=[DataRequired()])
    note = TextAreaField("Note")
    # ADD validators=[Optional()] HERE
    follow_up = DateField("Follow Up", format='%Y-%m-%d', validators=[Optional()])


    class Meta:
        csrf = False

class QualityClaimForm(FlaskForm):
    id = HiddenField()
    status = SelectField("Status",
                        choices = [('Open', 'Open'),
                                   ('Closed', 'Closed')
                                        ],
                        validators=[DataRequired()])
    customer = StringField("Customer",validators=[DataRequired()])
    report_date = DateField("Report Date", format='%Y-%m-%d', validators=[DataRequired()])
    application = StringField("Application")
    model = TextAreaField("Model")
    type = StringField("Type")
    rma_no = StringField("RMA No")
    serial_no = StringField("Serial No")
    failure_loc = StringField("Failure Location")
    credit_memo = StringField("Credit Memo")
    issue = TextAreaField("Issue")
    corrective_action = TextAreaField("Corrective Action")
    closed_date = DateField("Closed Date", format='%Y-%m-%d', validators=[DataRequired()])

  
    items = FieldList(FormField(QualityClaimItemForm, default=QualityClaimItem), min_entries=0)
    # items = FieldList(FormField(QualityClaimItemForm, default=QualityClaimItem))


  
