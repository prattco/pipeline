from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

# Adjust these imports to match your folder structure if needed
from ..models import TaskList, TaskListItem, User  
from .. import db 
from ..forms.TaskList import TaskListForm, TaskListItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

from datetime import timedelta # Add this to your imports at the top

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib
from email.message import EmailMessage

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

def sendNotification(obj, is_new=True):
    EMAIL_FROM = "no-reply@chicagolandcfs.com"
    RECIPIENTS = ["danny.yun@prattco.com", "sungsoon.jang@prattco.com"]

# 1. 태스크 담당자(Owner)를 이메일 목록에 추가
    # obj.owner 값이 있으면 '@prattco.com'을 붙여서 추가합니다.
    if hasattr(obj, 'owner') and obj.owner:
        owner_email = f"{obj.owner.strip()}@prattco.com"
        RECIPIENTS.append(owner_email)
        print(f"Added owner email: {owner_email}")

# 2. 생성자(created_user)의 이메일 추가
    if hasattr(obj, 'created_user') and obj.created_user:
        try:
            creator = User.query.get(obj.created_user)
            if creator and creator.email:
                RECIPIENTS.append(creator.email)
                print(f"Added creator email: {creator.email}")
        except Exception as e:
            print(f"Could not retrieve creator email for ID {obj.created_user}: {e}")   

    # 3. 현재 수정 중인 사용자의 이메일 추가
    if current_user.email:
        RECIPIENTS.append(current_user.email)

# Remove duplicates
    RECIPIENTS = list(set(RECIPIENTS))

    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USERNAME = 'no-reply@chicagolandcfs.com'
    SMTP_PASSWORD = 'NReply@1418'

# 사용자 표시 이름 설정
    user_display_name = current_user.email.split('@')[0]


    action_verb = "assigned a new" if is_new else "updated the"
    summary_text = f"'{user_display_name}' {action_verb} task."

    # ------------------------------
    BASE_URL = "https://pipe-line.prattco.com/"  
    task_link = f"{BASE_URL}/task_list/display/{obj.id}"

    body = f"""
    <p>{summary_text}</p>
    <p>Please check <a href="{task_link}" style="color: #007bff; text-decoration: underline;">the system</a> for details.</p>
    """
    # ---------------------------

    msg = MIMEText(body, "html")
    msg['Subject'] = f"{'New' if is_new else 'Updated'} Task: {obj.customer}"
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(RECIPIENTS)

    try:
        smtp_obj = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp_obj.starttls()
        smtp_obj.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp_obj.sendmail(EMAIL_FROM, RECIPIENTS, msg.as_string())
        smtp_obj.quit()
        print("Notification sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def saveAction(form):
    """
    Helper function to perform the actual save action.
    """
    try:
        if hasattr(form.id, 'data'):
            task_id = form.id.data
        else:
            task_id = form.id
            
        task_list_obj = getTaskList(task_id, True)

        is_new = task_list_obj.id is None

        original_created_date = task_list_obj.created_date
        existing_item_ids = [item.id for item in task_list_obj.items]
        submitted_item_ids = set()

        for index, item_form_field in enumerate(form.items, start=1):
            sub_form = item_form_field.form
            
            # --- CRITICAL FIX START ---
            # 1. Capture the ID value to determine if it's an update or create
            item_id_val = sub_form.id.data
            
            # 2. Extract the data but EXCLUDE 'id' from being populated into the model
            # This prevents the "Cannot update identity column" error
            item_data = {k: v for k, v in sub_form.data.items() if k != 'id'}
            
            if item_id_val and str(item_id_val).strip() and str(item_id_val) != '0':
                # Existing Item Update
                item = TaskListItem.query.get(item_id_val)
                if item:
                    for key, value in item_data.items():
                        setattr(item, key, value)
                    item.item_line = index
                    submitted_item_ids.add(int(item_id_val))
            else:
                # New Item Creation
                item = TaskListItem()
                for key, value in item_data.items():
                    setattr(item, key, value)
                item.item_line = index
                task_list_obj.items.append(item)
            # --- CRITICAL FIX END ---

        for remove_id in [rid for rid in existing_item_ids if rid not in submitted_item_ids]:
            removeItem = TaskListItem.query.get(remove_id)
            if removeItem:
                db.session.delete(removeItem)

        excluded_keys = ['id', 'items', 'csrf_token']
        for fieldname, field in form._fields.items():
            if fieldname not in excluded_keys:
                setattr(task_list_obj, fieldname, field.data)
        
        if is_new:
            task_list_obj.created_user = current_user.id
        
        task_list_obj.updated_user = current_user.id
        task_list_obj.created_date = original_created_date
        
        db.session.add(task_list_obj)
        db.session.commit()
        
        sendNotification(task_list_obj, is_new)

        return str(task_list_obj.id)
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