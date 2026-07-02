import streamlit as st
import pandas as pd
import re
import os

# --- INITIALIZATION SETUP ---
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

MAX_FILE_SIZE_MB = 5  # Set max file size constraint

if 'staff_df' not in st.session_state:
    st.session_state.staff_df = pd.DataFrame(columns=[
        "Computer Number", "Full Name", "Department", "Designation", 
        "Grade Level", "Email", "Phone Number", "Credential Files", 
        "Approval Status", "Approved By"
    ])

def save_data(df):
    st.session_state.staff_df = df

# --- MAIN NAVIGATION CONTROLLER ---
menu = st.sidebar.radio("Navigation Menu", [
    "🏠 Home Dashboard", 
    "📝 Staff Registration Form", 
    "🔐 Admin Verification Panel"
])

# --- OPTION 1: HOME PAGE ---
if menu == "🏠 Home Dashboard":
    st.title("🏠 Secure Block System (SBS) Home")
    st.write("Welcome! Please use the sidebar navigation to switch between modules.")
    
    df = st.session_state.staff_df
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(df))
    col2.metric("Pending Review", len(df[df["Approval Status"] == "Pending"]))
    col3.metric("Approved Staff", len(df[df["Approval Status"] == "Approved"]))

# --- OPTION 2: STAFF REGISTRATION FORM ---
elif menu == "📝 Staff Registration Form":
    st.title("📝 Staff Credential Registration Portal")
    st.write("Please fill out your personal and professional details below.")
    
    with st.form("registration_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Legal Name", placeholder="e.g., John Doe").strip()
            computer_number = st.text_input("Computer Number (Exactly 6 Digits)", placeholder="e.g., 123456").strip()
            department = st.text_input("Department", placeholder="e.g., Human Resources").strip()
            designation = st.text_input("Designation / Job Title", placeholder="e.g., Senior Officer").strip()
            
        with col2:
            grade_level = st.selectbox("Grade Level", [f"Level {i}" for i in range(1, 18)] + ["Management", "Executive"])
            email = st.text_input("Email Address", placeholder="e.g., john.doe@company.com").strip()
            phone_number = st.text_input("Phone Number (e.g., 08012345678 or +234...)", placeholder="e.g., 08031234567").strip()
        
        uploaded_files = st.file_uploader(
            f"Upload Credential Documents (Max {MAX_FILE_SIZE_MB}MB per file)", 
            type=["pdf", "png", "jpg", "jpeg"], 
            accept_multiple_files=True
        )
        
        submit_btn = st.form_submit_button("Submit Registration for Approval")
        
        if submit_btn:
            # --- VALIDATION ENGINE WITH STRICT CONSTRAINTS ---
            
            # 1. Check for empty fields
            if not all([full_name, computer_number, department, designation, email, phone_number]):
                st.error("⚠️ All personal and professional details are required.")
            
            # 2. Full Name: Letters & spaces only
            elif not re.match(r"^[a-zA-Z\s]+$", full_name):
                st.error("❌ Invalid Name: Name must only contain letters and spaces.")
            
            # 3. Computer Number Constraint: Must be exactly 6 digits long
            elif not (computer_number.isdigit() and len(computer_number) == 6):
                st.error("❌ Constraint Error: Computer Number must be exactly 6 digits long (e.g., 123456).")
                
            # 4. Email Constraint: Basic validation
            elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                st.error("❌ Invalid Email: Please enter a valid email address.")
                
            # 5. Phone Number Constraint: Match Nigerian 0... or +234... pattern
            elif not re.match(r"^(0|\+234)[789][01]\d{8}$", phone_number.replace(" ", "")):
                st.error("❌ Constraint Error: Enter a valid Nigerian phone number (11 digits starting with 0, or 14 characters starting with +234).")
                
            # 6. Check files present
            elif not uploaded_files:
                st.error("⚠️ Please upload at least one credential document.")
                
            # 7. Check if Computer Number already exists
            elif computer_number in st.session_state.staff_df["Computer Number"].values:
                st.error(f"❌ A registration is already on file for Computer Number: {computer_number}")
                
            else:
                # 8. File Size Constraint Check
                large_file_found = False
                for f_item in uploaded_files:
                    file_size_mb = f_item.size / (1024 * 1024)
                    if file_size_mb > MAX_FILE_SIZE_MB:
                        st.error(f"❌ Constraint Error: The file `{f_item.name}` exceeds the {MAX_FILE_SIZE_MB}MB size limit ({file_size_mb:.2f}MB).")
                        large_file_found = True
                        break
                
                if not large_file_found:
                    saved_file_names = []
                    for f_item in uploaded_files:
                        safe_name = f_item.name.replace(" ", "_")
                        file_path = os.path.join(UPLOAD_DIR, safe_name)
                        
                        with open(file_path, "wb") as f:
                            f.write(f_item.getbuffer())
                        saved_file_names.append(safe_name)
                    
                    files_string = "|".join(saved_file_names)
                    
                    new_entry = {
                        "Computer Number": computer_number,
                        "Full Name": full_name,
                        "Department": department,
                        "Designation": designation,
                        "Grade Level": grade_level,
                        "Email": email,
                        "Phone Number": phone_number,
                        "Credential Files": files_string,
                        "Approval Status": "Pending",
                        "Approved By": "N/A"
                    }
                    
                    updated_df = pd.concat([st.session_state.staff_df, pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(updated_df)
                    st.success(f"🎉 Success! Registration details saved for {full_name}.")

# --- OPTION 3: ADMIN APPROVAL PANEL ---
elif menu == "🔐 Admin Verification Panel":
    st.markdown("### 🔐 Institutional Management & Verification Dashboard")
    
    staff_df = st.session_state.staff_df
    admin_password = st.sidebar.text_input("Enter Admin Verification Key", type="password")
    
    if admin_password == "SBS_Admin_2026": 
        st.write("---")
        
        if staff_df.empty:
            st.info("No registration submissions are in the system yet.")
        else:
            status_filter = st.selectbox("Filter Registry By Status", ["All", "Pending", "Approved", "Rejected"])
            df_filtered = staff_df if status_filter == "All" else staff_df[staff_df["Approval Status"] == status_filter]
            
            st.markdown("#### 📊 Current Registry Entries")
            st.dataframe(df_filtered, use_container_width=True)
            
            st.write("---")
            
            # Action Processing Section
            st.markdown("### 🛠️ Process Pending Approvals")
            pending_staff = staff_df[staff_df["Approval Status"] == "Pending"]["Computer Number"].tolist()
            
            if not pending_staff:
                st.success("✅ Excellent! There are currently zero pending submissions.")
            else:
                selected_comp_id = st.selectbox("Select Computer Number to Action", pending_staff, key="action_selector")
                row_idx = staff_df[staff_df["Computer Number"] == selected_comp_id].index[0]
                staff_details = staff_df.loc[row_idx]
                
                st.info(f"**Target Profile:** {staff_details['Full Name']} | **Dept:** {staff_details['Department']} | **Role:** {staff_details['Designation']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👍 Grant Ethical Approval", use_container_width=True, key=f"approve_{selected_comp_id}"):
                        st.session_state.staff_df.at[row_idx, "Approval Status"] = "Approved"
                        st.session_state.staff_df.at[row_idx, "Approved By"] = "Management Board"
                        st.success(f"Approved entry for {staff_details['Full Name']}")
                        st.rerun()
                        
                with col2:
                    if st.button("❌ Deny / Flag File", use_container_width=True, key=f"reject_{selected_comp_id}"):
                        files_to_delete = [f.strip() for f in staff_details['Credential Files'].split("|") if f.strip()]
                        for single_file_name in files_to_delete:
                            file_path = os.path.join(UPLOAD_DIR, single_file_name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        
                        st.session_state.staff_df.at[row_idx, "Approval Status"] = "Rejected"
                        st.session_state.staff_df.at[row_idx, "Approved By"] = "Management Board"
                        st.warning(f"Rejected submission and deleted local files for {staff_details['Full Name']}")
                        st.rerun()

            st.write("---")
            
            # Document Gallery View
            st.markdown("### 🔍 Quick-View Documents Registry")
            all_comp_list = staff_df["Computer Number"].tolist()
            selected_global_id = st.selectbox("Choose Computer Number to view files:", all_comp_list, key="global_viewer")
            
            global_idx = staff_df[staff_df["Computer Number"] == selected_global_id].index[0]
            global_details = staff_df.loc[global_idx]
            
            with st.expander(f"👁️ View Uploaded Files for: {global_details['Full Name']}", expanded=True):
                g_file_names = [f.strip() for f in global_details['Credential Files'].split("|") if f.strip()]
                
                for idx, single_file_name in enumerate(g_file_names):
                    g_file_path = os.path.join(UPLOAD_DIR, single_file_name)
                    st.write(f"📁 **File {idx+1}:** `{single_file_name}`")
                    
                    if os.path.exists(g_file_path):
                        g_file_ext = single_file_name.split(".")[-1].lower()
                        if g_file_ext in ["png", "jpg", "jpeg"]:
                            st.image(g_file_path, caption=single_file_name, use_container_width=True)
                        elif g_file_ext == "pdf":
                            with open(g_file_path, "rb") as p_file:
                                st.download_button(
                                    f"📥 Download {single_file_name}", 
                                    data=p_file.read(), 
                                    file_name=single_file_name, 
                                    key=f"gal_{selected_global_id}_{idx}"
                                )
                    else:
                        st.error(f"❌ File not found on disk (It may have been deleted during a rejection).")
                    st.write("---")
    
    elif admin_password != "":
        st.error("❌ Incorrect Security Key. Access Denied.")
    else:
        st.warning("🔒 Please supply the valid verification security key in the sidebar to manage clearances.")