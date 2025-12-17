from wtforms import ValidationError

class ExistCheck(object):
    def __init__(self, table, searchColumn, existIsValid=True, skipOnModify=False, message=None):
        self.message = message
        self.table = table
        self.searchColumn = searchColumn
        self.existIsValid = existIsValid
        self.skipOnModify = skipOnModify

    def __call__(self, form, field):
        if self.skipOnModify and form.id.data:  # Skip on modify if the flag is set
            return

        search = {self.searchColumn: field.data}
        exists = self.table.query.filter_by(**search).first()  # Use .first()
        
        # search = {self.searchColumn: field.data.strip().lower()}
        # exists = self.table.query.filter_by(**search).first()

        if self.existIsValid == True and exists == None:
            # Record should exist, but it doesn't
            if self.message is None:
                message = "Item not exist."  # Changed message
            else:
                message = self.message
            raise ValidationError(message)
        elif self.existIsValid == False and exists != None:
            # Record should not exist, but it does
            if self.message is None:
                message = "Already exist item."
            else:
                message = self.message
            raise ValidationError(message)

