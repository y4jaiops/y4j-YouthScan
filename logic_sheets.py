import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def _get_gspread_client():
    """Helper to authenticate and return the gspread client."""
    if "gcp_service_account" not in st.secrets:
        st.error("Google Cloud Secrets missing in .streamlit/secrets.toml")
        return None

    # Authenticate using the modern google-auth library
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def append_to_sheet(sheet_url, data_dict):
    """
    Appends a single row to the sheet.
    (Kept for backward compatibility, but batching is preferred).
    """
    try:
        client = _get_gspread_client()
        if not client: return False

        # Open Sheet
        sheet = client.open_by_url(sheet_url).sheet1
        
        # If sheet is empty, add headers first
        if not sheet.row_values(1):
            sheet.append_row(list(data_dict.keys()))
            
        # Ensure we write data in the same order as the headers
        headers = sheet.row_values(1)
        row_to_add = [data_dict.get(h, "") for h in headers]
        
        sheet.append_row(row_to_add)
        return True
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
        return False

def append_batch_to_sheet(sheet_url, list_of_dicts):
    """
    Appends multiple rows at once to avoid API Quota limits.
    """
    if not list_of_dicts:
        return True

    try:
        client = _get_gspread_client()
        if not client: return False

        # Open Sheet
        sheet = client.open_by_url(sheet_url).sheet1
        
        # 1. Handle Headers
        existing_headers = sheet.row_values(1)
        
        if not existing_headers:
            # Sheet is empty, create headers from the first record
            headers = list(list_of_dicts[0].keys())
            sheet.append_row(headers)
        else:
            headers = existing_headers

        # 2. Align all data to the headers
        rows_to_add = []
        for data in list_of_dicts:
            # For every header col, grab value from dict, or "" if missing
            row = [data.get(h, "") for h in headers]
            rows_to_add.append(row)
        
        # 3. Batch Append (One single API call)
        sheet.append_rows(rows_to_add)
        return True

    except Exception as e:
        st.error(f"Google Sheet Batch Error: {e}")
        return False
