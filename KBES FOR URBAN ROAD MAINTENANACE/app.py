import streamlit as st
import pandas as pd
from tooltip_data import SINGLE_TOOLTIP, MULTI_TOOLTIP
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

EXCEL_FILE = 'RULES_FINAL.xlsx'

# ---------- Styling ----------
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #0d6efd;
    }
    .stButton>button {
        background-color: #0d6efd;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    single_df = pd.read_excel(EXCEL_FILE, sheet_name='Single_Distress')
    multi_df = pd.read_excel(EXCEL_FILE, sheet_name='Multiple_Distress_Rules')
    return single_df, multi_df

def format_tooltip(entry):
    if entry:
        return f"📘 **{entry['Description']}**\n\n🧠 {entry['Guidance']}\n\n💡 {entry['Tooltip']}"
    return ""

def get_single_tooltip(field, distress, level):
    distress = distress.upper()
    level = level.upper()
    def try_keys(*keys):
        for k in keys:
            for variant in [
                k, (k[0], distress, level),
                (k[0], "ALL", level),
                (k[0], distress, "ALL"),
                (k[0], "ALL", "ALL")
            ]:
                if variant in SINGLE_TOOLTIP:
                    return format_tooltip(SINGLE_TOOLTIP[variant])
        return ""
    return try_keys((field.upper(), distress, level))

def get_multi_tooltip(field, major, minor, level):
    major, minor, level = major.upper(), minor.upper(), level.upper()
    def try_keys(*keys):
        for k in keys:
            for variant in [
                k, (k[0], major, minor, level),
                (k[0], major, minor, "ALL"),
                (k[0], major, "ALL", "ALL"),
                (k[0], "ALL", "ALL", "ALL")
            ]:
                if variant in MULTI_TOOLTIP:
                    return format_tooltip(MULTI_TOOLTIP[variant])
        return ""
    return try_keys((field.upper(), major, minor, level))

def textwrap(text, width_limit=95):
    lines = []
    while len(text) > width_limit:
        idx = text.rfind(' ', 0, width_limit)
        if idx == -1:
            idx = width_limit
        lines.append(text[:idx])
        text = text[idx:].lstrip()
    lines.append(text)
    return lines

def generate_pdf(inputs, row):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x, y = 40, height - 40
    line_height = 15

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "Urban Road Maintenance Treatment Report")
    y -= 30
    c.setFont("Helvetica", 11)

    c.drawString(x, y, "Input Parameters:")
    y -= 20
    for key, value in inputs.items():
        text = f"{key}: {str(value)}"
        for line in textwrap(text):
            c.drawString(x, y, line)
            y -= line_height

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Treatment Recommendation:")
    y -= 20
    c.setFont("Helvetica", 11)

    for label in ['Treatment', 'Procedure', 'Suggestions', 'Cost_per_m2', 'Time_Required', 'Equipment_Required', 'IRC_Code']:
        content = f"{label.replace('_', ' ')}: {str(row[label]).replace('₹', 'Rs.').replace('–', '-')}"
        for line in textwrap(content):
            c.drawString(x, y, line)
            y -= line_height
            if y < 40:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 11)

    c.save()
    buffer.seek(0)
    return buffer

def display_output(row):
    st.markdown("""
        <style>
        .justified-text {
            text-align: justify;
            line-height: 1.4;
            margin-bottom: 0.8rem;
        }
        .section-title {
            font-weight: bold;
            font-size: 1.2rem;
            margin-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="section-title">🛠️ Recommended Treatment:</div>
    <div class="justified-text"><b>{row['Treatment']}</b></div>

    <div class="section-title">📝 Procedure:</div>
    <div class="justified-text">{row['Procedure'].replace('\n', '<br>')}</div>

    <div class="section-title">💡 Suggestions:</div>
    <div class="justified-text">{row['Suggestions'].replace('\n', '<br>')}</div>

    <div class="section-title">💰 Cost per m²:</div>
    <div class="justified-text">{row['Cost_per_m2']}</div>

    <div class="section-title">⏱️ Time Required:</div>
    <div class="justified-text">{row['Time_Required']}</div>

    <div class="section-title">🧰 Equipment Required:</div>
    <div class="justified-text">{row['Equipment_Required']}</div>

    <div class="section-title">📘 IRC Code:</div>
    <div class="justified-text">{row['IRC_Code']}</div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config("Urban Road Maintenance Expert System", layout="centered")
    st.title("🏙️ Urban Road Maintenance Expert System")

    with st.expander("📘 User Manual"):
        st.markdown("""
        - Use **Single Mode** if only one distress is visible.
        - Use **Multiple Mode** if road shows more than one distress type.
        - Fill in severity, traffic, budget and other inputs.
        - Outputs include treatment, procedure, cost and IRC Code.
        """)
        try:
            with open("User_Manual.pdf", "rb") as f:
                st.download_button("📘 Download User Manual", f, file_name="User_Manual.pdf")
        except FileNotFoundError:
            st.warning("User manual not found. Please place 'User_Manual.pdf' in the project folder.")

    single_df, multi_df = load_data()
    tab1, tab2 = st.tabs(["🚧 Single Distress Mode", "🚧 Multiple Distress Mode"])

    with tab1:
        st.subheader("🔹 Input for Single Distress")
        col1, col2 = st.columns(2)
        with col1:
            distress = st.selectbox("Distress Type", single_df['Distress_Type'].unique(), key="s_distress")
            st.caption(get_single_tooltip("DISTRESS_TYPE", distress, "ALL"))

            severity = st.selectbox("Severity", single_df[single_df['Distress_Type'] == distress]['Severity'].unique(), key="s_severity")
            st.caption(get_single_tooltip("SEVERITY", distress, severity))

            traffic = st.selectbox("Traffic Type", single_df['Traffic_Type'].unique(), key="s_traffic")
            st.caption(get_single_tooltip("TRAFFIC_TYPE", distress, severity))

            budget = st.selectbox("Budget Level", single_df['Budget_Level'].unique(), key="s_budget")
            st.caption(get_single_tooltip("BUDGET_LEVEL", distress, severity))

        with col2:
            material = st.selectbox("Material Available", single_df['Material_Available'].unique(), key="s_material")
            st.caption(get_single_tooltip("MATERIAL_AVAILABLE", distress, severity))

            time_limit = st.selectbox("Time Limit", single_df['Time_Limit'].unique(), key="s_time")
            st.caption(get_single_tooltip("TIME_LIMIT", distress, severity))

            extent = st.selectbox("Extent of Distress", single_df['Extent_of_Distress'].unique(), key="s_extent")
            st.caption(get_single_tooltip("EXTENT_OF_DISTRESS", distress, severity))

        if st.button("🔍 Show Treatment (Single Mode)"):
            match = single_df[
                (single_df['Distress_Type'] == distress) &
                (single_df['Severity'] == severity) &
                (single_df['Traffic_Type'] == traffic) &
                (single_df['Budget_Level'] == budget) &
                (single_df['Material_Available'] == material) &
                (single_df['Time_Limit'] == time_limit) &
                (single_df['Extent_of_Distress'] == extent)
            ]
            if not match.empty:
                display_output(match.iloc[0])
                pdf = generate_pdf({
                    "Distress Type": distress,
                    "Severity": severity,
                    "Traffic": traffic,
                    "Budget": budget,
                    "Material": material,
                    "Time": time_limit,
                    "Extent": extent
                }, match.iloc[0])
                st.download_button("📄 Download Treatment PDF", pdf, file_name="treatment_report.pdf")
            else:
                st.warning("❌ No treatment found for this combination.")

    with tab2:
        st.subheader("🔸 Input for Multiple Distress")
        col1, col2 = st.columns(2)
        with col1:
            major = st.selectbox("Major Distress Type", multi_df['Major_Distress_Type'].unique(), key="m_major")
            st.caption(get_multi_tooltip("MAJOR_DISTRESS_TYPE", major, "ALL", "ALL"))

            minor = st.selectbox("Minor Distress Type", multi_df['Minor_Distress_Type'].unique(), key="m_minor")
            st.caption(get_multi_tooltip("MINOR_DISTRESS_TYPE", major, minor, "ALL"))

            severity = st.selectbox("Severity", multi_df[multi_df['Major_Distress_Type'] == major]['Severity'].unique(), key="m_severity")
            st.caption(get_multi_tooltip("SEVERITY", major, minor, severity))

            traffic = st.selectbox("Traffic Type", multi_df['Traffic_Type'].unique(), key="m_traffic")
            st.caption(get_multi_tooltip("TRAFFIC_TYPE", major, minor, severity))

        with col2:
            budget = st.selectbox("Budget Level", multi_df['Budget_Level'].unique(), key="m_budget")
            st.caption(get_multi_tooltip("BUDGET_LEVEL", major, minor, severity))

            material = st.selectbox("Material Available", multi_df['Material_Available'].unique(), key="m_material")
            st.caption(get_multi_tooltip("MATERIAL_AVAILABLE", major, minor, severity))

            time_limit = st.selectbox("Time Limit", multi_df['Time_Limit'].unique(), key="m_time")
            st.caption(get_multi_tooltip("TIME_LIMIT", major, minor, severity))

            extent = st.selectbox("Extent of Distress", multi_df['Extent_of_Distress'].unique(), key="m_extent")
            st.caption(get_multi_tooltip("EXTENT_OF_DISTRESS", major, minor, severity))

        if st.button("🔍 Show Treatment (Multiple Mode)"):
            match = multi_df[
                (multi_df['Major_Distress_Type'] == major) &
                (multi_df['Minor_Distress_Type'] == minor) &
                (multi_df['Severity'] == severity) &
                (multi_df['Traffic_Type'] == traffic) &
                (multi_df['Budget_Level'] == budget) &
                (multi_df['Material_Available'] == material) &
                (multi_df['Time_Limit'] == time_limit) &
                (multi_df['Extent_of_Distress'] == extent)
            ]
            if not match.empty:
                display_output(match.iloc[0])
                pdf = generate_pdf({
                    "Major Distress": major,
                    "Minor Distress": minor,
                    "Severity": severity,
                    "Traffic": traffic,
                    "Budget": budget,
                    "Material": material,
                    "Time": time_limit,
                    "Extent": extent
                }, match.iloc[0])
                st.download_button("📄 Download Treatment PDF", pdf, file_name="treatment_report.pdf")
            else:
                st.warning("❌ No treatment found for this combination.")

if __name__ == "__main__":
    main()
    