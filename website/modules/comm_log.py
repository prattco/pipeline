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

import urllib.parse
import requests
from .. import azurecred # 기존에 설정된 인증 정보 활용

CLIENT_ID = azurecred.CLIENT_ID
TENANT_ID = azurecred.TENANT_ID
CLIENT_SECRET = azurecred.CLIENT_SECRET
SHAREPOINT_SITE_ID = "802m.sharepoint.com,b22264cc-8d3f-4f25-ba53-a2d1b134e40b,0ada892e-67f3-41cc-b30c-5815ab635a79"

def get_graph_token():
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        'client_id': CLIENT_ID, 'scope': 'https://graph.microsoft.com/.default',
        'client_secret': CLIENT_SECRET, 'grant_type': 'client_credentials'
    }
    response = requests.post(token_url, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if response.status_code == 200: return response.json().get('access_token')
    raise Exception(f"OAuth2 Error: {response.text}")

def upload_file_to_sharepoint(file_storage, custom_filename):
    token = get_graph_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": file_storage.content_type}
    encoded_filename = urllib.parse.quote(custom_filename)
    # 폴더 경로는 원하시는 대로 설정 가능 (예: comm_logs)
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/General/comm_logs/{encoded_filename}:/content"
    response = requests.put(url, headers=headers, data=file_storage.read())
    if response.status_code in [200, 201]: return response.json().get("webUrl") 
    raise Exception(f"SharePoint Upload Error: {response.text}")


comm_log = Blueprint('comm_log', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW/
# ----------------------------------------------------------------------------
@comm_log.route('/comm_log/list', methods=['GET', 'POST'])
@login_required
def do_comm_log_index():
    try:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')

        comm_logs = CommLog.query.filter(CommLog.delete_flag != 1).order_by(desc(CommLog.id)).all()

        comm_log_list = []
        for comm_log in comm_logs:
            subq = db.session.query(func.max(CommLogItem.date)).filter_by(comm_log_id=comm_log.id).scalar_subquery()
            
            latest_item = db.session.query(
                CommLogItem.date, 
                CommLogItem.contact,
                CommLogItem.method,
                CommLogItem.note,
            ).filter(
                CommLogItem.comm_log_id == comm_log.id,
                CommLogItem.date == subq
            ).first()

            l_date = latest_item.date.strftime('%Y-%m-%d') if (latest_item and latest_item.date) else None
      
            # --------------------------------------------------------
            # 💡 [핵심 수정 로직] 특수문자/줄바꿈 에러를 원천 차단하는 방식 적용
            # --------------------------------------------------------
            raw_latest_note = latest_item.note if latest_item else ""
            
            if raw_latest_note:
                import html
                # HTML 태그 속성에 들어가도 안전하도록 문자열을 인코딩합니다.
                safe_note = html.escape(raw_latest_note, quote=True)
                stripped_note = raw_latest_note.strip()
                
                if len(stripped_note) > 50:
                    # 화면에 보여질 50글자도 태그 꼬임을 막기 위해 인코딩
                    truncated_text = html.escape(stripped_note[:50]) + "..."
                    # onclick 대신 class와 data-note를 부여
                    latest_note_html = f'{truncated_text} <a href="javascript:void(0);" class="view-more-btn" data-note="{safe_note}" style="color: #007bff; font-weight: bold; cursor: pointer;">[More]</a>'
                else:
                    latest_note_html = html.escape(stripped_note)
            else:
                latest_note_html = ""
            # --------------------------------------------------------

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

                'latest_note': latest_note_html,
                'latest_date': l_date,
            }
            comm_log_list.append(comm_log_data)

        return render_template("comm_log/list.html", user=current_user, comm_logs=comm_log_list)

    except Exception as e:
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
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')
        
        comm_log = getCommLog(id)
        form = CommLogForm(obj=comm_log)
        item_form = CommLogItemForm()

        # 💡 [수정] comm_log 객체 전달 추가
        return render_template("comm_log/display.html", user=current_user, form=form, item_form=item_form, comm_log=comm_log)
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
    try:
        comm_log = getCommLog(form.id.data, True)
        original_created_date = comm_log.created_date
        
        if hasattr(form, 'id'):
            delattr(form, 'id')

        existing_item_ids = [item.id for item in comm_log.items]
        submitted_item_ids = set()
        old_attachments = {item.id: item.attachment_file_meta for item in comm_log.items}

# 기존: for index, comm_log_item_form in enumerate(form.items, start=1):
        for index, comm_log_item_form in enumerate(form.items, start=1):
            comm_log_item_form.item_line.data = index
            item_id = comm_log_item_form.form.id.data
            
            sub_form = comm_log_item_form.form
            if hasattr(sub_form, 'id'):
                delattr(sub_form, 'id')

            item_data = {k: v for k, v in sub_form.data.items()}

            if item_id and str(item_id).strip() and str(item_id) != '0':
                item = CommLogItem.query.get(item_id)
                for key, value in item_data.items(): setattr(item, key, value)
                submitted_item_ids.add(int(item_id))
            else:
                item = CommLogItem()
                for key, value in item_data.items(): setattr(item, key, value)
                comm_log.items.append(item)

            item.item_line = index
            
            # 💡 [수정] 파일 업로드 및 삭제(Delete) 처리 로직
            file_index = index - 1
            file_input_name = f'items-{file_index}-attachment'
            delete_checkbox_name = f'items-{file_index}-delete_attachment'
            
            file = request.files.get(file_input_name)
            delete_flag = request.form.get(delete_checkbox_name) # 체크박스 값 가져오기

            if file and file.filename != '':
                unique_filename = f"cl_{comm_log.id}_L{file_index}_{file.filename}"
                try:
                    sharepoint_url = upload_file_to_sharepoint(file, unique_filename)
                    item.attachment_file_meta = f"{file.filename}||URL_INFO:{sharepoint_url}"
                except Exception as file_err:
                    print(f"Attachment Upload Error (Line {file_index}): {file_err}")
            else:
                # 💡 파일 첨부가 새로 안 된 상태에서 '삭제' 체크박스가 눌렸다면 DB에서 파일 정보 제거
                if delete_flag:
                    item.attachment_file_meta = None
                elif item.id in old_attachments:
                    item.attachment_file_meta = old_attachments[item.id]

        # 삭제된 아이템 처리
        remove_items = [remove_item for remove_item in existing_item_ids if remove_item not in submitted_item_ids]
        for remove_item_id in remove_items:
            removeItem = CommLogItem.query.get(remove_item_id)
            if removeItem:
                comm_log.items.remove(removeItem)

        form.populate_obj(comm_log)
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