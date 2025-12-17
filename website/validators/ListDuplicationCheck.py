from wtforms import ValidationError

class ListDuplicationCheck(object):
    def __init__(self, checkfield, message=None):
        self.message = message
        self.checkfield = checkfield
    def __call__(self, form, fields):
        checkset = set()
        for entry in fields.entries:
            if self.checkfield in entry.data:
                if entry.data[self.checkfield] :
                    if entry.data[self.checkfield] in checkset:
                        checkfieldlabel = entry.form[self.checkfield].label.text
                        raise ValidationError(checkfieldlabel + " is duplicated")
                    else :
                        checkset.add(entry.data[self.checkfield])