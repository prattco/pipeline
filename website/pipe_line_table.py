import pandas as pd
from sqlalchemy import create_engine
import localsqlcred  # your credential file

lsdsn = "mssql+pyodbc://" + localsqlcred.lsDBUSER + ":" + localsqlcred.lsDBPW + "@" + localsqlcred.lsDBSERVER + localsqlcred.lsDBNAME + "?driver=" + localsqlcred.lsDBDRIVER
lsengine = create_engine(lsdsn)

excel_file = 'pipe_line.xlsx'  # Store the filename in a variable

try:
    df = pd.read_excel(excel_file)

    # Remove the 'id' column if it exists (important for IDENTITY columns)
    if 'id' in df.columns:
        df = df.drop('id', axis=1)

    df.to_sql('pipe_line', lsengine, if_exists='append', index=False, chunksize=1000) #add chunksize

    print("Data inserted successfully.")

except FileNotFoundError:
    print(f"Error: Excel file '{excel_file}' not found.")
except Exception as e:
    print(f"An error occurred: {e}")