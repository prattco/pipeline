import pandas as pd
import pyodbc
from sqlalchemy import create_engine, event
import localsqlcred  # Assuming you have localsqlcred.py with your credentials
from datetime import datetime
import logging  # Import the logging module

# Configure logging (replace with your preferred setup)
logging.basicConfig(level=logging.ERROR)  # Or logging.INFO, etc.

# 1. Database Connection
lsdsn = "mssql+pyodbc://" + localsqlcred.lsDBUSER + ":" + localsqlcred.lsDBPW + "@" + localsqlcred.lsDBSERVER + localsqlcred.lsDBNAME + "?driver=" + localsqlcred.lsDBDRIVER
lsengine = create_engine(lsdsn)


# Function to execute SQL statements
def execute_sql(engine, sql):
    try:
        engine.execute(sql)
        print(f"SQL executed successfully: {sql}")
    except Exception as e:
        logging.error(f"Error executing SQL: {e}", exc_info=True)
        print(f"Error executing SQL: {e}")
        print(e)



    # 2. Load Data from Excel
    try:
        pipeline_df = pd.read_excel('pipe_line.xlsx')
        pipeline_item_df = pd.read_excel('pipe_line_item.xlsx')
    except UnicodeDecodeError:
        pipeline_df = pd.read_excel('pipe_line.xlsx', encoding='utf-8')
        pipeline_item_df = pd.read_excel('pipe_line_item.xlsx', encoding='utf-8')
    except Exception as e:
        logging.error("Error loading Excel files", exc_info=True)
        print("Error loading Excel files. Please check file paths and formats.")
        print(e)
        exit()  # Or handle this appropriately for your application


    pipeline_df = pipeline_df.fillna('')
    pipeline_item_df = pipeline_item_df.fillna('')

    # 3. Rename Columns (if necessary)
    #    If your Excel column names don't exactly match your database column names,
    #    you can rename them:
    #    pipeline_df.rename(columns={'ExcelColumnName': 'db_column_name'}, inplace=True)
    #    pipeline_item_df.rename(columns={'ExcelColumnName': 'db_column_name'}, inplace=True)

    # 4. Data Type Conversion (if necessary)
    #    Ensure that the data types in your DataFrames match the data types of the
    #    columns in your SQL Server tables.  For example, if you have a column that should be an integer:
    #    pipeline_df['column_name'] = pipeline_df['column_name'].astype(int)
    #    pipeline_item_df['column_name'] = pipeline_item_df['column_name'].astype(int)

    # 5. Handle 'id' column (which is an IDENTITY column) - No need to drop, just don't use it
    #if 'id' in pipeline_df.columns:
    #    print("Found 'id' column in pipeline_df. Removing...")
    #    pipeline_df = pipeline_df.drop(columns=['id'])
    #    print("pipeline_df columns after removing 'id':", pipeline_df.columns)
    #else:
    #    print("No 'id' column found in pipeline_df.")
    #    print("pipeline_df columns:", pipeline_df.columns)

    #if 'id' in pipeline_item_df.columns:
    #    print("Found 'id' column in pipeline_item_df. Removing...")
    #    pipeline_item_df = pipeline_item_df.drop(columns=['id'])
    #    print("pipeline_item_df columns after removing 'id':", pipeline_item_df.columns)
    #else:
    #    print("No 'id' column found in pipeline_item_df.")
    #    print("pipeline_item_df columns:", pipeline_item_df.columns)

    # 6. Handle Missing Foreign Keys (created_user, updated_user) and Date Columns
    #   You'll need to decide how to handle these.  For example, if you have a default user ID:
    default_user_id = 1  # Replace with your actual default user ID

    # Handle missing created_user and updated_user for pipeline_df
    if 'created_user' not in pipeline_df.columns:
        pipeline_df['created_user'] = default_user_id
    else:
        pipeline_df['created_user'] = pipeline_df['created_user'].fillna(default_user_id).astype(int)

    if 'updated_user' not in pipeline_df.columns:
        pipeline_df['updated_user'] = default_user_id
    else:
        pipeline_df['updated_user'] = pipeline_df['updated_user'].fillna(default_user_id).astype(int)

    # Handle missing created_user and updated_user for pipeline_item_df
    if 'created_user' not in pipeline_item_df.columns:
        pipeline_item_df['created_user'] = default_user_id
    else:
        pipeline_item_df['created_user'] = pipeline_item_df['created_user'].fillna(default_user_id).astype(int)

    if 'updated_user' not in pipeline_item_df.columns:
        pipeline_item_df['updated_user'] = default_user_id
    else:
        pipeline_item_df['updated_user'] = pipeline_item_df['updated_user'].fillna(default_user_id).astype(int)

    # Handle missing date columns for pipeline_df
    if 'created_date' not in pipeline_df.columns:
        pipeline_df['created_date'] = datetime.now()
    else:
        pipeline_df['created_date'] = pipeline_df['created_date'].fillna(datetime.now())

    if 'updated_date' not in pipeline_df.columns:
        pipeline_df['updated_date'] = datetime.now()
    else:
        pipeline_df['updated_date'] = pipeline_df['updated_date'].fillna(datetime.now())

    # Handle missing date columns for pipeline_item_df
    if 'created_date' not in pipeline_item_df.columns:
        pipeline_item_df['created_date'] = datetime.now()
    else:
        pipeline_item_df['created_date'] = pipeline_item_df['created_date'].fillna(datetime.now())

    if 'updated_date' not in pipeline_item_df.columns:
        pipeline_item_df['updated_date'] = datetime.now()
    else:
        pipeline_item_df['updated_date'] = pipeline_item_df['updated_date'].fillna(datetime.now())

    if 'date' not in pipeline_item_df.columns:
        pipeline_item_df['date'] = datetime.now().date()
    else:
        pipeline_item_df['date'] = pipeline_item_df['date'].fillna(datetime.now().date())

    # 8. Generate item_line numbers (CRITICAL)
    if 'pipe_line_id' in pipeline_item_df.columns:
        pipeline_item_df['item_line'] = pipeline_item_df.groupby('pipe_line_id').cumcount() + 1
    else:
        print("Error: 'pipe_line_id' column not found in pipeline_item_df. Cannot generate item_line numbers.")
        exit()  # Or handle this appropriately for your application


    # Debugging: Print DataFrames Before Insertion
    print("--- pipeline_df Before Insertion ---")
    print(pipeline_df.head())
    print(pipeline_df.columns)
    print("-----------------------------------")

    print("--- pipeline_item_df Before Insertion ---")
    print(pipeline_item_df.head())
    print(pipeline_item_df.columns)
    print("---------------------------------------")

    # 9. Upload data to SQL Server tables (APPEND instead of REPLACE)
    try:
        pipeline_df.to_sql('pipe_line', lsengine, if_exists='append', index=False)
        print("Data appended to pipe_line successfully!")
    except Exception as e:
        print(f"Error appending to pipe_line: {e}")
        # print(e)

    try:
        pipeline_item_df.to_sql('pipe_line_item', lsengine, if_exists='append', index=False)
        print("Data appended to pipe_line_item successfully!")
    except Exception as e:
        print(f"Error appending to pipe_line_item: {e}")
        print(e)
