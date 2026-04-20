from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

# Adjust these imports to match your folder structure if needed
from ..models import CommLog, CommLogItem  
from .. import db 
from ..forms.CommLog import CommLogForm, CommLogItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

comm_log = Blueprint('comm_log', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW/
# ----------------------------------------------------------------------------
@comm_log.route('/comm_log/list', methods=['GET', 'POST'])
@login_required
def do_comm_log_index():
    try:
        # Authorization Check
        # if current_user.first_name not in ["ALL"]:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')

        # Use joinedload to prevent N+1 query issues if necessary
        comm_logs = CommLog.query.filter(CommLog.delete_flag != 1).order_by(desc(CommLog.id)).all()

        comm_log_list = []
        for comm_log in comm_logs:
            # Subquery for the latest item date
            subq = db.session.query(func.max(CommLogItem.date)).filter_by(comm_log_id=comm_log.id).scalar_subquery()
            
            # Retrieve latest item details
            latest_item = db.session.query(
 
                CommLogItem.date, 
                CommLogItem.contact,
                CommLogItem.method,
                CommLogItem.note,
            ).filter(
                CommLogItem.comm_log_id == comm_log.id,
                CommLogItem.date == subq
            ).first()

            # Safety checks for date formatting
            l_date = latest_item.date.strftime('%Y-%m-%d') if (latest_item and latest_item.date) else None
      

            # Build data dictionary matching model names
            comm_log_data = {
                'id': comm_log.id,
                'status': comm_log.status.strip() if comm_log.status else "",
                'customer': comm_log.customer.strip() if comm_log.customer else "",
                'owner': comm_log.owner.strip() if comm_log.owner else "",
                'application': comm_log.application.strip() if comm_log.application else "",
                'address': comm_log.address.strip() if comm_log.address else "",
                'city': comm_log.city.strip() if comm_log.city else "",
                'state': comm_log.state.strip() if comm_log.state else "",
                'zip': comm_log.zip.strip() if comm_log.zip else "",
                
                'contact1': comm_log.contact1.strip() if comm_log.contact1 else "",
                'title1': comm_log.title1.strip() if comm_log.title1 else "",
                'email1': comm_log.email1.strip() if comm_log.email1 else "",
                'phone1': comm_log.phone1.strip() if comm_log.phone1 else "",
                'office1': comm_log.office1.strip() if comm_log.office1 else "",
                'cnote1': comm_log.cnote1.strip() if comm_log.cnote1 else "",
                
                'contact2': comm_log.contact2.strip() if comm_log.contact2 else "",
                'title2': comm_log.title2.strip() if comm_log.title2 else "",
                'email2': comm_log.email2.strip() if comm_log.email2 else "",
                'phone2': comm_log.phone2.strip() if comm_log.phone2 else "",
                'office2': comm_log.office2.strip() if comm_log.office2 else "",
                'cnote2': comm_log.cnote2.strip() if comm_log.cnote2 else "",
                
                'contact3': comm_log.contact3.strip() if comm_log.contact3 else "",
                'title3': comm_log.title3.strip() if comm_log.title3 else "",
                'email3': comm_log.email3.strip() if comm_log.email3 else "",
                'phone3': comm_log.phone3.strip() if comm_log.phone3 else "",
                'office3': comm_log.office3.strip() if comm_log.office3 else "",
                'cnote3': comm_log.cnote3.strip() if comm_log.cnote3 else "",
                
                'contact4': comm_log.contact4.strip() if comm_log.contact4 else "",
                'title4': comm_log.title4.strip() if comm_log.title4 else "",
                'email4': comm_log.email4.strip() if comm_log.email4 else "",
                'phone4': comm_log.phone4.strip() if comm_log.phone4 else "",
                'office4': comm_log.office4.strip() if comm_log.office4 else "",
                'cnote4': comm_log.cnote4.strip() if comm_log.cnote4 else "",                
                
                'contact5': comm_log.contact5.strip() if comm_log.contact5 else "",
                'title5': comm_log.title5.strip() if comm_log.title5 else "",
                'email5': comm_log.email5.strip() if comm_log.email5 else "",
                'phone5': comm_log.phone5.strip() if comm_log.phone5 else "",
                'office5': comm_log.office5.strip() if comm_log.office5 else "",
                'cnote5': comm_log.cnote5.strip() if comm_log.cnote5 else "",


                'launch_date': comm_log.launch_date.strftime('%Y-%m-%d') if comm_log.launch_date else "",
                'remark': comm_log.remark.strip() if comm_log.remark else "",

                'latest_note': latest_item.note if latest_item else "",
                'latest_date': l_date,
                
            }
            comm_log_list.append(comm_log_data)

        # Renamed variable from 'list' to 'comm_log_list' to avoid keyword conflicts
        return render_template("comm_log/list.html", user=current_user, comm_logs=comm_log_list)

    except Exception as e:
        # For local debugging, print the full traceback
        import traceback
        traceback.print_exc()
        print(f"Error in do_comm_log_index: {e}")
        flash("An error occurred while retrieving communication logs.", category='error')
        return redirect('/')


# ----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def getCommLog(id, create=False):
    """
    Retrieves a CommLog object by ID, handling errors and authorization.
    """
    try:
        comm_log = CommLog.query.get(id)

        if comm_log is None:
            if create:
                return CommLog()
            else:
                abort(404)
        elif comm_log.delete_flag == 1:
            abort(404)

        if current_user.first_name != "ALL":
            abort(403)

        return comm_log
    except Exception as e:
        print(f"Error in getCommLog: {e}")
        abort(500)

def prepareFormWithReference():
    """
    Prepares a CommLogForm with reference data.
    """
    try:
        refer_id = request.args.get('refer')
        comm_log = getCommLog(refer_id)
        form = CommLogForm(obj=comm_log)
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
@comm_log.route('/comm_log/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_comm_log_display(id):
    try:
        if current_user.first_name == "ALL":
             # Just checking permission, not using the list here
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')
        
        comm_log = getCommLog(id)
        form = CommLogForm(obj=comm_log)
        item_form = CommLogItemForm()

        return render_template("comm_log/display.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_comm_log_display: {e}")
        abort(500)


@comm_log.route('/comm_log/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_comm_log_item(id):
    try:
        if current_user.first_name == "ALL":
             pass
        # elif current_user.first_name == "LG":
        #      # LG logic handled in getCommLog essentially, but explicit check here is fine
        #      pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        comm_log = getCommLog(id)
        form = CommLogForm(obj=comm_log)
        item_form = CommLogItemForm()

        return render_template("comm_log/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_comm_log_item: {e}")
        abort(500)


@comm_log.route('/comm_log/create', methods=['GET', 'POST'])
@login_required
def do_comm_log_create():
    try:
        if createWithReference():
            form = prepareFormWithReference()
        else:
            form = prepareForm(CommLogForm)
        item_form_template = CommLogItemForm()
        return render_template("comm_log/create.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_comm_log_create: {e}")
        abort(500)

@comm_log.route('/comm_log/modify/<int:id>', methods=['GET', 'POST'])
@login_required
def do_comm_log_modify(id):
    try:
        comm_log = getCommLog(id)
        form = prepareForm(CommLogForm, comm_log)
        item_form_template = CommLogItemForm()
        return render_template("comm_log/modify.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_comm_log_modify: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 5. SAVE & DELETE LOGIC
# ----------------------------------------------------------------------------
@comm_log.route('/comm_log/save', methods=['POST'])
@login_required
def do_comm_log_save():
    form = CommLogForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try:
                data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/comm_log/display/" + data_id)
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    """
    Helper function to perform the actual save action.
    """
    try:
        # 'True' creates a new instance if ID is empty
        comm_log = getCommLog(form.id.data, True)
        
        # Store the original created_date before populating the object (to prevent overwrite)
        original_created_date = comm_log.created_date
        
        # Remove ID from form data to avoid conflicts
        delattr(form, 'id')

        # Get list of existing item IDs currently in DB
        existing_item_ids = [item.id for item in comm_log.items]
        submitted_item_ids = set()

        # Loop through items submitted in the form
        for index, comm_log_item_form in enumerate(form.items, start=1):
            comm_log_item_form.item_line.data = index
            item_id = comm_log_item_form.form.id.data
            
            # Remove ID from sub-form to avoid conflicts
            delattr(comm_log_item_form.form, 'id')

            # Debugging logs
            print(f"Item ID: {item_id}")
            print(f"Item Form Data: {comm_log_item_form.form.data}")

            if item_id:
                # Update existing item
                item = CommLogItem.query.get(item_id)
                comm_log_item_form.form.populate_obj(item)
                submitted_item_ids.add(int(item_id))
            else:
                # Create new item
                item = CommLogItem()
                comm_log_item_form.form.populate_obj(item)
                comm_log.items.append(item)

        # Identify items that were in the DB but NOT in the form submission (User deleted them)
        remove_items = [remove_item for remove_item in existing_item_ids if
                        remove_item not in submitted_item_ids]
        
        for remove_item_id in remove_items:
            removeItem = CommLogItem.query.get(remove_item_id)
            comm_log.items.remove(removeItem)

        # Populate the main object
        form.populate_obj(comm_log)
        
        # Restore the original created_date
        comm_log.created_date = original_created_date
        
        db.session.add(comm_log)
        db.session.commit()

        return str(comm_log.id)
    except Exception as e:
        print(f"Error in saveAction: {e}")
        db.session.rollback()
        abort(500)

@comm_log.route('/comm_log/delete', methods=['POST'])
@login_required
def do_comm_log_delete():
    try:
        id = request.form["delete_id"]
        comm_log = getCommLog(id)
        comm_log.delete_flag = 1
        db.session.add(comm_log)
        db.session.commit()
        flash("Project is deleted", category="success")
        return redirect("/comm_log/list")
    except Exception as e:
        print(f"Error in do_comm_log_delete: {e}")
        db.session.rollback()
        abort(500)