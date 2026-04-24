# QuoteRequest.py

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import html5
from wtforms import HiddenField, IntegerField, StringField, BooleanField, SelectField, TextAreaField, FieldList, FormField, validators, ValidationError
from .. import db
from sqlalchemy import text

from ..models import QuoteRequest, QuoteRequestItem

class QuoteRequestItemForm(FlaskForm):
    id = HiddenField()
    quote_request_id = HiddenField()
    item_line = IntegerField("Item Line")
    material = StringField("Material",validators=[DataRequired()])
    eau = IntegerField("EAU")
    vendor = StringField("Vendor",validators=[DataRequired()])
    incoterm = StringField("Price Term",validators=[DataRequired()])
    incoterm_location = StringField("Location",validators=[DataRequired()])
    target_price = IntegerField("Target Price",validators=[DataRequired()])
    note = TextAreaField("Note")

    class Meta:
        csrf = False

class QuoteRequestForm(FlaskForm):
    id = HiddenField()
    requester = StringField("Requester",validators=[DataRequired()])
    customer = StringField("Company Name",validators=[DataRequired()])
    status = SelectField("Status", 
                        choices=[('Customer', 'Customer'), 
                                 ('Prospect', 'Prospect'),
                                 ], 
                        validators=[DataRequired()])

    location = StringField("MF Location",validators=[DataRequired()])
    type = SelectField("Type", 
                        choices=[('Existing', 'Existing'), 
                                 ('New Development', 'New Development'),
                                 ], 
                        validators=[DataRequired()])
    application = StringField("Application",validators=[DataRequired()])
    terms = StringField("Terms")
    remark = TextAreaField("Remark")
  
    items = FieldList(FormField(QuoteRequestItemForm, default=QuoteRequestItem), min_entries=0)




  
