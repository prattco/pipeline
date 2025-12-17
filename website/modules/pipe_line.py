from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

# Adjust these imports to match your folder structure if needed
from ..models import PipeLine, PipeLineItem  
from .. import db 
from ..forms.PipeLine import PipeLineForm, PipeLineItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

pipe_line = Blueprint('pipe_line', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW
# ----------------------------------------------------------------------------
@pipe_line.route('/pipe_line/list', methods=['GET', 'POST'])
@login_required
def do_pipe_line_index():
    """
    Retrieves and displays a list of PipeLine objects.
    """
    try:
        if current_user.first_name == "ALL":
            pipe_lines = PipeLine.query.filter(PipeLine.delete_flag != 1).order_by(desc(PipeLine.id)).all()
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        pipe_line_list = []
        for pipe_line in pipe_lines:
            # Subquery to find the latest note date for this pipeline
            subq = db.session.query(func.max(PipeLineItem.date)).filter_by(pipe_line_id=pipe_line.id).scalar_subquery()
            
            latest_item = db.session.query(PipeLineItem.note, PipeLineItem.date, PipeLineItem.follow_up).filter(
                PipeLineItem.pipe_line_id == pipe_line.id,
                PipeLineItem.date == subq
            ).first()

            latest_note = latest_item.note if latest_item else None
            latest_date = latest_item.date.strftime('%Y-%m-%d') if latest_item and latest_item.date else None
            follow_up = latest_item.follow_up.strftime('%Y-%m-%d') if latest_item and latest_item.follow_up else None

            pipe_line_data = {
                'id': pipe_line.id,
                'customer': pipe_line.customer.strip() if pipe_line.customer else None,
                'customer_prospect': pipe_line.customer_prospect.strip() if pipe_line.customer_prospect else None,
                'application': pipe_line.application.strip() if pipe_line.application else None,
                'owner': pipe_line.owner.strip() if pipe_line.owner else None,
                'product': pipe_line.product.strip() if pipe_line.product else None,
                'product_type': pipe_line.product_type.strip() if pipe_line.product_type else None,
                'shared': pipe_line.shared.strip() if pipe_line.shared else None,
                'status': pipe_line.status.strip() if pipe_line.status else None,
                'priority': pipe_line.priority.strip() if pipe_line.priority else None,
                'refrigerant': pipe_line.refrigerant.strip() if pipe_line.refrigerant else None,
                'model': pipe_line.model.strip() if pipe_line.model else None,
                'latest_note': latest_note,
                'latest_date': latest_date,
                'follow_up' : follow_up,
                'comp_model': pipe_line.comp_model.strip() if pipe_line.comp_model else None,
                'remark': pipe_line.remark.strip() if pipe_line.remark else None
            }
            pipe_line_list.append(pipe_line_data)

        return render_template("pipe_line/list.html", user=current_user, list=pipe_line_list)
    except Exception as e:
        print(f"Error in do_pipe_line_index: {e}")
        flash("An error occurred while retrieving pipe lines.", category='error')
        return redirect('/')


# ----------------------------------------------------------------------------
# 2. REPORT VIEW
# ----------------------------------------------------------------------------
@pipe_line.route('/pipe_line/report', methods=['GET', 'POST'])
@login_required
def do_pipe_line_report():
    try:
        if current_user.first_name == "ALL":
            pipe_lines = PipeLine.query.filter(PipeLine.delete_flag != 1).order_by(desc(PipeLine.id)).all()
        elif current_user.first_name == "LG":
            # Filter where shared is 'shared' (case-insensitive)
            pipe_lines = PipeLine.query.filter(
                PipeLine.delete_flag != 1,
                func.lower(PipeLine.shared) == "shared"
            ).order_by(desc(PipeLine.id)).all()
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        pipe_line_report = []
        for pipe_line in pipe_lines:
            subq = db.session.query(func.max(PipeLineItem.date)).filter_by(pipe_line_id=pipe_line.id).scalar_subquery()
            latest_item = db.session.query(PipeLineItem.note, PipeLineItem.date).filter(
                PipeLineItem.pipe_line_id == pipe_line.id,
                PipeLineItem.date == subq
            ).first()

            latest_note = latest_item.note if latest_item else None
            latest_date = latest_item.date.strftime('%Y-%m-%d') if latest_item and latest_item.date else None

            pipe_line_data = {
                'id': pipe_line.id,
                'customer': pipe_line.customer.strip() if pipe_line.customer else None,
                'customer_prospect': pipe_line.customer_prospect.strip() if pipe_line.customer_prospect else None,
                'application': pipe_line.application.strip() if pipe_line.application else None,
                'owner': pipe_line.owner.strip() if pipe_line.owner else None,
                'product': pipe_line.product.strip() if pipe_line.product else None,
                'product_type': pipe_line.product_type.strip() if pipe_line.product_type else None,
                'status': pipe_line.status.strip() if pipe_line.status else None,
                'priority': pipe_line.priority.strip() if pipe_line.priority else None,
                'refrigerant': pipe_line.refrigerant.strip() if pipe_line.refrigerant else None,
                'model': pipe_line.model.strip() if pipe_line.model else None,
                'latest_note': latest_note,
                'latest_date': latest_date,
                'comp_model': pipe_line.comp_model.strip() if pipe_line.comp_model else None,
            }
            pipe_line_report.append(pipe_line_data)

        return render_template("pipe_line/report.html", user=current_user, list=pipe_line_report)
    except Exception as e:
        print(f"Error in do_pipe_line_report: {e}")
        flash("An error occurred while retrieving pipe lines.", category='error')
        return redirect('/')


# ----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def getPipeLine(id, create=False):
    """
    Retrieves a PipeLine object by ID, handling errors and authorization.
    """
    try:
        pipe_line = PipeLine.query.get(id)

        if pipe_line is None:
            if create:
                return PipeLine()
            else:
                abort(404)
        elif pipe_line.delete_flag == 1:
            abort(404)

        if current_user.first_name != "ALL" and current_user.first_name != "LG":
            abort(403)

        return pipe_line
    except Exception as e:
        print(f"Error in getPipeLine: {e}")
        abort(500)

def prepareFormWithReference():
    """
    Prepares a PipeLineForm with reference data.
    """
    try:
        refer_id = request.args.get('refer')
        pipe_line = getPipeLine(refer_id)
        form = PipeLineForm(obj=pipe_line)
        form.id.data = None

        # remove all lines so we start fresh
        form.items.entries = []

        return form
    except Exception as e:
        print(f"Error in prepareFormWithReference: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 4. CRUD ROUTES (Display, Create, Modify, Item)
# ----------------------------------------------------------------------------
@pipe_line.route('/pipe_line/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_pipe_line_display(id):
    try:
        if current_user.first_name == "ALL":
             # Just checking permission, not using the list here
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')
        
        pipe_line = getPipeLine(id)
        form = PipeLineForm(obj=pipe_line)
        item_form = PipeLineItemForm()

        return render_template("pipe_line/display.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_pipe_line_display: {e}")
        abort(500)


@pipe_line.route('/pipe_line/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_pipe_line_item(id):
    try:
        if current_user.first_name == "ALL":
             pass
        elif current_user.first_name == "LG":
             # LG logic handled in getPipeLine essentially, but explicit check here is fine
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        pipe_line = getPipeLine(id)
        form = PipeLineForm(obj=pipe_line)
        item_form = PipeLineItemForm()

        return render_template("pipe_line/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_pipe_line_item: {e}")
        abort(500)


@pipe_line.route('/pipe_line/create', methods=['GET', 'POST'])
@login_required
def do_pipe_line_create():
    try:
        if createWithReference():
            form = prepareFormWithReference()
        else:
            form = prepareForm(PipeLineForm)
        item_form_template = PipeLineItemForm()
        return render_template("pipe_line/create.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_pipe_line_create: {e}")
        abort(500)

@pipe_line.route('/pipe_line/modify/<int:id>', methods=['GET', 'POST'])
@login_required
def do_pipe_line_modify(id):
    try:
        pipe_line = getPipeLine(id)
        form = prepareForm(PipeLineForm, pipe_line)
        item_form_template = PipeLineItemForm()
        return render_template("pipe_line/modify.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_pipe_line_modify: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 5. SAVE & DELETE LOGIC
# ----------------------------------------------------------------------------
@pipe_line.route('/pipe_line/save', methods=['POST'])
@login_required
def do_pipe_line_save():
    form = PipeLineForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try:
                data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/pipe_line/display/" + data_id)
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    """
    Helper function to perform the actual save action.
    """
    try:
        # 'True' creates a new instance if ID is empty
        pipe_line = getPipeLine(form.id.data, True)
        
        # Store the original created_date before populating the object (to prevent overwrite)
        original_created_date = pipe_line.created_date
        
        # Remove ID from form data to avoid conflicts
        delattr(form, 'id')

        # Get list of existing item IDs currently in DB
        existing_item_ids = [item.id for item in pipe_line.items]
        submitted_item_ids = set()

        # Loop through items submitted in the form
        for index, pipe_line_item_form in enumerate(form.items, start=1):
            pipe_line_item_form.item_line.data = index
            item_id = pipe_line_item_form.form.id.data
            
            # Remove ID from sub-form to avoid conflicts
            delattr(pipe_line_item_form.form, 'id')

            # Debugging logs
            print(f"Item ID: {item_id}")
            print(f"Item Form Data: {pipe_line_item_form.form.data}")

            if item_id:
                # Update existing item
                item = PipeLineItem.query.get(item_id)
                pipe_line_item_form.form.populate_obj(item)
                submitted_item_ids.add(int(item_id))
            else:
                # Create new item
                item = PipeLineItem()
                pipe_line_item_form.form.populate_obj(item)
                pipe_line.items.append(item)

        # Identify items that were in the DB but NOT in the form submission (User deleted them)
        remove_items = [remove_item for remove_item in existing_item_ids if
                        remove_item not in submitted_item_ids]
        
        for remove_item_id in remove_items:
            removeItem = PipeLineItem.query.get(remove_item_id)
            pipe_line.items.remove(removeItem)

        # Populate the main object
        form.populate_obj(pipe_line)
        
        # Restore the original created_date
        pipe_line.created_date = original_created_date
        
        db.session.add(pipe_line)
        db.session.commit()

        return str(pipe_line.id)
    except Exception as e:
        print(f"Error in saveAction: {e}")
        db.session.rollback()
        abort(500)

@pipe_line.route('/pipe_line/delete', methods=['POST'])
@login_required
def do_pipe_line_delete():
    try:
        id = request.form["delete_id"]
        pipe_line = getPipeLine(id)
        pipe_line.delete_flag = 1
        db.session.add(pipe_line)
        db.session.commit()
        flash("Project is deleted", category="success")
        return redirect("/pipe_line/list")
    except Exception as e:
        print(f"Error in do_pipe_line_delete: {e}")
        db.session.rollback()
        abort(500)