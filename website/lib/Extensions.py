from flask import flash, session, request, redirect
from wtforms import FieldList, HiddenField
from datetime import datetime

def errorForm(form) :
    stashFormData(form)
    formErrorHandle(form)
    
def stashFormData(form) :
    formclass = form.__class__
    form_data = formdata(form, formclass)
    session["old_input"] = form_data[0]

def formdata(formlist, formclass) :
    form_dict = parseForm(formclass)
    form_data_list = []
    
    if isinstance(formlist, list) == False :
        formlist = [formlist]
    
    for form in formlist :
        form_data = {}
        for key, value in form.data.items() :
            form_info = form_dict.get(key)
            if form_info :
                form_class = form_info[1]
                if form_class == FieldList :
                    form_data[key] = formdata(form[key].entries, form[key].unbound_field.args[0])
                else :
                    form_data[key] = {"value" : str(value), "fieldtype" : form_class.__name__}

        form_data_list.append(form_data)
    return form_data_list

def oldInputExists() :
    if "old_input" in session :
        return True
    else :
        return False
    
def createWithReference():
    if "refer" in request.args and oldInputExists() == False :
        return True
    else :
        return False

def prepareForm(formclass, default=None) :
    form = formclass()
    old_value = {}
    old_input = session.get("old_input")
    if old_input :
        for old_field, old_data in old_input.items() :
            if isinstance(old_data, list) :
                old_relation_datalist = []
                for old_relation_input in old_data :
                    old_relation_data = {}
                    for old_relation_field, old_relation_dict in old_relation_input.items() :
                        old_relation_data[old_relation_field] = getValueByType(old_relation_dict["fieldtype"], old_relation_dict["value"])
                    old_relation_datalist.append(old_relation_data)
                old_value[old_field] = old_relation_datalist
            else :
                old_value[old_field] = getValueByType(old_data["fieldtype"], old_data["value"])
        form = formclass(**old_value)
        session.pop('old_input', None)
    elif default :
        form = formclass(obj=default)

    return form

def getValueByType(fieldType, fieldValue) :
    if fieldType == "DateField" :
        if fieldValue == "None" :
            return None
        return datetime.strptime(fieldValue, "%Y-%m-%d")
    elif fieldType == "BooleanField" :
        return (fieldValue.lower() == "true")
    elif fieldType == "DecimalField" :
        if fieldValue == "None" :
            return None
        return float(fieldValue)
    else :
        return fieldValue
    
def formErrorHandle(form) :
    error_dict = {}
    form_dict = parseForm(form.__class__)
    relations_errors = {}
    for field, errors in form.errors.items() :
        if form_dict[field][1] == FieldList :
            relations_errors[field] = errors
        else :
            error_dict[field] = errors
    flashErrors(error_dict, form_dict)
    for section, errors in relations_errors.items() :
        form_dict_rel = parseForm(form[section].unbound_field.args[0])
        for index, error in enumerate(errors, start=1) :
            if isinstance(error, dict) :
                flashErrors(error, form_dict_rel, form_dict[section][0] + " " + str(index) + " ")
            elif isinstance(error, str) :
                flashErrors({section:[error]},form_dict)
    
    
def flashErrors(error_dict, form_dict, prefix = None) :
    messages = []
    for field_id, errors in error_dict.items() :
        field_label = form_dict[field_id][0]
        if field_label != "" :
            field_label += " : "
        field_error_messages = "," . join(errors)
        messages.append(field_label + field_error_messages)
    if messages :
        messagestr = "<br>" . join(messages)
        if prefix :
            messagestr = prefix + messagestr
        flash(messagestr, category="validate_error")

def parseForm(formclass) :
    form_dict = {}
    fields = formclass._unbound_fields
    for field in fields :
        if field[1].field_class == FieldList :
            form_dict[field[0]] = [field[0].capitalize(), field[1].field_class]
        elif field[1].field_class == HiddenField :
            form_dict[field[0]] = ["", field[1].field_class]
        else :
            form_dict[field[0]] = [field[1].args[0], field[1].field_class]
    return form_dict

def parseErrors(formclass, errors):
    messages = []
    for field_name, field in formclass.__dict__.items():
        errorMessages = errors.get(field_name)
        if errorMessages :
            for message in errorMessages :
                if isinstance(message, str):
                    messages.append(field.args[0] + " : " + message)
    if messages :
        messagestr = "<br>" . join(messages)
        flash(messagestr, category="validate_error")

def parseErrorsMultiple(section_name, formclass, errors_list):
    for index, form in enumerate(errors_list, start=1) :
        messages = []
        for field_name, field in formclass.__dict__.items():
            errorMessages = form.errors.get(field_name)
            if errorMessages :
                for message in errorMessages :
                    if isinstance(message, str):
                        messages.append(field.args[0] + " : " + message)
        if messages :
            messagestr = "<br>" . join(messages)
            messagestr = section_name + " " + str(index) + "<br>" + messagestr
            flash(messagestr, category="validate_error")

def redirect_back() :
    previous_url = request.referrer
    return redirect(previous_url)