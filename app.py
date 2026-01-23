import streamlit as st
import pandas as pd
from logic_gemini import parse_document_dynamic
from logic_sheets import append_batch_to_sheet, get_or_create_spreadsheet
from logic_drive import get_file_from_link

st.set_page_config(page_title="Y4J YouthScan App", page_icon="🇮🇳", layout="wide")
st.title("🇮🇳 Youth4Jobs Smart Scanner")

# --- SESSION STATE ---
if 'drive_data' not in st.session_state: st.session_state['drive_data'] = None
if 'drive_mime' not in st.session_state: st.session_state['drive_mime'] = None

def clear_drive_data():
    st.session_state['drive_data'] = None
    st.session_state['drive_mime'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Output Settings")
    
    sheet_name = st.text_input("Spreadsheet Name", value="Youth4Jobs_Candidates")
    
    with st.expander("📂 Change Drive Folder"):
        # Default Folder from your Y4J app
        default_folder = "1Vavl3N2vLsJtIY7xdsrjB_fi2LMS1tfU"
        folder_id = st.text_input("Target Drive Folder ID", value=default_folder)

    st.header("2. Data Extraction")
    default_cols = "First Name, Last Name, ID Type, ID Number, Email, PhoneNumber, DateOfBirth, Gender, DisabilityType, Qualification, State"
    cols_input = st.text_area("Columns to Extract", value=default_cols, height=100)
    target_columns = [x.strip() for x in cols_input.split(",") if x.strip()]

# --- MAIN AREA ---
tab1, tab2, tab3 = st.tabs(["📸 Camera", "📂 Upload File", "🔗 Google Drive Link"])

active_image_data = None
active_mime_type = "image/jpeg"

# 1. Camera
with tab1:
    cam = st.camera_input("Take a photo", on_change=clear_drive_data, key="cam_widget")

# 2. Upload
with tab2:
    up = st.file_uploader("Upload Image/PDF", type=["jpg", "png", "jpeg", "pdf"], 
                          on_change=clear_drive_data, key="up_widget")

# 3. Drive Link
with tab3:
    st.markdown("Paste a link to a file in Google Drive.")
    drive_link = st.text_input("Google Drive Link")
    if drive_link:
        if st.button("📥 Fetch from Drive"):
            with st.spinner("Downloading..."):
                file_bytes, detected_mime, error = get_file_from_link(drive_link)
                if error:
                    st.error(error)
                else:
                    st.session_state['drive_data'] = file_bytes
                    st.session_state['drive_mime'] = detected_mime
                    st.success(f"Loaded: {detected_mime}")

# --- DETERMINE SOURCE ---
if st.session_state['drive_data'] is not None:
    active_image_data = st.session_state['drive_data']
    active_mime_type = st.session_state['drive_mime']
elif up:
    active_image_data = up.getvalue()
    active_mime_type = up.type
elif cam:
    active_image_data = cam.getvalue()
    active_mime_type = "image/jpeg"

# --- PROCESSING ---
if active_image_data:
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"**Loaded Document ({active_mime_type})**")
        if "image" in active_mime_type:
            st.image(active_image_data, use_column_width=True)
        else:
            st.info("📄 PDF Document Loaded")
        
        if st.button("🚀 Analyze with Gemini", type="primary"):
            with st.spinner("Gemini is analyzing..."):
                result = parse_document_dynamic(active_image_data, target_columns, active_mime_type)
                
                if result and isinstance(result, list) and "error" in result[0]:
                    st.error(f"AI Error: {result[0]['error']}")
                else:
                    st.session_state['result_df'] = pd.DataFrame(result)

    with col2:
        if 'result_df' in st.session_state:
            st.subheader("Verify Data")
            edited_df = st.data_editor(st.session_state['result_df'], num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Save to Google Sheet"):
                if not sheet_name:
                    st.error("Enter a Spreadsheet Name.")
                else:
                    with st.spinner(f"Saving to '{sheet_name}'..."):
                        # Uses the new Refresh Token Logic
                        sheet_url = get_or_create_spreadsheet(sheet_name, folder_id if folder_id else None)
                        
                        if sheet_url:
                            data_to_save = edited_df.to_dict('records')
                            if append_batch_to_sheet(sheet_url, data_to_save):
                                st.success(f"✅ Saved to **{sheet_name}**!")
                                st.balloons()
                                st.markdown(f"[Open Spreadsheet]({sheet_url})")
                        else:
                            st.error("Failed to access spreadsheet.")
