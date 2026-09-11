from flask_wtf import FlaskForm
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Optional
from wtforms import HiddenField, IntegerField, StringField, FloatField, SelectField, TextAreaField, FieldList, FormField
from ..models import ExpenseReport, ExpenseItem

class ExpenseItemForm(FlaskForm):
    id = HiddenField()
    expense_report_id = HiddenField()
    item_line = IntegerField("Item Line")
    
    expense_date = DateField("Date", format='%Y-%m-%d', validators=[Optional()])
    expense_type = SelectField("Type", choices=[('', 'Select...'), ('Company Card', 'Company Card'), ('Reimburse', 'Reimburse')], validators=[Optional()])
    
    # 💡 [핵심 수정] WTForms의 엄격한 유효성 검사 충돌을 피하기 위해 StringField로 변경
    category = StringField("Category")
    sub_category = StringField("Sub Category")
    
    amount = FloatField("Amount", validators=[Optional()])
    description = TextAreaField("Description")
    
    class Meta:
        csrf = False

class ExpenseReportForm(FlaskForm):
    id = HiddenField()
    title = StringField("Title", validators=[DataRequired()])
    status = SelectField("Status", choices=[('Draft', 'Draft'), ('Submitted', 'Submitted'), ('Approved', 'Approved')], validators=[DataRequired()])
    owner = StringField("Owner", validators=[DataRequired()])
    remark = TextAreaField("Remark")
    
    items = FieldList(FormField(ExpenseItemForm, default=ExpenseItem), min_entries=0)