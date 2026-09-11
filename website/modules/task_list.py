# task_list.py

from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

from ..models import TaskList, TaskListItem, User  
from .. import azurecred
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

CLIENT_ID = azurecred.CLIENT_ID
TENANT_ID = azurecred.TENANT_ID
CLIENT_SECRET = azurecred.CLIENT_SECRET
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
        # [안정화 반영] 사용자의 권한 검증 유지
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')
            
        # 데이터베이스 객체 리스트를 그대로 가져옵니다.
        task_lists = TaskList.query\
            .filter(TaskList.delete_flag != 1)\
            .options(joinedload(TaskList.creator))\
            .order_by(desc(TaskList.id))\
            .all()
        # 가공용 루프를 돌릴 필요 없이 객체 리스트를 그대로 템플릿으로 토스합니다.
        return render_template("task_list/list.html", user=current_user, list=task_lists)
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

@task_list.route('/task_list/display/<id>', methods=['GET'])
@login_required
def do_task_list_display(id):
    try:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')

        task_list_obj = TaskList.query\
            .options(
                joinedload(TaskList.creator),
                joinedload(TaskList.items).joinedload(TaskListItem.creator)
            )\
            .filter_by(id=id)\
            .first()

        if task_list_obj is None:
            abort(404)

        form = TaskListForm(obj=task_list_obj)
        form.id.data = task_list_obj.id
        form.created_user.data = task_list_obj.created_user_name

        form.items.entries = []
        for item in task_list_obj.items:
            # 💡 [핵심 수정] 폼 데이터 딕셔너리가 아닌, SQLAlchemy '객체(item)' 자체를 그대로 넣어야 
            # object_data가 보존되어 템플릿에서 attachment_file_meta 값을 읽어올 수 있습니다.
            form.items.append_entry(item)
            
            # 💡 작성자 이름(이메일 앞부분)만 방금 추가된 라인에 덮어쓰기
            if item.creator and item.creator.email:
                item_user_prefix = item.creator.email.split('@')[0]
            else:
                item_user_prefix = ""
                
            form.items[-1].created_user.data = item_user_prefix

        return render_template("task_list/display.html", user=current_user, form=form)
    except Exception as e:
        print(f"Error in do_task_list_display: {e}")
        return redirect('/')


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
        task_list_obj = getTaskList(id)
        form = prepareForm(TaskListForm)
        
        form.id.data = task_list_obj.id
        form.status.data = task_list_obj.status
        form.owner.data = task_list_obj.owner
        form.customer.data = task_list_obj.customer
        form.customer_prospect.data = task_list_obj.customer_prospect
        form.project.data = task_list_obj.project
        form.remark.data = task_list_obj.remark

        form.items.entries = []
        for item in task_list_obj.items:
            # 💡 [핵심 버그 수정] item_form.data 가 아닌 SQLAlchemy '객체(item)' 자체를 그대로 넣어야 
            # object_data가 보존되어 템플릿에서 첨부파일(attachment_file_meta) 값을 읽어올 수 있습니다.
            form.items.append_entry(item)

        item_form_template = prepareForm(TaskListItemForm)

        return render_template(
            'task_list/modify.html', 
            user=current_user,
            form=form, 
            item_form_template=item_form_template
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
    RECIPIENTS = ["danny.yun@prattco.com","sungsoon.jang@prattco.com"]
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
    try:
        if hasattr(form.id, 'data'): task_id = form.id.data
        else: task_id = form.id
            
        task_list_obj = getTaskList(task_id, True)
        is_new = task_list_obj.id is None

        original_created_date = task_list_obj.created_date
        existing_item_ids = [item.id for item in task_list_obj.items]
        submitted_item_ids = set()
        
        # 💡 아이템별 기존 첨부파일 유지 딕셔너리
        old_attachments = {item.id: item.attachment_file_meta for item in task_list_obj.items}

        for index, item_form_field in enumerate(form.items, start=1):
            sub_form = item_form_field.form
            item_id_val = sub_form.id.data
            
            # ForeignKey 에러 방지 위해 created_user는 폼 전송 데이터에서 제외
            item_data = {k: v for k, v in sub_form.data.items() if k not in ('id', 'created_user')}
            
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
                if is_new: item.created_user = current_user.id
                task_list_obj.items.append(item)

            # 💡 [핵심] 아이템 단위 파일 업로드 및 삭제(Delete) 처리
            file_index = index - 1
            file_input_name = f'items-{file_index}-attachment'
            delete_checkbox_name = f'items-{file_index}-delete_attachment'
            
            file = request.files.get(file_input_name)
            delete_flag = request.form.get(delete_checkbox_name)

            if file and file.filename != '':
                unique_filename = f"task_{task_list_obj.id}_L{file_index}_{file.filename}"
                try:
                    sharepoint_url = upload_file_to_sharepoint(file, unique_filename)
                    item.attachment_file_meta = f"{file.filename}||URL_INFO:{sharepoint_url}"
                except Exception as file_err:
                    print(f"Attachment Upload Error (Line {file_index}): {file_err}")
            else:
                # 파일 첨부가 새로 안 된 상태에서 '삭제' 체크박스가 눌렸다면 DB에서 파일 정보 제거
                if delete_flag:
                    item.attachment_file_meta = None
                elif item.id in old_attachments:
                    item.attachment_file_meta = old_attachments[item.id]

        for remove_id in [rid for rid in existing_item_ids if rid not in submitted_item_ids]:
            removeItem = TaskListItem.query.get(remove_id)
            if removeItem: db.session.delete(removeItem)

        excluded_keys = ['id', 'items', 'csrf_token', 'created_user']

        for fieldname, field in form._fields.items():
            if fieldname not in excluded_keys:
                setattr(task_list_obj, fieldname, field.data)
        
        if is_new: task_list_obj.created_user = current_user.id
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
        return redirect("/task_list/list")
    except Exception as e:
        db.session.rollback()
        abort(500)