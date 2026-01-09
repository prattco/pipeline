from flask import Blueprint, render_template, request, redirect, abort, flash
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import joinedload
import re

# Adjust these imports to match your folder structure if needed
from ..models import QualityClaim, QualityClaimItem  
from .. import db 
from ..forms.QualityClaim import QualityClaimForm, QualityClaimItemForm
from ..lib.Extensions import prepareForm, errorForm, redirect_back, createWithReference

quality_claim = Blueprint('quality_claim', __name__)

# ----------------------------------------------------------------------------
# 1. LIST VIEW/
# ----------------------------------------------------------------------------
@quality_claim.route('/quality_claim/list', methods=['GET', 'POST'])
@login_required
def do_quality_claim_index():
    try:
        # Authorization Check
        if current_user.first_name not in ["ALL", "LG"]:
            flash('You are not authorized', category='error')
            return redirect('/')

        # Use joinedload to prevent N+1 query issues if necessary
        quality_claims = QualityClaim.query.filter(QualityClaim.delete_flag != 1).order_by(desc(QualityClaim.id)).all()

        quality_claim_list = []
        for claim in quality_claims:
            # Subquery for the latest item date
            subq = db.session.query(func.max(QualityClaimItem.date)).filter_by(quality_id=claim.id).scalar_subquery()
            
            # Retrieve latest item details
            latest_item = db.session.query(
                QualityClaimItem.note, 
                QualityClaimItem.date, 
                QualityClaimItem.follow_up
            ).filter(
                QualityClaimItem.quality_id == claim.id,
                QualityClaimItem.date == subq
            ).first()

            # Safety checks for date formatting
            l_date = latest_item.date.strftime('%Y-%m-%d') if (latest_item and latest_item.date) else None
            f_up = latest_item.follow_up.strftime('%Y-%m-%d') if (latest_item and latest_item.follow_up) else None

            # Build data dictionary matching model names
            quality_claim_data = {
                'id': claim.id,
                'status': claim.status.strip() if claim.status else "",
                'customer': claim.customer.strip() if claim.customer else "",
                'report_date': claim.report_date.strftime('%Y-%m-%d') if claim.report_date else "",
                'application': claim.application.strip() if claim.application else "",
                'model': claim.model.strip() if claim.model else "",
                'type': claim.type.strip() if claim.type else "",
                'rma_no': claim.rma_no.strip() if claim.rma_no else "",
                'failure_loc': claim.failure_loc.strip() if claim.failure_loc else "",
                'serial_no': claim.serial_no.strip() if claim.serial_no else "",
                'issue': claim.issue.strip() if claim.issue else "",
                # FIXED: Corrected attribute name from .action to .corrective_action
                'corrective_action': claim.corrective_action.strip() if claim.corrective_action else "",
                'closed_date': claim.closed_date.strftime('%Y-%m-%d') if claim.closed_date else "",
                'credit_memo': claim.credit_memo.strip() if claim.credit_memo else "",
                'latest_note': latest_item.note if latest_item else "",
                'latest_date': l_date,
                'follow_up': f_up,
                
            }
            quality_claim_list.append(quality_claim_data)

        # Renamed variable from 'list' to 'claims' to avoid keyword conflicts
        return render_template("quality_claim/list.html", user=current_user, claims=quality_claim_list)

    except Exception as e:
        # For local debugging, print the full traceback
        import traceback
        traceback.print_exc()
        print(f"Error in do_quality_claim_index: {e}")
        flash("An error occurred while retrieving quality claims.", category='error')
        return redirect('/')


# ----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def getQualityClaim(id, create=False):
    """
    Retrieves a QualityClaim object by ID, handling errors and authorization.
    """
    try:
        quality_claim = QualityClaim.query.get(id)

        if quality_claim is None:
            if create:
                return QualityClaim()
            else:
                abort(404)
        elif quality_claim.delete_flag == 1:
            abort(404)

        if current_user.first_name != "ALL" and current_user.first_name != "LG":
            abort(403)

        return quality_claim
    except Exception as e:
        print(f"Error in getQualityClaim: {e}")
        abort(500)

def prepareFormWithReference():
    """
    Prepares a QualityClaimForm with reference data.
    """
    try:
        refer_id = request.args.get('refer')
        quality_claim = getQualityClaim(refer_id)
        form = QualityClaimForm(obj=quality_claim)
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
@quality_claim.route('/quality_claim/display/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quality_claim_display(id):
    try:
        if current_user.first_name == "ALL" or current_user.first_name == "LG":
             # Just checking permission, not using the list here
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')
        
        quality_claim = getQualityClaim(id)
        form = QualityClaimForm(obj=quality_claim)
        item_form = QualityClaimItemForm()

        return render_template("quality_claim/display.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_quality_claim_display: {e}")
        abort(500)


@quality_claim.route('/quality_claim/item/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quality_claim_item(id):
    try:
        if current_user.first_name == "ALL":
             pass
        elif current_user.first_name == "LG":
             # LG logic handled in getQualityClaim essentially, but explicit check here is fine
             pass
        else:
            flash('You are not authorized', category='error')
            return redirect('/')

        quality_claim = getQualityClaim(id)
        form = QualityClaimForm(obj=quality_claim)
        item_form = QualityClaimItemForm()

        return render_template("quality_claim/item.html", user=current_user, form=form, item_form=item_form)
    except Exception as e:
        print(f"Error in do_quality_claim_item: {e}")
        abort(500)


@quality_claim.route('/quality_claim/create', methods=['GET', 'POST'])
@login_required
def do_quality_claim_create():
    try:
        if createWithReference():
            form = prepareFormWithReference()
        else:
            form = prepareForm(QualityClaimForm)
        item_form_template = QualityClaimItemForm()
        return render_template("quality_claim/create.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_quality_claim_create: {e}")
        abort(500)

@quality_claim.route('/quality_claim/modify/<int:id>', methods=['GET', 'POST'])
@login_required
def do_quality_claim_modify(id):
    try:
        quality_claim = getQualityClaim(id)
        form = prepareForm(QualityClaimForm, quality_claim)
        item_form_template = QualityClaimItemForm()
        return render_template("quality_claim/modify.html", user=current_user, form=form, item_form_template=item_form_template)
    except Exception as e:
        print(f"Error in do_quality_claim_modify: {e}")
        abort(500)


# ----------------------------------------------------------------------------
# 5. SAVE & DELETE LOGIC
# ----------------------------------------------------------------------------
@quality_claim.route('/quality_claim/save', methods=['POST'])
@login_required
def do_quality_claim_save():
    form = QualityClaimForm()
    if form.validate_on_submit():
        with db.session.no_autoflush:
            try:
                data_id = saveAction(form)
            except StaleDataError:
                db.session.rollback()
                return redirect_back()
        return redirect("/quality_claim/display/" + data_id)
    else:
        errorForm(form)
        return redirect_back()

def saveAction(form):
    """
    Helper function to perform the actual save action.
    """
    try:
        # 'True' creates a new instance if ID is empty
        quality_claim = getQualityClaim(form.id.data, True)
        
        # Store the original created_date before populating the object (to prevent overwrite)
        original_created_date = quality_claim.created_date
        
        # Remove ID from form data to avoid conflicts
        delattr(form, 'id')

        # Get list of existing item IDs currently in DB
        existing_item_ids = [item.id for item in quality_claim.items]
        submitted_item_ids = set()

        # Loop through items submitted in the form
        for index, quality_claim_item_form in enumerate(form.items, start=1):
            quality_claim_item_form.item_line.data = index
            item_id = quality_claim_item_form.form.id.data
            
            # Remove ID from sub-form to avoid conflicts
            delattr(quality_claim_item_form.form, 'id')

            # Debugging logs
            print(f"Item ID: {item_id}")
            print(f"Item Form Data: {quality_claim_item_form.form.data}")

            if item_id:
                # Update existing item
                item = QualityClaimItem.query.get(item_id)
                quality_claim_item_form.form.populate_obj(item)
                submitted_item_ids.add(int(item_id))
            else:
                # Create new item
                item = QualityClaimItem()
                quality_claim_item_form.form.populate_obj(item)
                quality_claim.items.append(item)

        # Identify items that were in the DB but NOT in the form submission (User deleted them)
        remove_items = [remove_item for remove_item in existing_item_ids if
                        remove_item not in submitted_item_ids]
        
        for remove_item_id in remove_items:
            removeItem = QualityClaimItem.query.get(remove_item_id)
            quality_claim.items.remove(removeItem)

        # Populate the main object
        form.populate_obj(quality_claim)
        
        # Restore the original created_date
        quality_claim.created_date = original_created_date
        
        db.session.add(quality_claim)
        db.session.commit()

        return str(quality_claim.id)
    except Exception as e:
        print(f"Error in saveAction: {e}")
        db.session.rollback()
        abort(500)

@quality_claim.route('/quality_claim/delete', methods=['POST'])
@login_required
def do_quality_claim_delete():
    try:
        id = request.form["delete_id"]
        quality_claim = getQualityClaim(id)
        quality_claim.delete_flag = 1
        db.session.add(quality_claim)
        db.session.commit()
        flash("Project is deleted", category="success")
        return redirect("/quality_claim/list")
    except Exception as e:
        print(f"Error in do_quality_claim_delete: {e}")
        db.session.rollback()
        abort(500)