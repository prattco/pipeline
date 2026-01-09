# __init__.py

import time
import urllib.parse
from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.exc import OperationalError

from . import azurecred
from .lib.Helper import getUrl as helperGetUrl, getModule as helperGetModule, getMethod as helperGetMethod


params = urllib.parse.quote_plus(
    f"DRIVER={{{azurecred.AZDBDRIVER}}};"
    f"SERVER={azurecred.AZDBSERVER};"
    f"DATABASE={azurecred.AZDBNAME};"
    f"UID={azurecred.AZDBUSER};"
    f"PWD={azurecred.AZDBPW};"
)
dsn = f"mssql+pyodbc:///?odbc_connect={params}"

# dsn = "mssql+pyodbc://"+azurecred.AZDBUSER+":"+azurecred.AZDBPW+"@"+azurecred.AZDBSERVER+azurecred.AZDBNAME+"?driver="+azurecred.AZDBDRIVER

db = SQLAlchemy()
DB_NAME = azurecred.AZDBNAME


app = Flask(__name__)

def create_app():
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = dsn
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = -1

    db.init_app(app)

    from .views import views
    from .auth import auth
    from .modules.pipe_line import pipe_line
    from .modules.quality_claim import quality_claim

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(pipe_line, url_prefix='/')
    app.register_blueprint(quality_claim, url_prefix='/')


    from .models import User, Note
    
    with app.app_context():
        db.create_all()

    max_retries = 3
    retry_delay = 1  # Delay in seconds before retrying
    for attempt in range(1, max_retries + 1):
        try:
            login_manager = LoginManager()
            login_manager.login_view = 'auth.login'
            login_manager.init_app(app)

            @login_manager.user_loader
            def load_user(id):
                return User.query.get(int(id))
            break
        except OperationalError as e:
            print(f"Attempt {attempt} failed. Retrying...")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                # Redirect to home page on database connection failure
                @app.errorhandler(OperationalError)
                def handle_db_connection_error(e):
                    return redirect(url_for('views.home'))  # Adjust the endpoint based on your actual home page URL
                return app

    return app

# Add this function to handle the operational errors and redirect the user
from sqlalchemy import exc
@app.errorhandler(exc.OperationalError)
def handle_operational_error(error):
    # Redirect the user to a different page (e.g., home page) when the connection drops
    return redirect(url_for('views.home'))

@app.context_processor
def utility_processor():
    def getUrl():
        return helperGetUrl()

    def getModule():
        return helperGetModule()
    
    def getMethod():
        return helperGetMethod()
    
    return {'getUrl' : getUrl, 'getModule' : getModule, 'getMethod' : getMethod}