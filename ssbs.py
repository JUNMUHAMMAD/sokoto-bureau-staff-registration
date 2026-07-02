import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
import os

# --- INITIALIZATION SETUP ---
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

MAX_FILE_SIZE_MB = 5

# --- ESTABLISH GOOGLE SHEETS CONNECTION ---
# This looks for the URL inside your deployment configuration
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Read existing entries from the Google Sheet
    staff_df = conn.read(ttl="5s") # Refreshes cache every 5 seconds
except Exception:
    # Fallback to prevent crash if sheet is not yet linked
    staff_df = pd.DataFrame(columns=[
        "Computer Number", "Full Name", "Department", "Designation", 
        "Grade Level", "Email", "Phone Number", "Credential Files", 
        "Approval Status", "Approved By"
    ])

# Helper function to push data updates back to Google Sheets
def save_to_google_sheets(updated_df):
    try:
        conn.update(data=updated_df)
        st.cache_data.clear() # Clear streamlit cache to show immediate updates
    except Exception as e:
        st.error(f"Failed to sync with database: {e}")

# --- MAIN NAVIGATION CONTROLLER ---
menu = st.sidebar.radio("Navigation Menu", [
    "🏠 Home Dashboard", 
    "📝 Staff Registration Form", 
    "🔐 Admin Verification Panel"
])

# --- OPTION 1: HOME PAGE ---
if menu == "🏠 Home Dashboard":
    st.title("🏠 Secure Block System (SBS) Home")
    st.write("Welcome! This database is actively connected to cloud storage.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(staff_df))
    col2.metric("Pending Review", len(staff_df[staff_df["Approval Status"] == "Pending"]))
    col3.metric("Approved Staff", len(staff_df[staff_df["Approval Status"] == "Approved"]))

# --- OPTION 2: STAFF REGISTRATION FORM ---
elif menu == "📝 Staff Registration Form":
    st.title("📝 Staff Credential Registration Portal")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Legal Name").strip()
            computer_number = st.text_input("Computer Number (Exactly 6 Digits)").strip()
            department = st.text_input("Department").strip()
            designation = st.text_input("Designation / Job Title").strip()
        with col2:
            grade_level = st.selectbox("Grade Level", [f"Level {i}" for i in range(1, 18)] + ["Management", "Executive"])
            email = st.text_input("Email Address").strip()
            phone_number = st.text_input("Phone Number").strip()
        
        uploaded_files = st.file_uploader("Upload Credential Documents", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
        submit_btn = st.form_submit_button("Submit Registration")
        
        if submit_btn:
            if not all([full_name, computer_number, department, designation, email, phone_number]):
                st.error("⚠️ All fields are required.")
            elif not re.match(r"^[a-zA-Z\s]+$", full_name):
                st.error("❌ Invalid Name.")
            elif not (computer_number.isdigit() and len(computer_number) == 6):
                st.error("❌ Computer Number must be exactly 6 digits.")
            elif not re.match(r"^(0|\+234)[789][01]\d{8}$", phone_number.replace(" ", "")):
                st.error("❌ Invalid Nigerian Phone Number.")
            elif not uploaded_files:
                st.error("⚠️ Please upload documents.")
            elif not staff_df.empty and computer_number in staff_df["Computer Number"].astype(str).values:
                st.error("❌ This Computer Number has already registered.")
            else:
                saved_file_names = []
                for f_item in uploaded_files:
                    safe_name = f_item.name.replace(" ", "_")
                    with open(os.path.join(UPLOAD_DIR, safe_name), "wb") as f:
                        f.write(f_item.getbuffer())
                    saved_file_names.append(safe_name)
                
                new_entry = pd.DataFrame([{
                    "Computer Number": computer_number,
                    "Full Name": full_name,
                    "Department": department,
                    "Designation": designation,
                    "Grade Level": grade_level,
                    "Email": email,
                    "Phone Number": phone_number,
                    "Credential Files": "|".join(saved_file_names),
                    "Approval Status": "Pending",
                    "Approved By": "N/A"
                }])
                
                new_df = pd.concat([staff_df, new_entry], ignore_index=True)
                save_to_google_sheets(new_df)
                st.success("🎉 Registration saved to cloud registry!")
                st.rerun()

# --- OPTION 3: ADMIN APPROVAL PANEL ---
elif menu == "🔐 Admin Verification Panel":
    st.markdown("### 🔐 Institutional Management & Verification Dashboard")
    admin_password = st.sidebar.text_input("Enter Admin Verification Key", type="password")
    
    if admin_password == "SBS_Admin_2026":
        if staff_df.empty:
            st.info("No entries found.")
        else:
            status_filter = st.selectbox("Filter Registry By Status", ["All", "Pending", "Approved", "Rejected"])
            df_filtered = staff_df if status_filter == "All" else staff_df[staff_df["Approval Status"] == status_filter]
            st.dataframe(df_filtered, use_container_width=True)
            
            st.markdown("### 🛠️ Process Pending Approvals")
            pending_staff = staff_df[staff_df["Approval Status"] == "Pending"]["Computer Number"].tolist()
            
            if not pending_staff:
                st.success("✅ No pending submissions.")
            else:
                selected_comp_id = st.selectbox("Select Computer Number", pending_staff)
                row_idx = staff_df[staff_df["Computer Number"].astype(str) == str(selected_comp_id)].index[0]
                staff_details = staff_df.loc[row_idx]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👍 Grant Approval", use_container_width=True, key=f"app_{selected_comp_id}"):
                        staff_df.at[row_idx, "Approval Status"] = "Approved"
                        staff_df.at[row_idx, "Approved By"] = "Management Board"
                        save_to_google_sheets(staff_df)
                        st.success("Approved!")
                        st.rerun()
                with col2:
                    if st.button("❌ Deny & Delete Files", use_container_width=True, key=f"rej_{selected_comp_id}"):
                        files_to_delete = [f.strip() for f in str(staff_details['Credential Files']).split("|") if f.strip()]
                        for f_name in files_to_delete:
                            file_path = os.path.join(UPLOAD_DIR, f_name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        
                        staff_df.at[row_idx, "Approval Status"] = "Rejected"
                        staff_df.at[row_idx, "Approved By"] = "Management Board"
                        save_to_google_sheets(staff_df)
                        st.warning("Rejected and removed files.")
                        st.rerun()
                        
            # Document Preview Gallery
            st.markdown("### 🔍 Quick-View Documents Registry")
            all_comp_list = staff_df["Computer Number"].tolist()
            selected_global_id = st.selectbox("Choose Computer Number to view files:", all_comp_list, key="global_viewer")
            global_idx = staff_df[staff_df["Computer Number"].astype(str) == str(selected_global_id)].index[0]
            global_details = staff_df.loc[global_idx]
            
            with st.expander(f"👁️ View Files for: {global_details['Full Name']}", expanded=True):
                g_file_names = [f.strip() for f in str(global_details['Credential Files']).split("|") if f.strip()]
                for idx, single_file_name in enumerate(g_file_names):
                    g_file_path = os.path.join(UPLOAD_DIR, single_file_name)
                    st.write(f"📁 **File {idx+1}:** `{single_file_name}`")
                    if os.path.exists(g_file_path):
                        if single_file_name.split(".")[-1].lower() in ["png", "jpg", "jpeg"]:
                            st.image(g_file_path, use_container_width=True)
                        else:
                            with open(g_file_path, "rb") as p_file:
                                st.download_button(f"📥 Download {single_file_name}", data=p_file.read(), file_name=single_file_name, key=f"g_{idx}")
                    else:
                        st.error("❌ Physical file not found locally on server storage.")
    elif admin_password != "":
        st.error("❌ Incorrect Security Key.")