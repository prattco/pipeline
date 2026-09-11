from flask import Blueprint, render_template, request, redirect, abort, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import desc
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import urllib.parse
import requests

from ..models import ExpenseReport, ExpenseItem, User  
from .. import azurecred, db 
from ..forms.Expense import ExpenseReportForm, ExpenseItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back

import io
import zipfile
import pandas as pd


expense_bp = Blueprint('expense', __name__)

# --- SharePoint Upload Logic ---
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
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/General/expenses/{encoded_filename}:/content"
    response = requests.put(url, headers=headers, data=file_storage.read())
    if response.status_code in [200, 201]: return response.json().get("webUrl") 
    raise Exception(f"SharePoint Upload Error: {response.text}")

def getExpenseReport(id, create=False):
    report = ExpenseReport.query.get(id)
    if report is None:
        if create: return ExpenseReport()
        else: abort(404)
    elif report.delete_flag == 1: abort(404)
    return report

def prepareFormWithReference_expense():
    refer_id = request.args.get('refer')
    report = getExpenseReport(refer_id)
    form = ExpenseReportForm(obj=report)
    form.id.data = None
    form.items.entries = []
    return form

# --- Routes ---
@expense_bp.route('/expense/list', methods=['GET'])
@login_required
def do_expense_index():

    if current_user.first_name != "ALL":
        flash('You are not authorized', category='error')
        return redirect('/')
               
    base_query = ExpenseReport.query.filter(ExpenseReport.delete_flag != 1)\
        .options(joinedload(ExpenseReport.creator))
        
    user_role = current_user.role.strip().lower() if getattr(current_user, 'role', None) else ""
    
    if user_role == 'admin':
        expenses = base_query.order_by(desc(ExpenseReport.id)).all()
        
    elif user_role == 'supervisor':
        all_users = User.query.all()
        allowed_user_ids = [current_user.id]
        
        for u in all_users:
            if getattr(u, 'supervisor', None) and str(u.supervisor).strip() == str(current_user.id).strip():
                allowed_user_ids.append(u.id)
                
        expenses = base_query.filter(ExpenseReport.created_user.in_(allowed_user_ids))\
            .order_by(desc(ExpenseReport.id)).all()
            
    else:
        expenses = base_query.filter(ExpenseReport.created_user == current_user.id)\
            .order_by(desc(ExpenseReport.id)).all()
            
    return render_template("expense/list.html", user=current_user, list=expenses)
    

@expense_bp.route('/expense/display/<id>', methods=['GET'])
@login_required
def do_expense_display(id):
    if current_user.first_name != "ALL":
        flash('You are not authorized', category='error')
        return redirect('/')
        
    report = getExpenseReport(id)
    
    user_role = current_user.role.strip().lower() if current_user.role else ""
    
    is_creator = (str(report.created_user).strip() == str(current_user.id).strip())
    is_admin = (user_role == 'admin')
    
    is_authorized_supervisor = False
    if user_role == 'supervisor':
        try:
            creator = User.query.get(int(report.created_user))
            if creator and str(creator.supervisor).strip() == str(current_user.id).strip():
                is_authorized_supervisor = True
        except:
            pass

    if not (is_creator or is_admin or is_authorized_supervisor):
        flash("You do not have permission to view this report.", "error")
        return redirect('/expense/list')
                
    form = ExpenseReportForm(obj=report)
    
    existing_receipts = {}
    for item in report.items:
        if item.receipt_file_meta and "||URL_INFO:" in item.receipt_file_meta:
            parts = item.receipt_file_meta.split("||URL_INFO:")
            existing_receipts[item.item_line] = {
                'filename': parts[0].strip(),
                'url': parts[1].strip()
            }
            
    return render_template("expense/display.html", user=current_user, form=form, existing_receipts=existing_receipts)


@expense_bp.route('/expense/create', methods=['GET', 'POST'])
@login_required
def do_expense_create():
    try:
        if request.args.get('refer'):
            form = prepareFormWithReference_expense()
        else:
            form = prepareForm(ExpenseReportForm)
            
        item_form_template = prepareForm(ExpenseItemForm)
        
        return render_template(
            "expense/create.html", 
            user=current_user, 
            form=form, 
            item_form_template=item_form_template, 
            existing_receipts={}
        )
    except Exception as e:
        print(f"Error in do_expense_create: {e}")
        abort(500)


@expense_bp.route('/expense/download/<int:id>', methods=['GET'])
@login_required
def do_expense_download(id):
    report = getExpenseReport(id)
    
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
        header_data = [{
            'Report ID': report.id,
            'Title': report.title,
            'Status': report.status,
            'Owner': report.owner,
            'Remark': report.remark,
            'Created Date': report.created_date.strftime('%Y-%m-%d %H:%M') if report.created_date else "",
            'Updated Date': report.updated_date.strftime('%Y-%m-%d %H:%M') if report.updated_date else ""
        }]
        df_header = pd.DataFrame(header_data)
        df_header.to_excel(writer, sheet_name='Report Header', index=False)
        
        items_data = []
        for item in report.items:
            items_data.append({
                'Line': item.item_line,
                'Date': item.expense_date.strftime('%Y-%m-%d') if item.expense_date else "",
                'Type': item.expense_type,
                'Category': item.category,
                'Sub Category': getattr(item, 'sub_category', ''),
                'Amount': item.amount,
                'Description': item.description,
                'Receipt Filename': item.receipt_file_meta.split("||URL_INFO:")[0].strip() if item.receipt_file_meta else "No Receipt"
            })
            
        if items_data:
            df_items = pd.DataFrame(items_data)
        else:
            df_items = pd.DataFrame(columns=['Line', 'Date', 'Type', 'Category', 'Sub Category', 'Amount', 'Description', 'Receipt Filename'])
            
        df_items.to_excel(writer, sheet_name='Line Items', index=False)
    
    excel_io.seek(0)
    
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"Expense_Report_{report.id}.xlsx", excel_io.getvalue())
        
        token = get_graph_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        for item in report.items:
            if item.receipt_file_meta and "||URL_INFO:" in item.receipt_file_meta:
                original_filename = item.receipt_file_meta.split("||URL_INFO:")[0].strip()
                unique_filename = f"exp_{report.id}_L{item.item_line}_{original_filename}"
                encoded_filename = urllib.parse.quote(unique_filename)
                
                url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/General/expenses/{encoded_filename}:/content"
                
                try:
                    resp = requests.get(url, headers=headers)
                    if resp.status_code == 200:
                        zf.writestr(f"Receipts/Line_{item.item_line}_{original_filename}", resp.content)
                    else:
                        print(f"SharePoint Download failed for {original_filename}: {resp.status_code}")
                except Exception as e:
                    print(f"Error fetching receipt {original_filename}: {e}")
                    
    zip_io.seek(0)
    
    return send_file(
        zip_io,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'Expense_Data_{report.id}.zip'
    )


@expense_bp.route('/expense/modify/<id>', methods=['GET'])
@login_required
def do_expense_modify(id):
    report = getExpenseReport(id)
    
    user_role = current_user.role.strip().lower() if current_user.role else ""
    is_admin = (user_role == 'admin')
    
    is_authorized_supervisor = False
    if user_role == 'supervisor':
        try:
            creator = User.query.get(int(report.created_user))
            if creator and str(creator.supervisor).strip() == str(current_user.id).strip():
                is_authorized_supervisor = True
        except:
            pass

    if not (is_admin or is_authorized_supervisor):
        if report.status != 'Draft':
            flash("You are not able to modify 'Submitted' or 'Approved' expense.", "error")
            return redirect(f'/expense/display/{id}')

    form = prepareForm(ExpenseReportForm)
    form.id.data = report.id
    form.title.data = report.title
    form.status.data = report.status
    form.owner.data = report.owner
    form.remark.data = report.remark

    existing_receipts = {}
    form.items.entries = []
    for item in report.items:
        if not item.expense_date and not item.amount:
            continue
            
        item_form = ExpenseItemForm(obj=item)
        form.items.append_entry(item_form.data)
        
        if item.receipt_file_meta and "||URL_INFO:" in item.receipt_file_meta:
            parts = item.receipt_file_meta.split("||URL_INFO:")
            existing_receipts[item.item_line] = {'filename': parts[0].strip(), 'url': parts[1].strip()}

    item_form_template = prepareForm(ExpenseItemForm)
    return render_template('expense/modify.html', user=current_user, form=form, item_form_template=item_form_template, existing_receipts=existing_receipts)


@expense_bp.route('/expense/save', methods=['POST'])
@login_required
def do_expense_save():
    form = ExpenseReportForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try: data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/expense/list")
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    expense_id = form.id.data if hasattr(form.id, 'data') else form.id
    report_obj = getExpenseReport(expense_id, True)
    is_new = report_obj.id is None

    if not is_new:
        user_role = current_user.role.strip().lower() if current_user.role else ""
        is_admin = (user_role == 'admin')
        
        is_authorized_supervisor = False
        if user_role == 'supervisor':
            try:
                creator = User.query.get(int(report_obj.created_user))
                if creator and str(creator.supervisor).strip() == str(current_user.id).strip():
                    is_authorized_supervisor = True
            except:
                pass
        
        if not (is_admin or is_authorized_supervisor):
            if report_obj.status != 'Draft':
                raise Exception("Permission Denied: You can only save modifications to 'Draft' reports.")

    existing_item_ids = [item.id for item in report_obj.items]
    submitted_item_ids = set()
    old_receipts = {item.id: item.receipt_file_meta for item in report_obj.items}

    report_obj.title = form.title.data
    report_obj.status = form.status.data
    report_obj.owner = form.owner.data
    report_obj.remark = form.remark.data

    if is_new:
        db.session.add(report_obj)
        db.session.flush()

    for index, item_form_field in enumerate(form.items, start=0):
        sub_form = item_form_field.form
        
        if not sub_form.expense_date.data and not sub_form.amount.data:
            continue

        item_id_val = sub_form.id.data
        item_data = {k: v for k, v in sub_form.data.items() if k != 'id'}

        if item_id_val and str(item_id_val).strip() and str(item_id_val) != '0':
            item = ExpenseItem.query.get(item_id_val)
            for key, value in item_data.items(): setattr(item, key, value)
            submitted_item_ids.add(int(item_id_val))
        else:
            item = ExpenseItem()
            for key, value in item_data.items(): setattr(item, key, value)
            report_obj.items.append(item)

        item.item_line = index
        
        # 파일 업로드 및 삭제(Delete) 처리 로직
        file_input_name = f'items-{index}-receipt'
        delete_checkbox_name = f'items-{index}-delete_receipt'
        
        file = request.files.get(file_input_name)
        delete_flag = request.form.get(delete_checkbox_name)

        if file and file.filename != '':
            unique_filename = f"exp_{report_obj.id}_L{index}_{file.filename}"
            try:
                sharepoint_url = upload_file_to_sharepoint(file, unique_filename)
                item.receipt_file_meta = f"{file.filename}||URL_INFO:{sharepoint_url}"
            except Exception as file_err:
                print(f"Receipt Upload Error (Line {index}): {file_err}")
        else:
            # 파일 첨부가 새로 안 된 상태에서 '삭제' 체크박스가 눌렸다면 DB에서 파일 정보 제거
            if delete_flag:
                item.receipt_file_meta = None
            elif item.id in old_receipts:
                item.receipt_file_meta = old_receipts[item.id]

    for remove_id in [rid for rid in existing_item_ids if rid not in submitted_item_ids]:
        removeItem = ExpenseItem.query.get(remove_id)
        if removeItem: db.session.delete(removeItem)

    db.session.commit()
    return str(report_obj.id)


@expense_bp.route('/expense/delete', methods=['POST'])
@login_required
def do_expense_delete():
    try:
        id = request.form["delete_id"]
        report = getExpenseReport(id)
        report.delete_flag = 1
        db.session.add(report)
        db.session.commit()
        return redirect("/expense/list")
    except Exception as e:
        db.session.rollback()
        abort(500)