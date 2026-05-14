from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

from datetime import timedelta # Add this to your imports at the top

# Adjust these imports to match your folder structure if needed
from ..models import TaskList, TaskListItem  
from .. import db 
from ..forms.TaskList import TaskListForm, TaskListItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

task_list = Blueprint('task_list', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW
# ----------------------------------------------------------------------------
@task_list.route('/task_list/list', methods=['GET', 'POST'])
@login_required
def do_task_list_index():
    """
    Retrieves and displays a list of TaskList objects.
    """
    try:
                # Authorization Check
        # if current_user.first_name not in ["ALL"]:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')

        task_lists = TaskList.query.filter(TaskList.delete_flag != 1).order_by(desc(TaskList.id)).all()

        # Define the offset (e.g., -5 hours for Central Daylight Time)
        # Change to -6 for standard winter time
        cst_offset = timedelta(hours=-5)    

        task_list_list = []
        for task_list in task_lists:
            # Subquery to find the latest note date for this TaskList
            subq = db.session.query(func.max(TaskListItem.date)).filter_by(task_list_id=task_list.id).scalar_subquery()
            
            latest_item = db.session.query(TaskListItem.note, TaskListItem.date, TaskListItem.follow_up).filter(
                TaskListItem.task_list_id == task_list.id,
                TaskListItem.date == subq
            ).first()

            # Apply offset safely
            c_date = task_list.created_date + cst_offset if task_list.created_date else None
            u_date = task_list.updated_date + cst_offset if task_list.updated_date else None

            task_list_data = {
                'id': task_list.id,
                
                'status': task_list.status.strip() if task_list.status else None,
                'owner': task_list.owner.strip() if task_list.owner else None,
                'customer': task_list.customer.strip() if task_list.customer else None,
                'customer_prospect': task_list.customer_prospect.strip() if task_list.customer_prospect else None,


                'project': task_list.project.strip() if task_list.project else None,
                'remark': task_list.remark.strip() if task_list.remark else None,
                # Pass the adjusted dates
                'created_date': c_date,
                'updated_date': u_date,
            }
            task_list_list.append(task_list_data)

        return render_template("task_list/list.html", user=current_user, list=task_list_list)
    except Exception as e:
        print(f"Error in do_task_list_index: {e}")
        flash("An error occurred while retrieving pipe lines.", category='error')
        return redirect('/')



# ----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def getTaskList(id, create=False):
    """
    Retrieves a TaskList object by ID, handling errors and authorization.
    """
    try:
        task_list = TaskList.query.get(id)

        if task_list is None:
            if create:
                return TaskList()
            else:
                abort(404)
        elif task_list.delete_flag == 1:
            abort(404)

        if current_user.first_name != "ALL":
            abort(403)

        return task_list
    except Exception as e:
        print(f"Error in getTaskList: {e}")
        abort(500)

def prepareFormWithReference():
    """
    Prepares a TaskListForm with reference data.
    """
    try:
        refer_id = request.args.get('refer')
        task_list = getTaskList(refer_id)
        form = TaskListForm(obj=task_list)
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
@task_list.route('/task_list/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_task_list_display(id):
    try:
        if current_user.first_name == "ALL":
             # Just checking permission, not using the list here
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')
        
        task_list = getTaskList(id)
        form = TaskListForm(obj=task_list)
        item_form = TaskListItemForm()

        return render_template("task_list/display.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_task_list_display: {e}")
        abort(500)


@task_list.route('/task_list/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_task_list_item(id):
    try:
        if current_user.first_name == "ALL":
             pass

        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        task_list = getTaskList(id)
        form = TaskListForm(obj=task_list)
        item_form = TaskListItemForm()

        return render_template("task_list/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_task_list_item: {e}")
        abort(500)


@task_list.route('/task_list/create', methods=['GET', 'POST'])
@login_required
def do_task_list_create():
    try:
        if createWithReference():
            form = prepareFormWithReference()
        else:
            form = prepareForm(TaskListForm)
        item_form_template = TaskListItemForm()
        return render_template("task_list/create.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_task_list_create: {e}")
        abort(500)

@task_list.route('/task_list/modify/<int:id>', methods=['GET', 'POST'])
@login_required
def do_task_list_modify(id):
    try:
        task_list = getTaskList(id)
        form = prepareForm(TaskListForm, task_list)
        item_form_template = TaskListItemForm()
        return render_template("task_list/modify.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_task_list_modify: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 5. SAVE & DELETE LOGIC
# ----------------------------------------------------------------------------
@task_list.route('/task_list/save', methods=['POST'])
@login_required
def do_task_list_save():
    form = TaskListForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try:
                data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/task_list/display/" + data_id)
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    """
    Helper function to perform the actual save action.
    """
    try:
        # 'True' creates a new instance if ID is empty
        task_list = getTaskList(form.id.data, True)
        
        # Store the original created_date before populating the object (to prevent overwrite)
        original_created_date = task_list.created_date
        
        # Remove ID from form data to avoid conflicts
        delattr(form, 'id')

        # Get list of existing item IDs currently in DB
        existing_item_ids = [item.id for item in task_list.items]
        submitted_item_ids = set()

        # Loop through items submitted in the form
        for index, task_list_item_form in enumerate(form.items, start=1):
            task_list_item_form.item_line.data = index
            item_id = task_list_item_form.form.id.data
            
            # Remove ID from sub-form to avoid conflicts
            delattr(task_list_item_form.form, 'id')

            # Debugging logs
            print(f"Item ID: {item_id}")
            print(f"Item Form Data: {task_list_item_form.form.data}")

            if item_id:
                # Update existing item
                item = TaskListItem.query.get(item_id)
                task_list_item_form.form.populate_obj(item)
                submitted_item_ids.add(int(item_id))
            else:
                # Create new item
                item = TaskListItem()
                task_list_item_form.form.populate_obj(item)
                task_list.items.append(item)

        # Identify items that were in the DB but NOT in the form submission (User deleted them)
        remove_items = [remove_item for remove_item in existing_item_ids if
                        remove_item not in submitted_item_ids]
        
        for remove_item_id in remove_items:
            removeItem = TaskListItem.query.get(remove_item_id)
            task_list.items.remove(removeItem)

        # Populate the main object
        form.populate_obj(task_list)
        
        # Restore the original created_date
        task_list.created_date = original_created_date
        
        db.session.add(task_list)
        db.session.commit()

        return str(task_list.id)
    except Exception as e:
        print(f"Error in saveAction: {e}")
        db.session.rollback()
        abort(500)



@task_list.route('/task_list/delete', methods=['POST'])
@login_required
def do_task_list_delete():
    try:
        id = request.form["delete_id"]
        task_list = getTaskList(id)
        task_list.delete_flag = 1
        db.session.add(task_list)
        db.session.commit()
        flash("Project is deleted", category="success")
        return redirect("/task_list/list")
    except Exception as e:
        print(f"Error in do_task_list_delete: {e}")
        db.session.rollback()
        abort(500)