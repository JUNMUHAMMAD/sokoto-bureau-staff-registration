import streamlit as st
import pandas as pd
import re
import os
from sqlalchemy import text  # Required for modern Streamlit/SQLAlchemy execution

# --- INITIALIZATION SETUP ---
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

MAX_FILE_SIZE_MB = 5

# --- ESTABLISH POSTGRESQL CONNECTION ---
try:
    conn = st.connection("postgresql", type="sql")
    
    # Query the existing table
    raw_df = conn.query("SELECT * FROM staff_registry;", ttl="2s")
    
    if raw_df is None or raw_df.empty:
        staff_df = pd.DataFrame(columns=[
            "computer_number", "full_name", "department", "designation", 
            "grade_level", "email", "phone_number", "credential_files", 
            "approval_status", "approved_by"
        ])
    else:
        staff_df = raw_df.dropna(how="all")
except Exception as e:
    st.error(f"Postgres Connection Error: {e}")
    st.info("💡 Make sure your PostgreSQL database has a table named 'staff_registry' with the correct columns.")
    staff_df = pd.DataFrame(columns=[
        "computer_number", "full_name", "department", "designation", 
        "grade_level", "email", "phone_number", "credential_files", 
        "approval_status", "approved_by"
    ])

# --- MAIN NAVIGATION CONTROLLER ---
menu = st.sidebar.radio("Navigation Menu", [
    "🏠 Home Dashboard", 
    "📝 Staff Registration Form", 
    "🔐 Admin Verification Panel"
])

# --- OPTION 1: HOME PAGE ---
if menu == "🏠 Home Dashboard":
    st.title("🏠 Secure Block System (SBS) Home")
    st.write("Welcome! This system is actively connected to your Postgres production database.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(staff_df))
    col2.metric("Pending Review", len(staff_df[staff_df["approval_status"] == "Pending"]) if "approval_status" in staff_df else 0)
    col3.metric("Approved Staff", len(staff_df[staff_df["approval_status"] == "Approved"]) if "approval_status" in staff_df else 0)

# --- OPTION 2: STAFF REGISTRATION FORM ---
elif menu == "📝 Staff Registration Form":
    st.title("📝 Staff Credential Registration Portal")
    
    # Removed clear_on_submit=True to preserve user input during validation errors
    with st.form("registration_form"):
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
                st.error("❌ Invalid Name: Characters only.")
            elif not (computer_number.isdigit() and len(computer_number) == 6):
                st.error("❌ Computer Number must be exactly 6 digits.")
            elif not re.match(r"^(0|\+234)[789][01]\d{8}$", phone_number.replace(" ", "")):
                st.error("❌ Invalid Nigerian Phone Number layout.")
            elif not uploaded_files:
                st.error("⚠️ Please upload documents.")
            elif not staff_df.empty and str(computer_number) in staff_df["computer_number"].astype(str).values:
                st.error("❌ This Computer Number has already registered.")
            else:
                saved_file_names = []
                for f_item in uploaded_files:
                    # Prefix file names with computer number to avoid overwriting matching filenames
                    safe_name = f"{computer_number}_{f_item.name.replace(' ', '_')}"
                    with open(os.path.join(UPLOAD_DIR, safe_name), "wb") as f:
                        f.write(f_item.getbuffer())
                    saved_file_names.append(safe_name)
                
                try:
                    with conn.session as session:
                        sql = """
                        INSERT INTO staff_registry (computer_number, full_name, department, designation, grade_level, email, phone_number, credential_files, approval_status, approved_by)
                        VALUES (:comp, :name, :dept, :desig, :grade, :email, :phone, :files, 'Pending', 'N/A');
                        """
                        # Wrapped query inside text() for SQLAlchemy compatibility
                        session.execute(text(sql), {
                            "comp": str(computer_number), "name": full_name, "dept": department,
                            "desig": designation, "grade": grade_level, "email": email,
                            "phone": phone_number, "files": "|".join(saved_file_names)
                        })
                        session.commit()
                    st.cache_data.clear()
                    st.success("🎉 Registration saved directly to Postgres Cloud!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Database write failure: {ex}")

# --- OPTION 3: ADMIN APPROVAL PANEL ---
elif menu == "🔐 Admin Verification Panel":
    st.markdown("### 🔐 Institutional Management & Verification Dashboard")
    admin_password = st.sidebar.text_input("Enter Admin Verification Key", type="password")
    
    # Securing password check via st.secrets fallback
    expected_password = st.secrets.get("ADMIN_PASSWORD", "SBS_Admin_2026")
    
    if admin_password == expected_password:
        if staff_df.empty:
            st.info("No entries found in the database.")
        else:
            status_filter = st.selectbox("Filter Registry By Status", ["All", "Pending", "Approved", "Rejected"])
            df_filtered = staff_df if status_filter == "All" else staff_df[staff_df["approval_status"] == status_filter]
            st.dataframe(df_filtered, use_container_width=True)
            
            st.markdown("### 🛠️ Process Pending Approvals")
            pending_staff = staff_df[staff_df["approval_status"] == "Pending"]["computer_number"].tolist()
            
            if not pending_staff:
                st.success("✅ No pending submissions.")
            else:
                selected_comp_id = st.selectbox("Select Computer Number", pending_staff)
                row_idx = staff_df[staff_df["computer_number"].astype(str) == str(selected_comp_id)].index[0]
                staff_details = staff_df.loc[row_idx]
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👍 Grant Approval", use_container_width=True, key=f"app_{selected_comp_id}"):
                        try:
                            with conn.session as session:
                                session.execute(
                                    text("UPDATE staff_registry SET approval_status = 'Approved', approved_by = 'Management Board' WHERE computer_number = :comp;"),
                                    {"comp": str(selected_comp_id)}
                                )
                                session.commit()
                            st.cache_data.clear()
                            st.success("Approved status updated!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Failed to update database: {ex}")
                            
                with col2:
                    if st.button("❌ Deny & Delete Files", use_container_width=True, key=f"rej_{selected_comp_id}"):
                        files_to_delete = [f.strip() for f in str(staff_details['credential_files']).split("|") if f.strip()]
                        for f_name in files_to_delete:
                            file_path = os.path.join(UPLOAD_DIR, f_name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        
                        try:
                            with conn.session as session:
                                session.execute(
                                    text("UPDATE staff_registry SET approval_status = 'Rejected', approved_by = 'Management Board' WHERE computer_number = :comp;"),
                                    {"comp": str(selected_comp_id)}
                                )
                                session.commit()
                            st.cache_data.clear()
                            st.warning("Submission rejected and files removed.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Failed to update database: {ex}")
                        
            # Document Preview Gallery
            st.markdown("### 🔍 Quick-View Documents Registry")
            all_comp_list = staff_df["computer_number"].tolist()
            selected_global_id = st.selectbox("Choose Computer Number to view files:", all_comp_list, key="global_viewer")
            global_idx = staff_df[staff_df["computer_number"].astype(str) == str(selected_global_id)].index[0]
            global_details = staff_df.loc[global_idx]
            
            with st.expander(f"👁️ View Files for: {global_details['full_name']}", expanded=True):
                g_file_names = [f.strip() for f in str(global_details['credential_files']).split("|") if f.strip()]
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