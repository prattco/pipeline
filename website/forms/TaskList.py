# TaskList.py

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms.fields import html5
from wtforms import HiddenField, IntegerField, StringField, BooleanField, SelectField, TextAreaField, FieldList, FormField, validators, ValidationError
from .. import db
from sqlalchemy import text

from ..models import TaskList, TaskListItem

class TaskListItemForm(FlaskForm):
    id = HiddenField()
    task_list_id = HiddenField()
    item_line = IntegerField("Item Line")
    date = DateField("Date", format='%Y-%m-%d',validators=[DataRequired()])
    note = TextAreaField("Note")
    # ADD validators=[Optional()] HERE
    follow_up = DateField("Follow Up", format='%Y-%m-%d', validators=[Optional()])


    class Meta:
        csrf = False

class TaskListForm(FlaskForm):
    id = HiddenField()
    status = SelectField("Status", 
                        choices=[('Pending', 'Pending'), 
                                 ('Complete', 'Complete'),
                                 ('Incomplete', 'Incomplete')
                                 ], 
                        validators=[DataRequired()])

    owner = StringField("Owner")
    customer = StringField("Customer",validators=[DataRequired()])
    customer_prospect = SelectField("Customer/Prospect",
                            choices=[('Customer', 'Customer'), 
                                    ('Prospect', 'Prospect')], 
                            validators=[DataRequired()])
    project = TextAreaField("Project")

                      
    remark = TextAreaField("Remark")

    attachment_1 = StringField("Attachment 1")
    attachment_2 = StringField("Attachment 2")
    attachment_3 = StringField("Attachment 3")
    attachment_4 = StringField("Attachment 4")
    attachment_5 = StringField("Attachment 5")
  
    items = FieldList(FormField(TaskListItemForm, default=TaskListItem), min_entries=0)
    