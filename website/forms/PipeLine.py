# PipeLine.py

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import html5
from wtforms import HiddenField, IntegerField, StringField, BooleanField, SelectField, TextAreaField, FieldList, FormField, validators, ValidationError
from .. import db
from sqlalchemy import text

from ..models import PipeLine, PipeLineItem

class PipeLineItemForm(FlaskForm):
    id = HiddenField()
    pipe_line_id = HiddenField()
    item_line = IntegerField("Item Line")
    date = DateField("Date", format='%Y-%m-%d',validators=[DataRequired()])
    note = TextAreaField("Note")
    # ADD validators=[Optional()] HERE
    follow_up = DateField("Follow Up", format='%Y-%m-%d', validators=[Optional()])


    class Meta:
        csrf = False

class PipeLineForm(FlaskForm):
    id = HiddenField()
    shared = SelectField("Shared", 
                        choices=[('Shared', 'Shared'), 
                                 ('Not Shared', 'Not Shared')
                                 ], 
                        validators=[DataRequired()])

    division = SelectField("Division",
                        choices=[('Comp', 'Comp'), 
                                 ('AC Comp', 'AC Comp'),
                                 ('DC Comp', 'DC Comp'),
                                 ('ECM', 'ECM'),
                                 ('MOTOR', 'MOTOR'),
                                 ('AC Comp', 'AC Comp'),
                                 ('OTHER', 'OTHER')
                                 ], 
                        validators=[DataRequired()])

    entity = SelectField("Entity",
                choices=[('LGCW', 'LGCW'), 
                            ('LGTH', 'LGTH'),
                            ('LGTA', 'LGTA'),
                            ('LGTR', 'LGTR'),
                            ('BOYARD', 'BOYARD'),
                            ('OTHER', 'OTHER')
                            ], 
                    validators=[DataRequired()])
                                    
    region = SelectField("Region",
                choices=[('US', 'US'), 
                            ('CANADA', 'CANADA'),
                            ('SOUTH_AMERICA', 'SOUTH_AMERICA'),
                            ('OTHER', 'OTHER')

                            ], 
                    validators=[DataRequired()])


    owner = StringField("Owner")
    product = StringField("Product")
    product_type = StringField("Product Type")
    customer = StringField("Customer",validators=[DataRequired()])
    customer_prospect = SelectField("Customer/Prospect",
                            choices=[('Customer', 'Customer'), 
                                    ('Prospect', 'Prospect')], 
                            validators=[DataRequired()])
    model = TextAreaField("Model")
    project = StringField("Project")
    status = SelectField("Status",
                        choices = [('New', 'New'),
                                    ('On going', 'On going'),
                                    ('Launched', 'Launched'),
                                    ('Closed', 'Closed'),
                                    ('Hold', 'Hold'),
                                    ('Dropped', 'Dropped')
                                    ],
                        validators=[DataRequired()])

    priority = SelectField("Priority",
                        choices = [('3', '3'),
                                    ('2', '2'),
                                    ('1', '1'),
                                    ('OTHER', 'OTHER')
                                    ],
                        validators=[DataRequired()])
                      
    refrigerant = StringField("Refrigerant")
    resolved = StringField("Resolved")
    application = StringField("Application")
    system_models = TextAreaField("System Models")
    target_spec = TextAreaField("Target Spec")
    comp_model = TextAreaField("Comp Model")
    scope = TextAreaField("Scope of Project")
    sample_serial = TextAreaField("Sample Serial")
    sample_ship_date = DateField("Sample Ship Date", format='%Y-%m-%d', validators=[Optional()])
    access = StringField("Access")
    spec_in = StringField("Spec In")
    award = StringField("Award")
    contact = StringField("Contact")
    remark = TextAreaField("Remark")
  
    items = FieldList(FormField(PipeLineItemForm, default=PipeLineItem), min_entries=0)
    # items = FieldList(FormField(PipeLineItemForm, default=PipeLineItem))


  
