# app.py
import os
import io
import re
from pathlib import Path

import streamlit as st
import pandas as pd
from tooltip_data import SINGLE_TOOLTIP, MULTI_TOOLTIP
# Page config must be set before other streamlit UI
st.set_page_config(page_title="Urban Road Maintenance Expert System", layout="wide")

# External video (YouTube)
video_url = "https://youtu.be/bTLjaZDj3S8"

st.subheader("📺 User Guide Video")
st.write("Watch this video for a complete walkthrough of the application features.")
st.video(video_url)

# Force headings black
st.markdown(
    """
    <style>
    h1, h2, h3, h4, h5, h6 {
        color: black !important;
    }
    div[data-testid$="-label"] {
        color: black !important;
        font-weight: bold !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ReportLab (for nicer PDF formatting)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------- CONFIG ----------------
EXCEL_FILE = "RULES_FINAL.xlsx"
FONT_FOLDER = Path("fonts")
NOTO_TTF = FONT_FOLDER / "NotoSans-Regular.ttf"
PAGE_SIZE = A4

# ----------------- FONT REGISTRATION -----------------
FONT_NAME = "NotoSans"
if NOTO_TTF.exists():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(NOTO_TTF)))
        pdfmetrics.registerFont(TTFont('NotoSans', 'fonts/NotoSans-Regular.ttf'))
        pdfmetrics.registerFont(TTFont('NotoSans-Bold', 'fonts/NotoSans-Bold.ttf'))
        font_available = True
    except Exception as e:
        font_available = False
        st.warning(f"Could not register font {NOTO_TTF}: {e}")
else:
    font_available = False
    st.warning("Font file not found at 'fonts/NotoSans-Regular.ttf'. PDF will use default font.")

# CSS to try to use same font in the Streamlit UI (best-effort)
if font_available:
    # We'll embed a relative url to the font - Streamlit may not allow direct ttf linking,
    # but this gives some UI consistency on local runs. If it doesn't work in deploy, UI falls back.
    st.markdown(
        f"""
    <style>
    @font-face {{
        font-family: '{FONT_NAME}';
        src: local('{FONT_NAME}'), url('/fonts/{NOTO_TTF.name}') format('truetype');
    }}
    html, body, [class*="css"] {{
        font-family: '{FONT_NAME}', sans-serif;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

# ----------------- STYLES -----------------
st.markdown(
    """
<style>
.main {
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 10px;
}
h1, h2, h3 { color: #0d6efd; }
.stButton>button { background-color: #0d6efd; color: white; }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------- DATA LOADING -----------------
@st.cache_data
def load_data():
    if not Path(EXCEL_FILE).exists():
        raise FileNotFoundError(f"Excel rules file not found at '{EXCEL_FILE}'")
    single_df = pd.read_excel(EXCEL_FILE, sheet_name="Single_Distress")
    multi_df = pd.read_excel(EXCEL_FILE, sheet_name="Multiple_Distress_Rules")
    return single_df, multi_df


def safe_upper(x):
    try:
        return str(x).upper()
    except Exception:
        return str(x)


# ----------------- TOOLTIP FORMATTERS -----------------
def format_tooltip(entry):
    if entry:
        return f"📘 **{entry.get('Description','')}**\n\n🧠 {entry.get('Guidance','')}\n\n💡 {entry.get('Tooltip','')}"
    return ""


def get_single_tooltip(field, distress, level):
    distress, level = safe_upper(distress), safe_upper(level)

    def try_keys(*keys):
        for k in keys:
            for variant in [
                (k[0], distress, level),
                (k[0], "ALL", level),
                (k[0], distress, "ALL"),
                (k[0], "ALL", "ALL"),
            ]:
                if variant in SINGLE_TOOLTIP:
                    return format_tooltip(SINGLE_TOOLTIP[variant])
        return ""

    return try_keys((field.upper(), distress, level))


def get_multi_tooltip(field, major, minor, level):
    major, minor, level = safe_upper(major), safe_upper(minor), safe_upper(level)

    def try_keys(*keys):
        for k in keys:
            for variant in [
                (k[0], major, minor, level),
                (k[0], major, minor, "ALL"),
                (k[0], major, "ALL", "ALL"),
                (k[0], "ALL", "ALL", "ALL"),
            ]:
                if variant in MULTI_TOOLTIP:
                    return format_tooltip(MULTI_TOOLTIP[variant])
        return ""

    return try_keys((field.upper(), major, minor, level))

# Font config
FONT_NAME = "NotoSans"
font_available = False

# Build font path (works in local and deployed environments)
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSans-Regular.ttf")
FONT_BOLD_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSans-Bold.ttf")

try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
        font_available = True
    if os.path.exists(FONT_BOLD_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME + "-Bold", FONT_BOLD_PATH))
except Exception as e:
    print(f"⚠ Could not register font: {e}")
    
# ----------------- PDF GENERATION (clean layout) -----------------
def make_paragraph_style(name="NotoSans", fontsize=12, leading=14, font_name_override=None):
    base = getSampleStyleSheet()["Normal"]
    # Use registered font if available
    font_name = font_name_override or (FONT_NAME if font_available else base.fontName)
    return ParagraphStyle(
        name=name,
        parent=base,
        fontName=font_name,
        fontSize=fontsize,
        leading=leading,
        alignment=TA_LEFT,
    )

def prepare_paragraphs_from_text(text, style):
    """
    Split text by double newline (paragraph breaks) and return list of Paragraph objects.
    Keep single newlines as line breaks.
    """
    items = []
    if text is None:
        return items
    # normalize
    text = str(text).strip()
    if not text:
        return items
    # Replace bullet characters with simple bullets if necessary
    text = text.replace("▪", "-").replace("•", "-").replace("–", "-")
    paras = re.split(r"\n\s*\n", text)  # double newline splits
    for p in paras:
        # convert single newlines to <br/> for Paragraph
        p_html = p.replace("\n", "<br/>")
        items.append(Paragraph(p_html, style))
        items.append(Spacer(1, 4 * mm))
    return items

def generate_pdf_bytes(inputs: dict, row: pd.Series) -> bytes:
    """
    Build a well-formatted PDF as bytes using ReportLab platypus.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # Styles
    title_style = make_paragraph_style("Title", fontsize=16, leading=20)
    heading_style = make_paragraph_style("Heading", fontsize=12, leading=14, font_name_override=FONT_NAME + "-Bold" if font_available else None)
    normal_style = make_paragraph_style("Body", fontsize=12, leading=14)
    small_style = make_paragraph_style("Small", fontsize=9, leading=12)

    story = []

    # Title
    story.append(Paragraph("<b>Urban Road Maintenance Treatment Report</b>", title_style))
    story.append(Spacer(1, 6 * mm))

    # Input parameters
    story.append(Paragraph("<b>Input Parameters</b>", heading_style))
    story.append(Spacer(1, 2 * mm))
    for k, v in inputs.items():
        # Bold only the key, value stays normal
        story.append(Paragraph(f"<b>{k}:</b> {v}", normal_style))
    story.append(Spacer(1, 6 * mm))

    # Treatment Recommendation
    story.append(Paragraph("<b>Treatment Recommendation</b>", heading_style))
    story.append(Spacer(1, 2 * mm))
    treatment_title = row.get("Treatment", "N/A")
    story.append(Paragraph(f"<b>{treatment_title}</b>", normal_style))
    story.append(Spacer(1, 4 * mm))

    # Procedure
    story.append(Paragraph("<b>Procedure</b>", heading_style))
    story.append(Spacer(1, 2 * mm))
    story.extend(prepare_paragraphs_from_text(row.get("Procedure", ""), normal_style))
    story.append(Spacer(1, 4 * mm))

    # Suggestions
    story.append(Paragraph("<b>Suggestions</b>", heading_style))
    story.append(Spacer(1, 2 * mm))
    story.extend(prepare_paragraphs_from_text(row.get("Suggestions", ""), normal_style))
    story.append(Spacer(1, 4 * mm))

    # Cost, Time, Equipment, IRC Code
    story.append(Paragraph("<b>Cost per m²</b>", heading_style))
    story.append(Paragraph(str(row.get("Cost_per_m2", "N/A")), normal_style))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("<b>Time Required</b>", heading_style))
    story.append(Paragraph(str(row.get("Time_Required", "N/A")), normal_style))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("<b>Equipment Required</b>", heading_style))
    story.extend(prepare_paragraphs_from_text(row.get("Equipment_Required", ""), normal_style))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("<b>IRC Code</b>", heading_style))
    story.append(Paragraph(str(row.get("IRC_Code", "N/A")), normal_style))  # Changed from small_style to normal_style
    story.append(Spacer(1, 4 * mm))

    # Footer
    story.append(Paragraph("Generated by Urban Road Maintenance Expert System", small_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ----------------- DISPLAY LOGIC / UI -----------------
def display_output(row):
    """Show nicely formatted output in streamlit page."""
    st.markdown(
        """
    <style>
    .justified-text { text-align: justify; line-height: 1.4; margin-bottom: 0.8rem; }
    .section-title { font-weight: bold; font-size: 1.2rem; margin-top: 1rem; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(f"<div class='section-title'>🛠️ Recommended Treatment:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'><b>{row.get('Treatment','')}</b></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>📝 Procedure:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{str(row.get('Procedure','')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>💡 Suggestions:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{str(row.get('Suggestions','')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>💰 Cost per m²:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{row.get('Cost_per_m2','')}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>⏱️ Time Required:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{row.get('Time_Required','')}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>🧰 Equipment Required:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{row.get('Equipment_Required','')}</div>", unsafe_allow_html=True)

    st.markdown(f"<div class='section-title'>📘 IRC Code:</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='justified-text'>{row.get('IRC_Code','')}</div>", unsafe_allow_html=True)


# ----------------- MAIN -----------------
def main():
    st.title("🏙️ Urban Road Maintenance Expert System")

    # User manual expander
    with st.expander("📘 User Manual"):
        st.markdown(
    "<h4 style='text-align: left; color: black; font-weight: normal;'>From Distress to Durable.</h4>",
    unsafe_allow_html=True
        )
        st.markdown(
            """
        - Use **Single Mode** if only one distress is visible.
        - Use **Multiple Mode** if road shows more than one distress type.
        - Fill in severity, traffic, budget and other inputs.
        - Outputs include treatment, procedure, cost and IRC Code.
        """
        )
        try:
            with open("User_Manual.pdf", "rb") as f:
                st.download_button("📘 Download User Manual", f, file_name="User_Manual.pdf")
        except FileNotFoundError:
            st.warning("User manual not found. Please place 'User_Manual.pdf' in the project folder.")

    # load data
    try:
        single_df, multi_df = load_data()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    tab1, tab2 = st.tabs(["🚧 Single Distress Mode", "🔸 Multiple Distress Mode"])

    # -------- SINGLE MODE --------
    with tab1:
        st.subheader("🔹 Input for Single Distress")
        col1, col2 = st.columns(2)
        with col1:
            distress = st.selectbox("Distress Type", single_df["Distress_Type"].unique(), key="s_distress")
            st.caption(get_single_tooltip("DISTRESS_TYPE", distress, "ALL"))

            severity = st.selectbox(
                "Severity",
                single_df[single_df["Distress_Type"] == distress]["Severity"].unique(),
                key="s_severity",
            )
            st.caption(get_single_tooltip("SEVERITY", distress, severity))

            traffic = st.selectbox("Traffic Type", single_df["Traffic_Type"].unique(), key="s_traffic")
            st.caption(get_single_tooltip("TRAFFIC_TYPE", distress, severity))

            budget = st.selectbox("Budget Level", single_df["Budget_Level"].unique(), key="s_budget")
            st.caption(get_single_tooltip("BUDGET_LEVEL", distress, severity))

        with col2:
            material = st.selectbox("Material Available", single_df["Material_Available"].unique(), key="s_material")
            st.caption(get_single_tooltip("MATERIAL_AVAILABLE", distress, severity))

            time_limit = st.selectbox("Time Limit", single_df["Time_Limit"].unique(), key="s_time")
            st.caption(get_single_tooltip("TIME_LIMIT", distress, severity))

            extent = st.selectbox("Extent of Distress", single_df["Extent_of_Distress"].unique(), key="s_extent")
            st.caption(get_single_tooltip("EXTENT_OF_DISTRESS", distress, severity))

        if st.button("🔍 Show Treatment (Single Mode)"):
            match = single_df[
                (single_df["Distress_Type"] == distress)
                & (single_df["Severity"] == severity)
                & (single_df["Traffic_Type"] == traffic)
                & (single_df["Budget_Level"] == budget)
                & (single_df["Material_Available"] == material)
                & (single_df["Time_Limit"] == time_limit)
                & (single_df["Extent_of_Distress"] == extent)
            ]
            if not match.empty:
                row = match.iloc[0]
                display_output(row)
                inputs = {
                    "Distress Type": distress,
                    "Severity": severity,
                    "Traffic": traffic,
                    "Budget": budget,
                    "Material": material,
                    "Time": time_limit,
                    "Extent": extent,
                }
                pdf_bytes = generate_pdf_bytes(inputs, row)
                st.download_button("📄 Download Treatment PDF", data=pdf_bytes, file_name="treatment_report.pdf", mime="application/pdf")
            else:
                st.warning("❌ No treatment found for this combination.")

    # -------- MULTI MODE --------
    with tab2:
        st.subheader("🔸 Input for Multiple Distress")
        col1, col2 = st.columns(2)
        with col1:
            major = st.selectbox("Major Distress Type", multi_df["Major_Distress_Type"].unique(), key="m_major")
            st.caption(get_multi_tooltip("MAJOR_DISTRESS_TYPE", major, "ALL", "ALL"))

            minor = st.selectbox("Minor Distress Type", multi_df["Minor_Distress_Type"].unique(), key="m_minor")
            st.caption(get_multi_tooltip("MINOR_DISTRESS_TYPE", major, minor, "ALL"))

            severity = st.selectbox(
                "Severity", multi_df[multi_df["Major_Distress_Type"] == major]["Severity"].unique(), key="m_severity"
            )
            st.caption(get_multi_tooltip("SEVERITY", major, minor, severity))

            traffic = st.selectbox("Traffic Type", multi_df["Traffic_Type"].unique(), key="m_traffic")
            st.caption(get_multi_tooltip("TRAFFIC_TYPE", major, minor, severity))

        with col2:
            budget = st.selectbox("Budget Level", multi_df["Budget_Level"].unique(), key="m_budget")
            st.caption(get_multi_tooltip("BUDGET_LEVEL", major, minor, severity))

            material = st.selectbox("Material Available", multi_df["Material_Available"].unique(), key="m_material")
            st.caption(get_multi_tooltip("MATERIAL_AVAILABLE", major, minor, severity))

            time_limit = st.selectbox("Time Limit", multi_df["Time_Limit"].unique(), key="m_time")
            st.caption(get_multi_tooltip("TIME_LIMIT", major, minor, severity))

            extent = st.selectbox("Extent of Distress", multi_df["Extent_of_Distress"].unique(), key="m_extent")
            st.caption(get_multi_tooltip("EXTENT_OF_DISTRESS", major, minor, severity))

        if st.button("🔍 Show Treatment (Multiple Mode)"):
            match = multi_df[
                (multi_df["Major_Distress_Type"] == major)
                & (multi_df["Minor_Distress_Type"] == minor)
                & (multi_df["Severity"] == severity)
                & (multi_df["Traffic_Type"] == traffic)
                & (multi_df["Budget_Level"] == budget)
                & (multi_df["Material_Available"] == material)
                & (multi_df["Time_Limit"] == time_limit)
                & (multi_df["Extent_of_Distress"] == extent)
            ]
            if not match.empty:
                row = match.iloc[0]
                display_output(row)
                inputs = {
                    "Major Distress": major,
                    "Minor Distress": minor,
                    "Severity": severity,
                    "Traffic": traffic,
                    "Budget": budget,
                    "Material": material,
                    "Time": time_limit,
                    "Extent": extent,
                }
                pdf_bytes = generate_pdf_bytes(inputs, row)
                st.download_button("📄 Download Treatment PDF", data=pdf_bytes, file_name="treatment_report.pdf", mime="application/pdf")
            else:
                st.warning("❌ No treatment found for this combination.")


if __name__ == "__main__":
    main()
