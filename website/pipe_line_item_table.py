import pandas as pd
from sqlalchemy import create_engine
import localsqlcred  # your credential file

lsdsn = "mssql+pyodbc://" + localsqlcred.lsDBUSER + ":" + localsqlcred.lsDBPW + "@" + localsqlcred.lsDBSERVER + localsqlcred.lsDBNAME + "?driver=" + localsqlcred.lsDBDRIVER
lsengine = create_engine(lsdsn)

excel_file = 'pipe_line_item.xlsx'  # Store the filename in a variable

try:
    df = pd.read_excel(excel_file)

    # Remove the 'id' column if it exists (important for IDENTITY columns)
    if 'id' in df.columns:
        df = df.drop('id', axis=1)

    # Generate item_line numbers based on pipe_line_id
    if 'item_line' in df.columns:
        df = df.drop('item_line', axis =1) #remove item_line from excel.

    df['item_line'] = df.groupby('pipe_line_id').cumcount() + 1

    df.to_sql('pipe_line_item', lsengine, if_exists='append', index=False, chunksize=1000)

    print("Data inserted successfully.")

except FileNotFoundError:
    print(f"Error: Excel file '{excel_file}' not found.")
except Exception as e:
    print(f"An error occurred: {e}")