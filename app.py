import streamlit as st
import pandas as pd
import time
from logic_gemini import parse_document_dynamic
# Updated import to include the batch function
from logic_sheets import append_to_sheet, append_batch_to_sheet
from logic_drive import get_file_from_link

st.set_page_config(page_title="Y4J YouthScan App", page_icon="🇮🇳", layout="wide")
st.title("🇮🇳 Youth4Jobs Smart Scanner")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuration")
    
    sheet_url = st.text_input("Paste Google Sheet URL here:")
    if sheet_url and "xlsx" in sheet_url:
        st.error("⚠️ You pasted a link to an Excel file (.xlsx). Please convert it to a Google Sheet first (File > Save as Google Sheets).")

    default_cols = "First Name, Last Name, ID Type, ID Number, Email, PhoneNumber, DateOfBirth, Gender, DisabilityType, Qualification, State"
    cols_input = st.text_area("Columns to Extract", value=default_cols, height=150)
    target_columns = [x.strip() for x in cols_input.split(",") if x.strip()]
    
    if "gcp_service_account" in st.secrets:
        bot_email = st.secrets["gcp_service_account"]["client_email"]
        st.info(f"🤖 **Bot Email:**\n`{bot_email}`\n\n(Share Drive files with this email!)")

# --- MAIN AREA ---
tab1, tab2, tab3 = st.tabs(["📸 Camera", "📂 Upload File", "🔗 Google Drive Link"])
image_data = None
mime_type = "image/jpeg" # Default

# 1. Camera
with tab1:
    cam = st.camera_input("Take a photo")
    if cam: 
        image_data = cam.getvalue()
        mime_type = "image/jpeg"

# 2. Upload
with tab2:
    up = st.file_uploader("Upload Image/PDF", type=["jpg", "png", "jpeg", "pdf"])
    if up: 
        image_data = up.getvalue()
        mime_type = up.type

# 3. Google Drive Link
with tab3:
    st.markdown("1. Share the file with the **Bot Email** (see sidebar).")
    st.markdown("2. Paste the link below.")
    drive_link = st.text_input("Google Drive Link")
    if drive_link:
        if st.button("📥 Fetch from Drive"):
            with st.spinner("Downloading from Drive..."):
                file_bytes, detected_mime, error = get_file_from_link(drive_link)
                if error:
                    st.error(error)
                else:
                    image_data = file_bytes
                    mime_type = detected_mime
                    st.success(f"Loaded: {detected_mime}")

# --- PROCESSING ---
if image_data:
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"**Loaded Document ({mime_type})**")
        if "image" in mime_type:
            st.image(image_data, use_column_width=True)
        else:
            st.info("📄 PDF Document Loaded")
        
        if st.button("🚀 Analyze with Gemini", type="primary"):
            if not sheet_url:
                st.warning("Please enter a Google Sheet URL first.")
            else:
                with st.spinner("Gemini is analyzing..."):
                    result = parse_document_dynamic(image_data, target_columns, mime_type)
                    
                    if result and isinstance(result, list) and "error" in result[0]:
                        st.error(f"AI Error: {result[0]['error']}")
                    else:
                        st.session_state['result_df'] = pd.DataFrame(result)

    with col2:
        if 'result_df' in st.session_state:
            st.subheader("Verify Data")
            edited_df = st.data_editor(st.session_state['result_df'], num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Save ALL to Google Sheet"):
                if not sheet_url:
                     st.error("Please provide a Google Sheet URL in the sidebar.")
                else:
                    with st.spinner("Saving all rows at once..."):
                        # --- NEW BATCH LOGIC (Fixes 429 Quota Error) ---
                        # Convert DataFrame to a list of dictionaries
                        data_to_save = edited_df.to_dict('records')
                        
                        # Call the batch function instead of looping
                        success = append_batch_to_sheet(sheet_url, data_to_save)
                        
                        if success:
                            st.success(f"✅ Successfully saved {len(data_to_save)} candidates!")
                            st.balloons()
                        else:
                            st.error("Failed to save data. Check the logs.")
