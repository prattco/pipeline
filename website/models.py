from sqlalchemy.sql import func
from sqlalchemy import event
from flask_login import current_user, UserMixin
from . import db

def before_insert_listener(mapper, connection, target):
    target.created_user = current_user.id
    target.created_date = func.current_timestamp()
    # Note: Ensure User model has these attributes if used here
    if hasattr(current_user, 'company_name'):
        target.customer_name = current_user.company_name
    if hasattr(current_user, 'first_name'):
        target.customer_code = current_user.first_name

def before_update_listener(mapper, connection, target):
    target.updated_user = current_user.id
    target.updated_date = func.current_timestamp()

def note_on_delete_cascade(mapper, connection, target):
    Note.query.filter(Note.ref_id==target.id).delete()

class User(db.Model, UserMixin):
    __tablename__ = 'user_p'  # <--- UPDATED: Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.Text)
    company_name = db.Column(db.String(None))
    first_name = db.Column(db.String(None))
    vendor = db.Column(db.String(None))
    # Relationship to Note
    notes = db.relationship('Note', back_populates='user')
    created_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
class Note(db.Model):
    __tablename__ = 'note_p'  # <--- UPDATED: Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    ref_id = db.Column(db.Integer)
    data = db.Column(db.String(None))
    date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
    # Updated FK to point to user_p
    user_id = db.Column(db.Integer, db.ForeignKey('user_p.id')) 
    user = db.relationship('User', back_populates='notes')

# Cascade delete logic for Note
event.listen(Note, 'before_delete', note_on_delete_cascade)

class PipeLine(db.Model):
    __tablename__ = 'pipe_line' # Explicit naming is good practice
    id = db.Column(db.Integer, primary_key=True)
    shared = db.Column(db.String(None))
    division = db.Column(db.String(None))
    entity = db.Column(db.String(None))
    region = db.Column(db.String(None))
    owner = db.Column(db.String(None))
    product = db.Column(db.String(None))
    product_type = db.Column(db.String(None))
    customer = db.Column(db.String(None))
    customer_prospect = db.Column(db.String(None))
    model = db.Column(db.String(None))
    project = db.Column(db.String(None))
    status = db.Column(db.String(None))
    priority = db.Column(db.String(None))
    refrigerant = db.Column(db.String(None))
    application = db.Column(db.String(None))
    system_models = db.Column(db.String(None))
    target_spec = db.Column(db.String(None))
    comp_model = db.Column(db.String(None))
    scope = db.Column(db.String(None))
    resolved = db.Column(db.String(None))
    contact = db.Column(db.String(None))  
    remark = db.Column(db.String(None))
    delete_flag = db.Column(db.Integer, nullable=False, default=0)
    
    # Updated FKs to point to user_p
    created_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    created_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    updated_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    updated_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
    version_id = db.Column(db.Integer, nullable=False)
    __mapper_args__ = {
        'version_id_col': version_id
    }
    items = db.relationship('PipeLineItem', back_populates='pipe_line', cascade='all, delete-orphan')

event.listen(PipeLine, 'before_insert', before_insert_listener)
event.listen(PipeLine, 'before_update', before_update_listener)

class PipeLineItem(db.Model):
    __tablename__ = 'pipe_line_item' # Explicit naming
    id = db.Column(db.Integer, primary_key=True)
    pipe_line_id = db.Column(db.Integer, db.ForeignKey('pipe_line.id'))
    item_line = db.Column(db.Integer)
    date = db.Column(db.Date, default=func.getdate())
    follow_up = db.Column(db.Date)
    note = db.Column(db.String(None)) 
    
    # Updated FKs to point to user_p
    created_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    created_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    updated_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    updated_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
    pipe_line = db.relationship('PipeLine', back_populates='items')

    # __table_args__ = (db.UniqueConstraint('inbound_request_id', 'item_line', name='unique_inbound_request_id_item_line'),)

event.listen(PipeLineItem, 'before_insert', before_insert_listener)
event.listen(PipeLineItem, 'before_update', before_update_listener)





class QualityClaim(db.Model):
    __tablename__ = 'quality_claim' # Explicit naming is good practice
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(None))    
    customer = db.Column(db.String(None))
    report_date = db.Column(db.Date)
    application = db.Column(db.String(None))
    model = db.Column(db.String(None))
    type = db.Column(db.String(None))
    rma_no = db.Column(db.String(None))
    failure_loc = db.Column(db.String(None))
    serial_no = db.Column(db.String(None))
    issue = db.Column(db.String(None))
    corrective_action = db.Column(db.String(None))
    closed_date = db.Column(db.Date)   
    credit_memo = db.Column(db.String(None))
    delete_flag = db.Column(db.Integer, nullable=False, default=0)
    
    # Updated FKs to point to user_p
    created_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    created_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    updated_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    updated_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
    version_id = db.Column(db.Integer, nullable=False)
    __mapper_args__ = {
        'version_id_col': version_id
    }
    items = db.relationship('QualityClaimItem', back_populates='quality_claim', cascade='all, delete-orphan')

event.listen(QualityClaim, 'before_insert', before_insert_listener)
event.listen(QualityClaim, 'before_update', before_update_listener)

class QualityClaimItem(db.Model):
    __tablename__ = 'quality_claim_item' # Explicit naming
    id = db.Column(db.Integer, primary_key=True)
    quality_id = db.Column(db.Integer, db.ForeignKey('quality_claim.id'))
    item_line = db.Column(db.Integer)
    date = db.Column(db.Date, default=func.getdate())
    follow_up = db.Column(db.Date)
    note = db.Column(db.String(None)) 
    
    # Updated FKs to point to user_p
    created_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    created_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    updated_user = db.Column(db.Integer, db.ForeignKey('user_p.id'))
    updated_date = db.Column(db.DateTime(timezone=True), default=func.getdate())
    
    quality_claim = db.relationship('QualityClaim', back_populates='items')

    # __table_args__ = (db.UniqueConstraint('inbound_request_id', 'item_line', name='unique_inbound_request_id_item_line'),)

event.listen(QualityClaimItem, 'before_insert', before_insert_listener)
event.listen(QualityClaimItem, 'before_update', before_update_listener)