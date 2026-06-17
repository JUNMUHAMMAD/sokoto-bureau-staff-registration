import streamlit as st
import pandas as pd  
import os           

# Define the CSV file and photo folder to store staff data
STAFF_DATA_FILE = 'staff_details.csv'
PHOTO_DIR = 'staff_photos'

# Ensure the photo directory exists
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

def load_staff_data():
    # Added 'Level' and 'Photo Path' to required columns
    required_columns = ['Comp Number', 'Name', 'Department/Unit', 'Designation', 'Level', 'Email', 'Phone Number', 'Photo Path']
    
    if os.path.exists(STAFF_DATA_FILE):
        df = pd.read_csv(STAFF_DATA_FILE)
        
        # Check if any required columns are missing from the existing file and add them dynamically
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            for col in missing_cols:
                df[col] = None
            df.to_csv(STAFF_DATA_FILE, index=False) # Update file structure safely
        return df
        
    # Return empty layout if file doesn't exist at all
    return pd.DataFrame(columns=required_columns)

def save_staff_data(df):
    df.to_csv(STAFF_DATA_FILE, index=False)

# --- Main App Layout ---
st.title('Sokoto State Bureau of Statistics - Staff Registration')

st.header('Register New Staff')

# Note: st.camera_input works inside st.form, but the user must click "Take Photo" before clicking "Register Staff"
with st.form('staff_registration_form'):
    comp_number = st.text_input('Comp Number', help='Unique company/computer number for the staff member')
    name = st.text_input('Full Name')
    department_unit = st.text_input('Department/Unit')
    designation = st.text_input('Designation')
    level = st.text_input('Level', help='e.g., Grade Level 08, GL 12, etc.')
    email = st.text_input('Email Address')
    phone_number = st.text_input('Phone Number')
    
    # Photo Capture Widget
    st.write("### Capture Staff Identification Photo")
    photo_file = st.camera_input("Take a snapshot")

    submitted = st.form_submit_button('Register Staff')

    if submitted:
        if comp_number and name and department_unit and designation and level and email and phone_number:
            current_df = load_staff_data()
            
            # Safe check to guarantee unique Comp Number
            if 'Comp Number' in current_df.columns and str(comp_number) in current_df['Comp Number'].astype(str).values:
                st.error(f'Comp Number {comp_number} already exists. Please use a unique number.')
            else:
                photo_path = "No Photo Saved"
                
                # If a photo was captured, save it locally to the staff_photos folder
                if photo_file is not None:
                    photo_filename = f"{str(comp_number).strip()}.png"
                    photo_path = os.path.join(PHOTO_DIR, photo_filename)
                    with open(photo_path, "wb") as f:
                        f.write(photo_file.getbuffer())
                
                new_staff = pd.DataFrame([{
                    'Comp Number': comp_number,
                    'Name': name,
                    'Department/Unit': department_unit,
                    'Designation': designation,
                    'Level': level,
                    'Email': email,
                    'Phone Number': phone_number,
                    'Photo Path': photo_path
                }])
                
                updated_df = pd.concat([current_df, new_staff], ignore_index=True)
                save_staff_data(updated_df)
                st.success(f'Staff {name} registered successfully!')
                st.rerun() # Refresh layout to show updated table immediately
        else:
            st.error('Please fill in all the details, including capturing a photo.')

# --- Display Section ---
st.header('Registered Staff Registry')
staff_df = load_staff_data()

if not staff_df.empty:
    # Display the basic interactive table
    st.subheader("Data Overview")
    display_cols = ['Comp Number', 'Name', 'Department/Unit', 'Designation', 'Level', 'Email', 'Phone Number']
    valid_display_cols = [col for col in display_cols if col in staff_df.columns]
    st.dataframe(staff_df[valid_display_cols], use_container_width=True)
    
    # Render rich Profile view with Photos
    st.subheader("Staff Profiles & Identification")
    for index, row in staff_df.iterrows():
        # Create a visually clean card interface using Streamlit columns
        with st.container(border=True):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Check if file exists, show a fallback if it doesn't
                if pd.notna(row.get('Photo Path')) and os.path.exists(str(row['Photo Path'])):
                    st.image(row['Photo Path'], width=130)
                else:
                    st.image("https://cdn-icons-png.flaticon.com/512/149/149071.png", width=130) # Default profile avatar
                    
            with col2:
                st.markdown(f"### **{row['Name']}**")
                st.markdown(f"**Comp Number:** {row['Comp Number']} | **Level:** {row['Level']}")
                st.markdown(f"**Dept/Unit:** {row['Department/Unit']} | **Designation:** {row['Designation']}")
                st.markdown(f"**Contact:** {row['Email']} / {row['Phone Number']}")
else:
    st.info('No staff registered yet.')