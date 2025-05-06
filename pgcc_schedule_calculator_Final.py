import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape


st.set_page_config(layout="wide")

RATIO_MAP = {
    "Lecture": {"ratio": "2:1", "minutes_per_credit": 37.5},
    "Lab": {"ratio": "2:1", "minutes_per_credit": 37.5},
    "Lab (nursing, allied health, some science courses, some music courses; ratio: 3:1)": {"ratio": "3:1", "minutes_per_credit": 50},
    "Studio": {"ratio": "2:1", "minutes_per_credit": 37.5},
    "Nursing": {"ratio": "3:1", "minutes_per_credit": 50},
    "Allied Health": {"ratio": "3:1", "minutes_per_credit": 50},
    "Clinical": {"ratio": "3:0", "minutes_per_credit": 37.5},
    "Fieldwork": {"ratio": "3:0", "minutes_per_credit": 37.5},
    "Private Lesson": {"ratio": "1:1", "minutes_per_credit": 25},
}

def remove_class(index):
    if 0 <= index < len(st.session_state.all_classes):
        st.session_state.all_classes.pop(index)

if "all_classes" not in st.session_state:
    st.session_state.all_classes = []

st.title("📘 PGCC Schedule Calculator")

with st.expander("ℹ️ How to Use This Calculator", expanded=False):
    st.markdown("""
    **NOTE:** The credit hour ratio varies by instructional method. Below is an overview of the standard breakdown. Some courses will have a different breakdown due to outside accreditation requirements. Breakdowns for courses in Nursing and Allied Health need to be verified with the Dean of Health, Wellness, and Culinary Arts to ensure accreditation standards are met.

    **How to schedule your class:**
    1. Select your class modalities  
    2. Select semester duration  
    3. Enter the start time of your class  
    4. Enter the number of credits for each modality  
    5. Select 'Add Class'  
    """)


with st.form("class_form"):
    st.subheader("Enter Class Information")
    custom_name = st.text_input("Class Name")

    st.markdown("### Enter Credits for Each Modality")
    credit_inputs = {}
    selected_modalities = []
    for modality in RATIO_MAP:
        credits = st.number_input(f"Credits for {modality}", min_value=0.0, step=0.5, key=f"credits_{modality}")
        if credits > 0:
            credit_inputs[modality] = credits
            selected_modalities.append(modality)

    weeks = st.selectbox("Select Number of Weeks", options=[5, 7, 15])
    start_time = st.text_input("Enter Start Time (HH:MM AM/PM)", value="08:00 AM")
    days_of_week = st.multiselect("Select Day(s) of the Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    if st.form_submit_button("Add Class"):
        if not selected_modalities:
            st.warning("Please enter credits for at least one modality.")
        elif not days_of_week:
            st.warning("Please select at least one day.")
        else:
            try:
                start_dt = datetime.strptime(start_time, "%I:%M %p")
            except ValueError:
                st.error("Invalid time format. Use HH:MM AM/PM.")
            else:
                total_weekly_minutes = 0
                total_credits = 0
                for modality, credits in credit_inputs.items():
                    total_credits += credits
                    total_weekly_minutes += RATIO_MAP[modality]["minutes_per_credit"] * credits

                rounded_weekly = round(total_weekly_minutes / 5) * 5

                breaks = 0
                break_minutes = 0
                if 120 <= rounded_weekly < 240:
                    breaks, break_minutes = 1, 15
                elif 240 <= rounded_weekly < 360:
                    breaks, break_minutes = 2, 60

                weekly_with_breaks = rounded_weekly + break_minutes
                total_course_minutes = weekly_with_breaks * weeks
                end_dt = start_dt + timedelta(minutes=weekly_with_breaks)

                modality_str = ', '.join(f"{mod} ({RATIO_MAP[mod]['ratio']}) - {credit_inputs[mod]}cr" for mod in selected_modalities)

                new_class = {
                    "Custom Name": custom_name,
                    "Course Modality(s)": modality_str,
                    "Credits": total_credits,
                    "Weeks": weeks,
                    "Day(s)": ', '.join(days_of_week),
                    "Start Time": start_dt.strftime("%I:%M %p"),
                    "End Time": end_dt.strftime("%I:%M %p"),
                    "Class Duration": f"{rounded_weekly} min/week",
                    "Breaks": f"{breaks} break(s), {break_minutes} min" if breaks else "None",
                    "Total Course Time": f"{total_course_minutes} min",
                    "Start (raw)": start_dt,
                    "End (raw)": end_dt
                }
                st.session_state.all_classes.append(new_class)
                st.success("Class(es) added!")


if st.session_state.all_classes:
    st.subheader("Class Session Duration Table")
    
df = pd.DataFrame(st.session_state.all_classes)

for i, class_info in enumerate(st.session_state.all_classes):
    with st.expander(f"📘 {class_info['Custom Name']} ({class_info['Start Time']} - {class_info['End Time']})", expanded=True):
        st.write(pd.DataFrame([class_info]).drop(columns=["Start (raw)", "End (raw)"], errors="ignore"))
        if st.button(f"❌ Remove '{class_info['Custom Name']}'", key=f"remove_{i}"):
            remove_class(i)
            st.experimental_rerun()
df_export = df.drop(columns=["Start (raw)", "End (raw)"], errors='ignore')

# Excel Download
excel_buffer = BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    df_export.to_excel(writer, index=False)
excel_buffer.seek(0)


# CSV Download
st.download_button(
    "Download Schedule (CSV)",
    data=df_export.to_csv(index=False),
    file_name="pgcc_schedule.csv",
    mime="text/csv"
)

# PDF Download
def generate_pdf(dataframe):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))  # ← landscape mode
    elements = []

    data = [list(dataframe.columns)] + dataframe.values.tolist()
    table = Table(data, repeatRows=1)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ])
    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

if not df_export.empty:
    pdf_data = generate_pdf(df_export)
    st.download_button("Download Schedule (PDF)", data=pdf_data, file_name="pgcc_schedule.pdf", mime="application/pdf")
else:
    st.warning("No data available to export as PDF.")

# Only export if DataFrame isn't empty
if not df_export.empty:
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False)
    excel_buffer.seek(0)

    st.download_button(
        label="Download Schedule (Excel)",
        data=excel_buffer,
        file_name="pgcc_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("No data available to export as Excel.")

# Use just one display table (collapsible)
with st.expander("📊 View Full Class Duration Table", expanded=False):
    df_display = df.drop(columns=["Start (raw)", "End (raw)"], errors='ignore')
    st.dataframe(df_display, use_container_width=True)

# Clean up DataFrame
df_export = df.drop(columns=["Start (raw)", "End (raw)"], errors='ignore')

# Display a summary table at the bottom with only course name, start time, and end time
if not df.empty:
    summary_df = df[["Custom Name", "Start Time", "End Time"]]
    st.subheader(" Class Time Summary")
    st.dataframe(summary_df, use_container_width=True)
