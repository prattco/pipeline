from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

# Adjust these imports to match your folder structure if needed
from ..models import QuoteRequest, QuoteRequestItem  
from .. import db 
from ..forms.QuoteRequest import QuoteRequestForm, QuoteRequestItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

quote_request = Blueprint('quote_request', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW/
# ----------------------------------------------------------------------------
@quote_request.route('/quote_request/list', methods=['GET', 'POST'])
@login_required
def do_quote_request_index():
    try:
        # Authorization Check
        # if current_user.first_name not in ["ALL"]:
        if current_user.first_name != "ALL":
            flash('You are not authorized', category='error')
            return redirect('/')

        # Use joinedload to prevent N+1 query issues if necessary
        quote_requests = QuoteRequest.query.filter(QuoteRequest.delete_flag != 1).order_by(desc(QuoteRequest.id)).all()

        quote_request_list = []
        for quote_request in quote_requests:

            quote_request_data = {
                'id': quote_request.id,
                'requester': quote_request.requester.strip() if quote_request.requester else "",
                'customer': quote_request.customer.strip() if quote_request.customer else "",
                'status': quote_request.status.strip() if quote_request.status else "",
                'location': quote_request.location.strip() if quote_request.location else "",
                'type': quote_request.type.strip() if quote_request.type else "",
                
                'application': quote_request.application.strip() if quote_request.application else "",
                'terms': quote_request.terms.strip() if quote_request.terms else "",
                'remark': quote_request.remark.strip() if quote_request.remark else "",
                'created_date': quote_request.created_date,
                'updated_date': quote_request.updated_date,

                # 'created_date': quote_request.created_date.strftime('%Y-%m-%d %H:%M') if quote_request.created_date else "",
                # 'updated_date': quote_request.updated_date.strftime('%Y-%m-%d %H:%M') if quote_request.updated_date else "",
            }
            quote_request_list.append(quote_request_data)

        # Renamed variable from 'list' to 'quote_request_list' to avoid keyword conflicts
        return render_template("quote_request/list.html", user=current_user, quote_requests=quote_request_list)

    except Exception as e:
        # For local debugging, print the full traceback
        import traceback
        traceback.print_exc()
        print(f"Error in do_quote_request_index: {e}")
        flash("An error occurred while retrieving communication logs.", category='error')
        return redirect('/')


# ----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def getQuoteRequest(id, create=False):
    """
    Retrieves a QuoteRequest object by ID, handling errors and authorization.
    """
    try:
        quote_request = QuoteRequest.query.get(id)

        if quote_request is None:
            if create:
                return QuoteRequest()
            else:
                abort(404)
        elif quote_request.delete_flag == 1:
            abort(404)

        if current_user.first_name != "ALL":
            abort(403)

        return quote_request
    except Exception as e:
        print(f"Error in getQuoteRequest: {e}")
        abort(500)

def prepareFormWithReference():
    """
    Prepares a QuoteRequestForm with reference data.
    """
    try:
        refer_id = request.args.get('refer')
        quote_request = getQuoteRequest(refer_id)
        form = QuoteRequestForm(obj=quote_request)
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
@quote_request.route('/quote_request/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quote_request_display(id):
    try:
        if current_user.first_name == "ALL":
             # Just checking permission, not using the list here
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        # quote_request_obj = getQuoteRequest(id) # Retrieve the model object
        quote_request = getQuoteRequest(id)
        form = QuoteRequestForm(obj=quote_request)
        item_form = QuoteRequestItemForm()

        return render_template("quote_request/display.html", user=current_user, form=form, item_form=item_form, quote_request=quote_request)

    except Exception as e:
        print(f"Error in do_quote_request_display: {e}")
        abort(500)


@quote_request.route('/quote_request/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quote_request_item(id):
    try:
        if current_user.first_name == "ALL":
             pass
        # elif current_user.first_name == "LG":
        #      # LG logic handled in getQuoteRequest essentially, but explicit check here is fine
        #      pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        quote_request = getQuoteRequest(id)
        form = QuoteRequestForm(obj=quote_request)
        item_form = QuoteRequestItemForm()

        return render_template("quote_request/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_quote_request_item: {e}")
        abort(500)


@quote_request.route('/quote_request/create', methods=['GET', 'POST'])
@login_required
def do_quote_request_create():
    try:
        if createWithReference():
            form = prepareFormWithReference()
        else:
            form = prepareForm(QuoteRequestForm)
        item_form_template = QuoteRequestItemForm()
        return render_template("quote_request/create.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_quote_request_create: {e}")
        abort(500)

@quote_request.route('/quote_request/modify/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quote_request_modify(id):
    try:
        quote_request = getQuoteRequest(id)
        form = prepareForm(QuoteRequestForm, quote_request)
        item_form_template = QuoteRequestItemForm()
        return render_template("quote_request/modify.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_quote_request_modify: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 5. SAVE & DELETE LOGIC
# ----------------------------------------------------------------------------
@quote_request.route('/quote_request/save', methods=['POST'])
@login_required
def do_quote_request_save():
    form = QuoteRequestForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try:
                data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/quote_request/display/" + data_id)
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    try:
        if hasattr(form.id, 'data'):
            quote_id = form.id.data
        else:
            quote_id = form.id
            
        quote_request_obj = getQuoteRequest(quote_id, True)
        original_created_date = quote_request_obj.created_date
        
        existing_item_ids = [item.id for item in quote_request_obj.items]
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
                item = QuoteRequestItem.query.get(item_id_val)
                if item:
                    for key, value in item_data.items():
                        setattr(item, key, value)
                    item.item_line = index
                    submitted_item_ids.add(int(item_id_val))
            else:
                # New Item Creation
                item = QuoteRequestItem()
                for key, value in item_data.items():
                    setattr(item, key, value)
                item.item_line = index
                quote_request_obj.items.append(item)
            # --- CRITICAL FIX END ---

        for remove_id in [rid for rid in existing_item_ids if rid not in submitted_item_ids]:
            removeItem = QuoteRequestItem.query.get(remove_id)
            if removeItem:
                db.session.delete(removeItem)

        excluded_keys = ['id', 'items', 'csrf_token']
        for fieldname, field in form._fields.items():
            if fieldname not in excluded_keys:
                setattr(quote_request_obj, fieldname, field.data)
        
        quote_request_obj.created_date = original_created_date
        
        db.session.add(quote_request_obj)
        db.session.commit()

        return str(quote_request_obj.id)
    except Exception as e:
        print(f"Error in saveAction: {e}")
        db.session.rollback()
        abort(500)

@quote_request.route('/quote_request/delete', methods=['POST'])
@login_required
def do_quote_request_delete():
    try:
        id = request.form["delete_id"]
        quote_request = getQuoteRequest(id)
        quote_request.delete_flag = 1
        db.session.add(quote_request)
        db.session.commit()
        flash("Project is deleted", category="success")
        return redirect("/quote_request/list")
    except Exception as e:
        print(f"Error in do_quote_request_delete: {e}")
        db.session.rollback()
        abort(500)