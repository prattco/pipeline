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

import urllib.parse
import requests
from .. import azurecred

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
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/General/pipe_lines/{encoded_filename}:/content"
    response = requests.put(url, headers=headers, data=file_storage.read())
    if response.status_code in [200, 201]: return response.json().get("webUrl") 
    raise Exception(f"SharePoint Upload Error: {response.text}")

pipe_line = Blueprint('pipe_line', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# 1. LIST VIEW
# ----------------------------------------------------------------------------
@pipe_line.route('/pipe_line/list', methods=['GET', 'POST'])
@login_required
def do_pipe_line_index():
    try:
        if current_user.first_name == "ALL":
            pipe_lines = PipeLine.query.filter(PipeLine.delete_flag != 1).order_by(desc(PipeLine.id)).all()
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        pipe_line_list = []
        import html # 이스케이프 처리를 위해 임포트

        for pipe_line in pipe_lines:
            subq = db.session.query(func.max(PipeLineItem.date)).filter_by(pipe_line_id=pipe_line.id).scalar_subquery()
            
            latest_item = db.session.query(PipeLineItem.note, PipeLineItem.date, PipeLineItem.follow_up).filter(
                PipeLineItem.pipe_line_id == pipe_line.id,
                PipeLineItem.date == subq
            ).first()

            latest_date = latest_item.date.strftime('%Y-%m-%d') if latest_item and latest_item.date else None
            follow_up = latest_item.follow_up.strftime('%Y-%m-%d') if latest_item and latest_item.follow_up else None

            # 💡 [Latest Note 가공]
            raw_latest_note = latest_item.note if latest_item else ""
            if raw_latest_note:
                safe_note = html.escape(raw_latest_note, quote=True)
                stripped_note = raw_latest_note.strip()
                if len(stripped_note) > 50:
                    truncated_text = html.escape(stripped_note[:50]) + "..."
                    latest_note_html = f'{truncated_text} <a href="javascript:void(0);" class="view-more-btn" data-note="{safe_note}" style="color: #007bff; font-weight: bold; cursor: pointer;">[More]</a>'
                else:
                    latest_note_html = html.escape(stripped_note)
            else:
                latest_note_html = ""

            # 💡 [Remark 가공] 50자 자르기 및 모달 팝업 추가
            raw_remark = pipe_line.remark if pipe_line.remark else ""
            if raw_remark:
                safe_remark = html.escape(raw_remark, quote=True)
                stripped_remark = raw_remark.strip()
                if len(stripped_remark) > 50:
                    truncated_remark = html.escape(stripped_remark[:50]) + "..."
                    remark_html = f'{truncated_remark} <a href="javascript:void(0);" class="view-more-btn" data-note="{safe_remark}" style="color: #007bff; font-weight: bold; cursor: pointer;">[More]</a>'
                else:
                    remark_html = html.escape(stripped_remark)
            else:
                remark_html = ""

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
                'latest_note': latest_note_html, 
                'latest_date': latest_date,
                'follow_up' : follow_up,
                'comp_model': pipe_line.comp_model.strip() if pipe_line.comp_model else None,
                'remark': remark_html # 💡 가공된 HTML 텍스트 매핑
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

            latest_date = latest_item.date.strftime('%Y-%m-%d') if latest_item and latest_item.date else None

            # 💡 [추가] 50자 자르기 및 팝업 모달 텍스트 인코딩 로직[cite: 32]
            raw_latest_note = latest_item.note if latest_item else ""
            if raw_latest_note:
                import html
                safe_note = html.escape(raw_latest_note, quote=True)
                stripped_note = raw_latest_note.strip()
                if len(stripped_note) > 50:
                    truncated_text = html.escape(stripped_note[:50]) + "..."
                    latest_note_html = f'{truncated_text} <a href="javascript:void(0);" class="view-more-btn" data-note="{safe_note}" style="color: #007bff; font-weight: bold; cursor: pointer;">[More]</a>'
                else:
                    latest_note_html = html.escape(stripped_note)
            else:
                latest_note_html = ""

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
                'latest_note': latest_note_html, # HTML 렌더링용 데이터 전달[cite: 32]
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
    try:
        pipe_line = getPipeLine(form.id.data, True)
        original_created_date = pipe_line.created_date
        
        if hasattr(form, 'id'): delattr(form, 'id')

        existing_item_ids = [item.id for item in pipe_line.items]
        submitted_item_ids = set()
        # 💡 [추가] 기존 첨부파일 유지용 딕셔너리
        old_attachments = {item.id: item.attachment_file_meta for item in pipe_line.items}

# 기존: for index, pipe_line_item_form in enumerate(form.items, start=1):
        for index, pipe_line_item_form in enumerate(form.items, start=1):
            pipe_line_item_form.item_line.data = index
            item_id = pipe_line_item_form.form.id.data
            
            sub_form = pipe_line_item_form.form
            if hasattr(sub_form, 'id'): delattr(sub_form, 'id')

            item_data = {k: v for k, v in sub_form.data.items()}

            if item_id and str(item_id).strip() and str(item_id) != '0':
                item = PipeLineItem.query.get(item_id)
                for key, value in item_data.items(): setattr(item, key, value)
                submitted_item_ids.add(int(item_id))
            else:
                item = PipeLineItem()
                for key, value in item_data.items(): setattr(item, key, value)
                pipe_line.items.append(item)

            item.item_line = index
            
            # 💡 [수정] 파일 업로드 및 삭제(Delete) 처리 로직
            file_index = index - 1
            file_input_name = f'items-{file_index}-attachment'
            delete_checkbox_name = f'items-{file_index}-delete_attachment'
            
            file = request.files.get(file_input_name)
            delete_flag = request.form.get(delete_checkbox_name) # 체크박스 값 가져오기

            if file and file.filename != '':
                unique_filename = f"pl_{pipe_line.id}_L{file_index}_{file.filename}"
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

        remove_items = [r_item for r_item in existing_item_ids if r_item not in submitted_item_ids]
        for r_item_id in remove_items:
            removeItem = PipeLineItem.query.get(r_item_id)
            if removeItem: pipe_line.items.remove(removeItem)

        form.populate_obj(pipe_line)
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