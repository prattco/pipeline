from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

from ..models import TaskList, TaskListItem, User  
from .. import db 
from ..forms.TaskList import TaskListForm, TaskListItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib
from email.message import EmailMessage

import requests
import urllib.parse
import msal

task_list = Blueprint('task_list', __name__)

CLIENT_ID = "f91f74a0-98f1-4c4e-b73e-ec7927859ddd"
TENANT_ID = "62795f34-e80c-46cb-bb48-f72a3f9ec90f"
CLIENT_SECRET = "6l_8Q~wGlQ8_RUSL~nV1RX~WgjKZxWIg-ZHvZdo~"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SHAREPOINT_SITE_ID = "802m.sharepoint.com,b22264cc-8d3f-4f25-ba53-a2d1b134e40b,0ada892e-67f3-41cc-b30c-5815ab635a79"

def get_graph_token():
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        'client_id': CLIENT_ID,
        'scope': 'https://graph.microsoft.com/.default',
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"OAuth2 다이렉트 토큰 획득 실패: {response.text}")

def upload_file_to_sharepoint(file_storage, custom_filename):
    token = get_graph_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": file_storage.content_type
    }
    encoded_filename = urllib.parse.quote(custom_filename)
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/General/pipeline/{encoded_filename}:/content"
    response = requests.put(url, headers=headers, data=file_storage.read())
    if response.status_code in [200, 201]:
        return response.json().get("webUrl") 
    else:
        raise Exception(f"SharePoint 업로드 실패: {response.text}")

@task_list.route('/task_list/list', methods=['GET', 'POST'])
@login_required
def do_task_list_index():
    try:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')
        task_lists = TaskList.query.filter(TaskList.delete_flag != 1).order_by(desc(TaskList.id)).all()
        cst_offset = timedelta(hours=-5)    
        task_list_list = []
        for task_list in task_lists:
            subq = db.session.query(func.max(TaskListItem.date)).filter_by(task_list_id=task_list.id).scalar_subquery()
            latest_item = db.session.query(TaskListItem.note, TaskListItem.date, TaskListItem.follow_up).filter(
                TaskListItem.task_list_id == task_list.id,
                TaskListItem.date == subq
            ).first()
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
                'created_date': c_date,
                'updated_date': u_date,
            }
            task_list_list.append(task_list_data)
        return render_template("task_list/list.html", user=current_user, list=task_list_list)
    except Exception as e:
        print(f"Error in do_task_list_index: {e}")
        return redirect('/')

def getTaskList(id, create=False):
    task_list = TaskList.query.get(id)
    if task_list is None:
        if create: return TaskList()
        else: abort(404)
    elif task_flag := task_list.delete_flag == 1:
        abort(404)
    if current_user.first_name != "ALL":
        abort(403)
    return task_list

def prepareFormWithReference():
    refer_id = request.args.get('refer')
    task_list = getTaskList(refer_id)
    form = TaskListForm(obj=task_list)
    form.id.data = None
    form.items.entries = []
    return form

@task_list.route('/task_list/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_task_list_display(id):
    try:
        if current_user.first_name != "ALL": abort(403)
        task_list = getTaskList(id)
        form = TaskListForm(obj=task_list)
        item_form = TaskListItemForm()
        return render_template("task_list/display.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        abort(500)

@task_list.route('/task_list/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_task_list_item(id):
    try:
        task_list = getTaskList(id)
        form = TaskListForm(obj=task_list)
        item_form = TaskListItemForm()
        return render_template("task_list/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        abort(500)

@task_list.route('/task_list/create', methods=['GET', 'POST'])
@login_required
def do_task_list_create():
    try:
        form = prepareFormWithReference() if createWithReference() else prepareForm(TaskListForm)
        item_form_template = TaskListItemForm()
        return render_template("task_list/create.html", user=current_user, form=form, item_form_template=item_form_template, existing_files=[])
    except Exception as e:
        abort(500)

@task_list.route('/task_list/modify/<id>', methods=['GET'])
@login_required
def do_task_list_modify(id):
    try:
        task_list = getTaskList(id)
        form = prepareForm(TaskListForm)
        
        form.id.data = task_list.id
        form.status.data = task_list.status
        form.owner.data = task_list.owner
        form.customer.data = task_list.customer
        form.customer_prospect.data = task_list.customer_prospect
        form.project.data = task_list.project
        form.remark.data = task_list.remark

        # 📁 [안정화] DB 컬럼에서 바로 첨부파일 데이터를 안전하게 읽어와 템플릿용 딕셔너리 구축
        existing_files = []
        for i in range(1, 6):
            field_name = f'attachment_{i}'
            db_file_data = getattr(task_list, field_name, None)
            
            # WTForms 내부 백킹 오브젝트 싱크를 위한 강제 주입
            if hasattr(form, field_name):
                getattr(form, field_name).data = db_file_data
            
            if db_file_data and "||URL_INFO_" in db_file_data:
                try:
                    url_marker = f"||URL_INFO_{i}:"
                    parts = db_file_data.split(url_marker)
                    filename = parts[0].strip()
                    url = parts[1].strip() if len(parts) > 1 else "#"
                    
                    if filename:
                        existing_files.append({
                            'index': i,
                            'filename': filename,
                            'url': url
                        })
                except Exception as parse_err:
                    print(f"Error reading attachment field {i}: {parse_err}")

        form.items.entries = []
        for item in task_list.items:
            item_form = TaskListItemForm(obj=item)
            form.items.append_entry(item_form.data)

        item_form_template = prepareForm(TaskListItemForm)

        return render_template(
            'task_list/modify.html', 
            user=current_user,
            form=form, 
            item_form_template=item_form_template,
            existing_files=existing_files
        )
    except Exception as e:
        print(f"Error in do_task_list_modify: {e}")
        abort(500)

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
    RECIPIENTS = ["danny.yun@prattco.com"]
    if hasattr(obj, 'owner') and obj.owner:
        RECIPIENTS.append(f"{obj.owner.strip()}@prattco.com")
    if hasattr(obj, 'created_user') and obj.created_user:
        try:
            creator = User.query.get(obj.created_user)
            if creator and creator.email: RECIPIENTS.append(creator.email)
        except: pass   
    if current_user.email: RECIPIENTS.append(current_user.email)
    RECIPIENTS = list(set(RECIPIENTS))

    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USERNAME = 'no-reply@chicagolandcfs.com'
    SMTP_PASSWORD = 'NReply@1418'

    user_display_name = current_user.email.split('@')[0]
    action_verb = "assigned a new" if is_new else "updated the"
    summary_text = f"'{user_display_name}' {action_verb} task."
    BASE_URL = "https://pipe-line.prattco.com/"  
    task_link = f"{BASE_URL}/task_list/display/{obj.id}"

    body = f"<p>{summary_text}</p><p>Please check <a href='{task_link}'>the system</a> for details.</p>"
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
    except Exception as e:
        print(f"Failed to send email: {e}")

def saveAction(form):
    """
    Helper function to perform the actual save action with support for up to 5 attachments via dedicated DB fields.
    """
    try:
        if hasattr(form.id, 'data'): task_id = form.id.data
        else: task_id = form.id
            
        task_list_obj = getTaskList(task_id, True)
        is_new = task_list_obj.id is None

        original_created_date = task_list_obj.created_date
        existing_item_ids = [item.id for item in task_list_obj.items]
        submitted_item_ids = set()

        for index, item_form_field in enumerate(form.items, start=1):
            sub_form = item_form_field.form
            item_id_val = sub_form.id.data
            item_data = {k: v for k, v in sub_form.data.items() if k != 'id'}
            
            if item_id_val and str(item_id_val).strip() and str(item_id_val) != '0':
                item = TaskListItem.query.get(item_id_val)
                if item:
                    for key, value in item_data.items(): setattr(item, key, value)
                    item.item_line = index
                    submitted_item_ids.add(int(item_id_val))
            else:
                item = TaskListItem()
                for key, value in item_data.items(): setattr(item, key, value)
                item.item_line = index
                task_list_obj.items.append(item)

        for remove_id in [rid for rid in existing_item_ids if rid not in submitted_item_ids]:
            removeItem = TaskListItem.query.get(remove_id)
            if removeItem: db.session.delete(removeItem)

        # 1. 폼 기본 일반 데이터 객체 주입
        excluded_keys = ['id', 'items', 'csrf_token', 'attachment_1', 'attachment_2', 'attachment_3', 'attachment_4', 'attachment_5']
        for fieldname, field in form._fields.items():
            if fieldname not in excluded_keys:
                setattr(task_list_obj, fieldname, field.data)
        
        if is_new: task_list_obj.created_user = current_user.id
        task_list_obj.updated_user = current_user.id
        task_list_obj.created_date = original_created_date
        
        # 파일 수정을 진행하기 전 세션에 있는 객체의 원래 스냅샷 데이터를 백업해둡니다.
        # 이렇게 해야 세션 변경 과정에서 컬럼 데이터가 FileStorage로 꼬이는 것을 원천 차단합니다.
        old_attachments = {}
        if not is_new:
            for idx in range(1, 6):
                old_attachments[idx] = getattr(task_list_obj, f'attachment_{idx}', None)

        db.session.add(task_list_obj)
        db.session.flush()

        # 2. 📁 전용 독립 컬럼 5개 루프 돌며 파일 매핑 및 보존 제어 (타입 에러 방어 보호막 완비)
        for i in range(1, 6):
            input_name = f'attachment_{i}'
            file = request.files.get(input_name) if input_name in request.files else None
            
            # Case A: 사용자가 새 파일을 업로드 한 경우 -> SharePoint 전송 후 해당 컬럼 문자열 새 데이터로 교체
            if file and file.filename != '':
                unique_filename = f"task_{task_list_obj.id}_f{i}_{file.filename}"
                try:
                    sharepoint_url = upload_file_to_sharepoint(file, unique_filename)
                    meta_value = f"{file.filename}||URL_INFO_{i}:{sharepoint_url}"
                    setattr(task_list_obj, f'attachment_{i}', meta_value)
                except Exception as file_err:
                    print(f"SharePoint Multi-Upload Error (File {i}): {file_err}")
            
            # Case B: 새 파일을 올리지 않은 경우 -> 객체 오염을 막고 원래 DB에 기록되어 있던 백업 문자열로 강제 환원 및 유지
            else:
                if not is_new:
                    setattr(task_list_obj, f'attachment_{i}', old_attachments.get(i))
                else:
                    setattr(task_list_obj, f'attachment_{i}', None)

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
        return redirect("/task_list/list")
    except Exception as e:
        db.session.rollback()
        abort(500)