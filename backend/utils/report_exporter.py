"""
AgriSmart - Smart Farm Reports & Export Center (Feature Upgrade 8 - Phase 3)
backend/utils/report_exporter.py

High-performance, secure report exporter supporting:
1. PDF Generation via ReportLab (A4, NumberedCanvas "Page X of Y", Devanagari/Unicode font support, currency formatting, auto-wrapping tables, clean headers/footers)
2. CSV Export with UTF-8 BOM (utf-8-sig) and protection against spreadsheet formula injection
3. Excel (.xlsx) Workbooks via openpyxl (Multi-sheet workbooks, emerald branding, auto-filters, freeze panes, real numeric & currency cell formatting)
"""

import os
import io
import csv
from datetime import datetime

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# openpyxl imports
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# =============================================================================
# 1. FONT REGISTRATION & CANVASES
# =============================================================================

FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

def _register_fonts():
    global FONT_NAME, FONT_NAME_BOLD
    candidate_regular = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
        "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    candidate_bold = [
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for p in candidate_regular:
        if os.path.exists(p):
            try:
                sub = 0 if p.endswith(".ttc") else None
                pdfmetrics.registerFont(TTFont("AgriSmartFont", p, subfontIndex=sub))
                FONT_NAME = "AgriSmartFont"
                break
            except Exception:
                pass

    for p in candidate_bold:
        if os.path.exists(p):
            try:
                sub = 0 if p.endswith(".ttc") else None
                pdfmetrics.registerFont(TTFont("AgriSmartFontBold", p, subfontIndex=sub))
                FONT_NAME_BOLD = "AgriSmartFontBold"
                break
            except Exception:
                pass

    if FONT_NAME != "Helvetica" and FONT_NAME_BOLD == "Helvetica-Bold":
        FONT_NAME_BOLD = FONT_NAME

_register_fonts()


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y' and running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont(FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header
        self.drawString(36, 842 - 26, "AgriSmart — Smart Agriculture Assistant | Confidential Farm Record")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 842 - 30, 595 - 36, 842 - 30)

        # Running Footer
        self.line(36, 32, 595 - 36, 32)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(595 - 36, 20, page_text)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.drawString(36, 20, f"Generated on {now_str} • Authorized Farmer Document")
        self.restoreState()


# =============================================================================
# 2. LOCALIZATION LABELS & METRIC TITLES
# =============================================================================

REPORT_TITLES = {
    "overview": {
        "en": "Farm Overview & Multi-Module KPI Summary",
        "mr": "शेत विहंगावलोकन आणि बहु-घटक केपीआय सारांश",
        "hi": "खेत अवलोकन और बहु-मॉड्यूल केपीआई सारांश",
    },
    "crops": {
        "en": "Crop Management & Growth Analytics Report",
        "mr": "पीक व्यवस्थापन आणि वाढ विश्लेषण अहवाल",
        "hi": "फसल प्रबंधन और विकास विश्लेषण रिपोर्ट",
    },
    "disease": {
        "en": "Plant Disease Diagnosis & Foliage Health Report",
        "mr": "पीक रोग निदान आणि वनस्पती आरोग्य अहवाल",
        "hi": "पौध रोग निदान और पौध स्वास्थ्य रिपोर्ट",
    },
    "irrigation": {
        "en": "Smart Irrigation & Water Conservation Report",
        "mr": "स्मार्ट सिंचन आणि जलसंधारण अहवाल",
        "hi": "स्मार्ट सिंचाई और जल संरक्षण रिपोर्ट",
    },
    "financial": {
        "en": "Farm Financial Ledger & Profitability Report",
        "mr": "शेत आर्थिक खतावणी आणि नफा अहवाल",
        "hi": "खेत वित्तीय बहीखाता और लाभप्रदता रिपोर्ट",
    },
    "harvest": {
        "en": "Crop Harvest & Revenue Sales Report",
        "mr": "पीक काढणी आणि महसूल विक्री अहवाल",
        "hi": "फसल कटाई और राजस्व बिक्री रिपोर्ट",
    },
    "activities": {
        "en": "Farm Activity Calendar & Operations Report",
        "mr": "शेती कामे आणि कार्य नियोजन अहवाल",
        "hi": "खेत गतिविधियाँ और कार्य नियोजन रिपोर्ट",
    },
    "inventory": {
        "en": "Farm Inventory, Stock Valuation & Movement Audit",
        "mr": "शेत साहित्य साठा, मूल्य आणि हालचाल अहवाल",
        "hi": "खेत इन्वेंट्री, स्टॉक मूल्यांकन और हलचल रिपोर्ट",
    },
    "alerts": {
        "en": "Farm Alerts, Weather Warnings & System Audit Log",
        "mr": "शेत सूचना, हवामान इशारे आणि सिस्टम ऑडिट लॉग",
        "hi": "खेत अलर्ट, मौसम चेतावनी और सिस्टम ऑडिट लॉग",
    },
    "all": {
        "en": "AgriSmart Comprehensive Master Farm Dossier",
        "mr": "अॅग्रीस्मार्ट सर्वसमावेशक मुख्य शेत अहवाल",
        "hi": "एग्रीस्मार्ट व्यापक मास्टर फार्म रिपोर्ट",
    }
}


def _get_title(category, lang="en"):
    lang = lang.lower() if lang in ("mr", "hi") else "en"
    cat_titles = REPORT_TITLES.get(category, REPORT_TITLES["overview"])
    return cat_titles.get(lang, cat_titles["en"])


def sanitize_csv_cell(val):
    """Neutralize spreadsheet formula injection for values starting with =, +, -, @, \\t, \\r."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


# =============================================================================
# 3. PDF GENERATION ENGINE
# =============================================================================

def _build_pdf_styles():
    base_styles = getSampleStyleSheet()
    styles = {}

    styles["Title"] = ParagraphStyle(
        "PDFTitle",
        parent=base_styles["Heading1"],
        fontName=FONT_NAME_BOLD,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#15803d"),
        spaceAfter=4,
    )
    styles["Subtitle"] = ParagraphStyle(
        "PDFSubtitle",
        parent=base_styles["Normal"],
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    styles["SectionHead"] = ParagraphStyle(
        "PDFSectionHead",
        parent=base_styles["Heading2"],
        fontName=FONT_NAME_BOLD,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#166534"),
        spaceBefore=12,
        spaceAfter=6,
    )
    styles["TableHeader"] = ParagraphStyle(
        "PDFTableHeader",
        parent=base_styles["Normal"],
        fontName=FONT_NAME_BOLD,
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0,
    )
    styles["TableCell"] = ParagraphStyle(
        "PDFTableCell",
        parent=base_styles["Normal"],
        fontName=FONT_NAME,
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )
    styles["TableCellBold"] = ParagraphStyle(
        "PDFTableCellBold",
        parent=base_styles["Normal"],
        fontName=FONT_NAME_BOLD,
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )
    styles["TableCellNum"] = ParagraphStyle(
        "PDFTableCellNum",
        parent=base_styles["Normal"],
        fontName=FONT_NAME,
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
        alignment=2,
    )
    styles["KpiLabel"] = ParagraphStyle(
        "PDFKpiLabel",
        parent=base_styles["Normal"],
        fontName=FONT_NAME,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )
    styles["KpiValue"] = ParagraphStyle(
        "PDFKpiValue",
        parent=base_styles["Normal"],
        fontName=FONT_NAME_BOLD,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
    )
    styles["EmptyNotice"] = ParagraphStyle(
        "PDFEmptyNotice",
        parent=base_styles["Italic"],
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
    )
    return styles


def _build_banner_block(category, metadata, lang, styles):
    """Build AgriSmart header branding and filter context block."""
    title_text = _get_title(category, lang)
    range_lbl = metadata.get("range_label", "All Recorded Time")
    gen_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    farm_info = metadata.get("farm_name") or "All Farms"
    crop_info = metadata.get("crop_name") or "All Crops"

    banner_data = [
        [
            Paragraph("<b>🌿 AgriSmart</b><br/><font size=8 color='#64748b'>Smart Agriculture Assistant</font>", styles["TableCellBold"]),
            Paragraph(f"<b>Reporting Period:</b> {range_lbl}<br/><b>Filters:</b> Farm: {farm_info} | Crop: {crop_info}<br/><b>Export Date:</b> {gen_time}", styles["TableCell"])
        ]
    ]
    banner_table = Table(banner_data, colWidths=[200, 323])
    banner_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#15803d")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    story = [
        banner_table,
        Spacer(1, 10),
        Paragraph(title_text, styles["Title"]),
        Paragraph("Certified farm telemetry, agronomic records, and financial ledger data.", styles["Subtitle"]),
        Spacer(1, 4),
    ]
    return story


def _build_kpi_table(kpi_pairs, styles):
    """Build a styled 4-column KPI card table."""
    cells = []
    for lbl, val in kpi_pairs:
        p = [Paragraph(lbl, styles["KpiLabel"]), Paragraph(str(val), styles["KpiValue"])]
        cells.append(p)

    rows = []
    for i in range(0, len(cells), 4):
        chunk = cells[i:i + 4]
        while len(chunk) < 4:
            chunk.append("")
        rows.append(chunk)

    if not rows:
        return Spacer(1, 1)

    t = Table(rows, colWidths=[130, 131, 131, 131])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def generate_pdf_report(category, data, metadata, lang="en"):
    """
    Generate professional A4 PDF report for specified category.
    Returns bytes buffer (io.BytesIO).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = _build_pdf_styles()
    story = _build_banner_block(category, metadata, lang, styles)

    # 1. FARM OVERVIEW
    if category == "overview":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Farms", sum_m.get("total_farms", 0)),
            ("Total Farm Area", f"{sum_m.get('total_farm_area', 0.0):.1f} Ac"),
            ("Active Crops", sum_m.get("active_crops", 0)),
            ("Cultivated Area", f"{sum_m.get('total_cultivated_area', 0.0):.1f} Ac"),
            ("Total Expenses", f"₹ {sum_m.get('total_expenses', 0.0):,.2f}"),
            ("Total Revenue", f"₹ {sum_m.get('total_revenue', 0.0):,.2f}"),
            ("Net Profit", f"₹ {sum_m.get('net_profit', 0.0):,.2f}"),
            ("Profit Margin", f"{sum_m.get('margin_pct', 0.0):.1f}%"),
            ("Irrigation Vol.", f"{sum_m.get('total_water_volume_mm', 0.0):.1f} mm"),
            ("Water Saved", f"{sum_m.get('water_saved_mm', 0.0):.1f} mm"),
            ("Plant Scans", sum_m.get("total_diagnoses", 0)),
            ("Foliage Health", f"{sum_m.get('health_ratio_pct', 0.0):.1f}%"),
            ("Completed Tasks", f"{sum_m.get('completed_activities', 0)} / {sum_m.get('total_activities', 0)}"),
            ("Task Rate", f"{sum_m.get('completion_rate', 0.0):.1f}%"),
            ("Stock Valuation", f"₹ {sum_m.get('total_inventory_valuation', 0.0):,.2f}"),
            ("Active Alerts", sum_m.get("total_alerts", 0)),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        # Recent activities table
        story.append(Paragraph("Recent Farm Activities & Operations", styles["SectionHead"]))
        acts = data.get("recent_activities", [])
        if acts:
            tbl_data = [[
                Paragraph("<b>Date</b>", styles["TableHeader"]),
                Paragraph("<b>Activity Title</b>", styles["TableHeader"]),
                Paragraph("<b>Category</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Status</b>", styles["TableHeader"]),
            ]]
            for a in acts[:10]:
                tbl_data.append([
                    Paragraph(str(a.get("scheduled_date") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("title") or "-"), styles["TableCellBold"]),
                    Paragraph(str(a.get("category") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("crop_name") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("status") or "-"), styles["TableCellBold"]),
                ])
            t = Table(tbl_data, colWidths=[70, 163, 100, 100, 90], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No activities recorded in this reporting period.", styles["EmptyNotice"]))

    # 2. CROPS REPORT
    elif category == "crops":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Crops", sum_m.get("total_crops", 0)),
            ("Active Growing", sum_m.get("active_crops", 0)),
            ("Harvested", sum_m.get("harvested_crops", 0)),
            ("Cultivated Area", f"{sum_m.get('total_area', 0.0):.1f} Acres"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        # Crop table
        crops = data.get("crops", [])
        story.append(Paragraph("Registered Crops & Growth Status", styles["SectionHead"]))
        if crops:
            tbl_data = [[
                Paragraph("<b>Crop Name</b>", styles["TableHeader"]),
                Paragraph("<b>Variety</b>", styles["TableHeader"]),
                Paragraph("<b>Growth Stage</b>", styles["TableHeader"]),
                Paragraph("<b>Planting Date</b>", styles["TableHeader"]),
                Paragraph("<b>Expected Harvest</b>", styles["TableHeader"]),
                Paragraph("<b>Area (Ac)</b>", styles["TableHeader"]),
                Paragraph("<b>Farm</b>", styles["TableHeader"]),
            ]]
            for c in crops:
                tbl_data.append([
                    Paragraph(str(c.get("crop_name") or "-"), styles["TableCellBold"]),
                    Paragraph(str(c.get("variety") or "-"), styles["TableCell"]),
                    Paragraph(str(c.get("growth_status") or "-"), styles["TableCellBold"]),
                    Paragraph(str(c.get("planting_date") or "-"), styles["TableCell"]),
                    Paragraph(str(c.get("expected_harvest_date") or "-"), styles["TableCell"]),
                    Paragraph(f"{float(c.get('cultivated_area') or 0.0):.1f}", styles["TableCellNum"]),
                    Paragraph(str(c.get("farm_name") or "-"), styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[90, 75, 80, 75, 80, 55, 68], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No crop records found for the selected period.", styles["EmptyNotice"]))

    # 3. DISEASE REPORT
    elif category == "disease":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Scans", sum_m.get("total_scans", 0)),
            ("Healthy Foliage", sum_m.get("healthy_scans", 0)),
            ("Diseased Scans", sum_m.get("diseased_scans", 0)),
            ("Foliage Health Ratio", f"{sum_m.get('health_ratio', 0.0):.1f}%"),
            ("Avg Model Confidence", f"{sum_m.get('avg_confidence', 0.0):.1f}%"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        scans = data.get("scans", [])
        story.append(Paragraph("Plant Disease Diagnosis Log & Recommendations", styles["SectionHead"]))
        if scans:
            tbl_data = [[
                Paragraph("<b>Date / Time</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Diagnosed Condition</b>", styles["TableHeader"]),
                Paragraph("<b>Confidence</b>", styles["TableHeader"]),
                Paragraph("<b>Health Status</b>", styles["TableHeader"]),
                Paragraph("<b>Recommended Action</b>", styles["TableHeader"]),
            ]]
            for s in scans:
                health_txt = "Healthy" if s.get("is_healthy") else "Diseased"
                conf_txt = f"{float(s.get('confidence') or 0.0):.1f}%"
                treat_txt = str(s.get("treatment_summary") or "-")
                if len(treat_txt) > 60:
                    treat_txt = treat_txt[:57] + "..."
                tbl_data.append([
                    Paragraph(f"{s.get('date') or '-'} {s.get('time') or ''}", styles["TableCell"]),
                    Paragraph(str(s.get("crop_name") or "-"), styles["TableCellBold"]),
                    Paragraph(str(s.get("condition") or "-"), styles["TableCellBold"]),
                    Paragraph(conf_txt, styles["TableCellNum"]),
                    Paragraph(health_txt, styles["TableCell"]),
                    Paragraph(treat_txt, styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[80, 75, 110, 60, 65, 133], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No disease scans recorded in this reporting period.", styles["EmptyNotice"]))

    # 4. IRRIGATION REPORT
    elif category == "irrigation":
        sum_m = data.get("summary", {})
        kpis = [
            ("Advisories Generated", sum_m.get("total_recommendations", 0)),
            ("Irrigation Needed", sum_m.get("water_needed_count", 0)),
            ("Water Skipped", sum_m.get("skip_count", 0)),
            ("Total Water Vol.", f"{sum_m.get('total_water_mm', 0.0):.1f} mm"),
            ("Water Saved", f"{sum_m.get('water_saved_mm', 0.0):.1f} mm"),
            ("Avg Soil Moisture", f"{sum_m.get('avg_soil_moisture', 0.0):.1f}%"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        # Advisory history
        recs = data.get("recommendations", [])
        story.append(Paragraph("Smart Irrigation Advisory Telemetry Log", styles["SectionHead"]))
        if recs:
            tbl_data = [[
                Paragraph("<b>Date / Time</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Moisture</b>", styles["TableHeader"]),
                Paragraph("<b>Temp</b>", styles["TableHeader"]),
                Paragraph("<b>Action</b>", styles["TableHeader"]),
                Paragraph("<b>Volume (mm)</b>", styles["TableHeader"]),
                Paragraph("<b>Reason / Advisory</b>", styles["TableHeader"]),
            ]]
            for r in recs:
                tbl_data.append([
                    Paragraph(f"{r.get('date') or '-'} {r.get('time') or ''}", styles["TableCell"]),
                    Paragraph(str(r.get("crop_name") or "-"), styles["TableCellBold"]),
                    Paragraph(f"{float(r.get('soil_moisture') or 0.0):.1f}%", styles["TableCellNum"]),
                    Paragraph(f"{float(r.get('temperature') or 0.0):.1f}°C", styles["TableCellNum"]),
                    Paragraph(str(r.get("action") or "-"), styles["TableCellBold"]),
                    Paragraph(f"{float(r.get('water_amount_mm') or 0.0):.1f}", styles["TableCellNum"]),
                    Paragraph(str(r.get("reason") or "-")[:50], styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[75, 75, 55, 50, 65, 60, 143], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No irrigation advisories recorded in this period.", styles["EmptyNotice"]))

    # 5. FINANCIAL REPORT
    elif category == "financial":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Expenses", f"₹ {sum_m.get('total_expenses', 0.0):,.2f}"),
            ("Total Revenue", f"₹ {sum_m.get('total_revenue', 0.0):,.2f}"),
            ("Net Profit / Loss", f"₹ {sum_m.get('net_profit', 0.0):,.2f}"),
            ("Profit Margin", f"{sum_m.get('profit_margin_pct', 0.0):.1f}%"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        # Crop profitability
        crop_prof = data.get("crop_profitability", [])
        if crop_prof:
            story.append(Paragraph("Crop-Wise Profitability Breakdown", styles["SectionHead"]))
            tbl_data = [[
                Paragraph("<b>Crop Name</b>", styles["TableHeader"]),
                Paragraph("<b>Expenses</b>", styles["TableHeader"]),
                Paragraph("<b>Revenue</b>", styles["TableHeader"]),
                Paragraph("<b>Net Profit</b>", styles["TableHeader"]),
                Paragraph("<b>Margin %</b>", styles["TableHeader"]),
            ]]
            for cp in crop_prof:
                tbl_data.append([
                    Paragraph(str(cp.get("crop_name") or "-"), styles["TableCellBold"]),
                    Paragraph(f"₹ {float(cp.get('expenses') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(cp.get('revenue') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(cp.get('net_profit') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(f"{float(cp.get('margin_pct') or 0.0):.1f}%", styles["TableCellNum"]),
                ])
            t = Table(tbl_data, colWidths=[143, 95, 95, 100, 90], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
            story.append(Spacer(1, 12))

        # Itemized Expenses
        exps = data.get("expenses", [])
        story.append(Paragraph("Itemized Farm Expenses Ledger", styles["SectionHead"]))
        if exps:
            tbl_data = [[
                Paragraph("<b>Date</b>", styles["TableHeader"]),
                Paragraph("<b>Category</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Description</b>", styles["TableHeader"]),
                Paragraph("<b>Amount (₹)</b>", styles["TableHeader"]),
            ]]
            for e in exps:
                tbl_data.append([
                    Paragraph(str(e.get("date") or "-"), styles["TableCell"]),
                    Paragraph(str(e.get("category") or "-"), styles["TableCellBold"]),
                    Paragraph(str(e.get("crop_name") or "-"), styles["TableCell"]),
                    Paragraph(str(e.get("description") or "-")[:50], styles["TableCell"]),
                    Paragraph(f"₹ {float(e.get('amount') or 0.0):,.2f}", styles["TableCellNum"]),
                ])
            t = Table(tbl_data, colWidths=[70, 90, 85, 178, 100], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No expenses recorded in this period.", styles["EmptyNotice"]))

    # 6. HARVEST REPORT
    elif category == "harvest":
        harvs = data.get("harvests", [])
        tot_rev = sum(float(h.get("total_revenue") or 0.0) for h in harvs)
        tot_qty = sum(float(h.get("quantity") or 0.0) for h in harvs)
        kpis = [
            ("Harvest Operations", len(harvs)),
            ("Total Yield Logged", f"{tot_qty:,.1f} Units"),
            ("Total Sales Revenue", f"₹ {tot_rev:,.2f}"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        story.append(Paragraph("Harvest & Market Sales Records", styles["SectionHead"]))
        if harvs:
            tbl_data = [[
                Paragraph("<b>Date</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Quantity</b>", styles["TableHeader"]),
                Paragraph("<b>Price / Unit</b>", styles["TableHeader"]),
                Paragraph("<b>Total Revenue</b>", styles["TableHeader"]),
                Paragraph("<b>Buyer / Market</b>", styles["TableHeader"]),
            ]]
            for h in harvs:
                tbl_data.append([
                    Paragraph(str(h.get("date") or "-"), styles["TableCell"]),
                    Paragraph(str(h.get("crop_name") or "-"), styles["TableCellBold"]),
                    Paragraph(f"{float(h.get('quantity') or 0.0):,.1f} {h.get('unit') or ''}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(h.get('price_per_unit') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(h.get('total_revenue') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(str(h.get("buyer_name") or "-"), styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[70, 95, 85, 85, 95, 93], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No harvest sales recorded in this period.", styles["EmptyNotice"]))

    # 7. ACTIVITIES REPORT
    elif category == "activities":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Tasks", sum_m.get("total_activities", 0)),
            ("Completed", sum_m.get("completed_activities", 0)),
            ("Pending", sum_m.get("pending_activities", 0)),
            ("Overdue", sum_m.get("overdue_activities", 0)),
            ("Completion Rate", f"{sum_m.get('completion_rate', 0.0):.1f}%"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        acts = data.get("activities", [])
        story.append(Paragraph("Farm Operations & Task Schedule", styles["SectionHead"]))
        if acts:
            tbl_data = [[
                Paragraph("<b>Scheduled</b>", styles["TableHeader"]),
                Paragraph("<b>Title</b>", styles["TableHeader"]),
                Paragraph("<b>Category</b>", styles["TableHeader"]),
                Paragraph("<b>Crop</b>", styles["TableHeader"]),
                Paragraph("<b>Priority</b>", styles["TableHeader"]),
                Paragraph("<b>Status</b>", styles["TableHeader"]),
            ]]
            for a in acts:
                tbl_data.append([
                    Paragraph(f"{a.get('scheduled_date') or '-'} {a.get('scheduled_time') or ''}", styles["TableCell"]),
                    Paragraph(str(a.get("title") or "-"), styles["TableCellBold"]),
                    Paragraph(str(a.get("category") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("crop_name") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("priority") or "-"), styles["TableCell"]),
                    Paragraph(str(a.get("status") or "-"), styles["TableCellBold"]),
                ])
            t = Table(tbl_data, colWidths=[80, 133, 85, 80, 65, 80], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No activities recorded in this reporting period.", styles["EmptyNotice"]))

    # 8. INVENTORY REPORT
    elif category == "inventory":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Items", sum_m.get("total_items", 0)),
            ("Low Stock Items", sum_m.get("low_stock_items", 0)),
            ("Expiring Soon", sum_m.get("expiring_items", 0)),
            ("Stock Valuation", f"₹ {sum_m.get('total_valuation', 0.0):,.2f}"),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        items = data.get("items", [])
        story.append(Paragraph("Current Farm Inventory & Valuation", styles["SectionHead"]))
        if items:
            tbl_data = [[
                Paragraph("<b>Item Name</b>", styles["TableHeader"]),
                Paragraph("<b>Category</b>", styles["TableHeader"]),
                Paragraph("<b>Quantity</b>", styles["TableHeader"]),
                Paragraph("<b>Unit Price</b>", styles["TableHeader"]),
                Paragraph("<b>Total Value</b>", styles["TableHeader"]),
                Paragraph("<b>Expiry Date</b>", styles["TableHeader"]),
            ]]
            for itm in items:
                tbl_data.append([
                    Paragraph(str(itm.get("item_name") or "-"), styles["TableCellBold"]),
                    Paragraph(str(itm.get("category") or "-"), styles["TableCell"]),
                    Paragraph(f"{float(itm.get('quantity') or 0.0):,.1f} {itm.get('unit') or ''}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(itm.get('unit_price') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(f"₹ {float(itm.get('total_value') or 0.0):,.2f}", styles["TableCellNum"]),
                    Paragraph(str(itm.get("expiry_date") or "-"), styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[113, 85, 85, 80, 85, 75], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No inventory items found.", styles["EmptyNotice"]))

    # 9. ALERTS REPORT
    elif category == "alerts":
        sum_m = data.get("summary", {})
        kpis = [
            ("Total Alerts", sum_m.get("total_notifications", 0)),
            ("Unread", sum_m.get("unread_notifications", 0)),
            ("High Severity", sum_m.get("high_severity_notifications", 0)),
            ("Medium", sum_m.get("medium_severity_notifications", 0)),
        ]
        story.append(_build_kpi_table(kpis, styles))
        story.append(Spacer(1, 14))

        notifs = data.get("notifications", [])
        story.append(Paragraph("Audit Trail: Alerts & System Notifications", styles["SectionHead"]))
        if notifs:
            tbl_data = [[
                Paragraph("<b>Date / Time</b>", styles["TableHeader"]),
                Paragraph("<b>Type</b>", styles["TableHeader"]),
                Paragraph("<b>Severity</b>", styles["TableHeader"]),
                Paragraph("<b>Title</b>", styles["TableHeader"]),
                Paragraph("<b>Message</b>", styles["TableHeader"]),
            ]]
            for n in notifs:
                tbl_data.append([
                    Paragraph(str(n.get("created_at") or "-")[:16], styles["TableCell"]),
                    Paragraph(str(n.get("type") or "-"), styles["TableCell"]),
                    Paragraph(str(n.get("severity") or "-"), styles["TableCellBold"]),
                    Paragraph(str(n.get("title") or "-"), styles["TableCellBold"]),
                    Paragraph(str(n.get("message") or "-")[:60], styles["TableCell"]),
                ])
            t = Table(tbl_data, colWidths=[80, 75, 65, 110, 193], repeatRows=1)
            t.setStyle(_table_style())
            story.append(t)
        else:
            story.append(Paragraph("No alerts logged for this reporting period.", styles["EmptyNotice"]))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    buf.seek(0)
    return buf


def _table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15803d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ])


# =============================================================================
# 4. CSV GENERATION ENGINE
# =============================================================================

def generate_csv_report(category, data, metadata, lang="en"):
    """
    Generate CSV file bytes encoded with UTF-8 BOM (utf-8-sig).
    Includes formula injection protection and metadata header banner.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Metadata banner
    title = _get_title(category, lang)
    range_lbl = metadata.get("range_label", "All Recorded Time")
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([f"# AgriSmart Farm Report: {title}"])
    writer.writerow([f"# Reporting Period: {range_lbl}"])
    writer.writerow([f"# Generated On: {gen_time}"])
    writer.writerow([f"# Farm: {metadata.get('farm_name', 'All Farms')} | Crop: {metadata.get('crop_name', 'All Crops')}"])
    writer.writerow([])

    # 2. Category-specific rows
    if category == "overview":
        sum_m = data.get("summary", {})
        writer.writerow(["Metric", "Value", "Unit"])
        for k, v in sum_m.items():
            writer.writerow([sanitize_csv_cell(k.replace("_", " ").title()), sanitize_csv_cell(v), ""])
        writer.writerow([])
        writer.writerow(["Recent Activity Title", "Category", "Crop", "Status", "Scheduled Date"])
        for a in data.get("recent_activities", []):
            writer.writerow([
                sanitize_csv_cell(a.get("title")),
                sanitize_csv_cell(a.get("category")),
                sanitize_csv_cell(a.get("crop_name")),
                sanitize_csv_cell(a.get("status")),
                sanitize_csv_cell(a.get("scheduled_date")),
            ])

    elif category == "crops":
        writer.writerow(["Crop ID", "Crop Name", "Variety", "Growth Stage", "Planting Date", "Expected Harvest", "Cultivated Area (Acres)", "Farm Name", "Days in Ground"])
        for c in data.get("crops", []):
            writer.writerow([
                sanitize_csv_cell(c.get("id")),
                sanitize_csv_cell(c.get("crop_name")),
                sanitize_csv_cell(c.get("variety")),
                sanitize_csv_cell(c.get("growth_status")),
                sanitize_csv_cell(c.get("planting_date")),
                sanitize_csv_cell(c.get("expected_harvest_date")),
                sanitize_csv_cell(c.get("cultivated_area")),
                sanitize_csv_cell(c.get("farm_name")),
                sanitize_csv_cell(c.get("days_in_ground")),
            ])

    elif category == "disease":
        writer.writerow(["Scan ID", "Date", "Time", "Crop Name", "Diagnosed Condition", "Model Confidence (%)", "Health Status", "Recommended Action"])
        for s in data.get("scans", []):
            writer.writerow([
                sanitize_csv_cell(s.get("id")),
                sanitize_csv_cell(s.get("date")),
                sanitize_csv_cell(s.get("time")),
                sanitize_csv_cell(s.get("crop_name")),
                sanitize_csv_cell(s.get("condition")),
                sanitize_csv_cell(f"{float(s.get('confidence') or 0.0):.1f}"),
                sanitize_csv_cell("Healthy" if s.get("is_healthy") else "Diseased"),
                sanitize_csv_cell(s.get("treatment_summary")),
            ])

    elif category == "irrigation":
        writer.writerow(["Record ID", "Date", "Time", "Crop Name", "Soil Type", "Growth Stage", "Soil Moisture (%)", "Temperature (°C)", "Rainfall (mm)", "Action", "Water Volume (mm)", "Reason"])
        for r in data.get("recommendations", []):
            writer.writerow([
                sanitize_csv_cell(r.get("id")),
                sanitize_csv_cell(r.get("date")),
                sanitize_csv_cell(r.get("time")),
                sanitize_csv_cell(r.get("crop_name")),
                sanitize_csv_cell(r.get("soil_type")),
                sanitize_csv_cell(r.get("growth_stage")),
                sanitize_csv_cell(r.get("soil_moisture")),
                sanitize_csv_cell(r.get("temperature")),
                sanitize_csv_cell(r.get("rainfall")),
                sanitize_csv_cell(r.get("action")),
                sanitize_csv_cell(r.get("water_amount_mm")),
                sanitize_csv_cell(r.get("reason")),
            ])

    elif category == "financial":
        writer.writerow(["Expense ID", "Date", "Category", "Amount (INR)", "Crop Name", "Farm Name", "Description", "Notes"])
        for e in data.get("expenses", []):
            writer.writerow([
                sanitize_csv_cell(e.get("id")),
                sanitize_csv_cell(e.get("date")),
                sanitize_csv_cell(e.get("category")),
                sanitize_csv_cell(f"{float(e.get('amount') or 0.0):.2f}"),
                sanitize_csv_cell(e.get("crop_name")),
                sanitize_csv_cell(e.get("farm_name")),
                sanitize_csv_cell(e.get("description")),
                sanitize_csv_cell(e.get("notes")),
            ])
        writer.writerow([])
        writer.writerow(["Crop Name", "Total Expenses (INR)", "Total Revenue (INR)", "Net Profit (INR)", "Margin (%)"])
        for cp in data.get("crop_profitability", []):
            writer.writerow([
                sanitize_csv_cell(cp.get("crop_name")),
                sanitize_csv_cell(f"{float(cp.get('expenses') or 0.0):.2f}"),
                sanitize_csv_cell(f"{float(cp.get('revenue') or 0.0):.2f}"),
                sanitize_csv_cell(f"{float(cp.get('net_profit') or 0.0):.2f}"),
                sanitize_csv_cell(f"{float(cp.get('margin_pct') or 0.0):.1f}"),
            ])

    elif category == "harvest":
        writer.writerow(["Harvest ID", "Date", "Crop Name", "Farm Name", "Quantity", "Unit", "Price Per Unit (INR)", "Total Revenue (INR)", "Buyer Name", "Notes"])
        for h in data.get("harvests", []):
            writer.writerow([
                sanitize_csv_cell(h.get("id")),
                sanitize_csv_cell(h.get("date")),
                sanitize_csv_cell(h.get("crop_name")),
                sanitize_csv_cell(h.get("farm_name")),
                sanitize_csv_cell(h.get("quantity")),
                sanitize_csv_cell(h.get("unit")),
                sanitize_csv_cell(f"{float(h.get('price_per_unit') or 0.0):.2f}"),
                sanitize_csv_cell(f"{float(h.get('total_revenue') or 0.0):.2f}"),
                sanitize_csv_cell(h.get("buyer_name")),
                sanitize_csv_cell(h.get("notes")),
            ])

    elif category == "activities":
        writer.writerow(["Activity ID", "Title", "Category", "Crop Name", "Farm Name", "Scheduled Date", "Scheduled Time", "Priority", "Status", "Completed Date", "Description"])
        for a in data.get("activities", []):
            writer.writerow([
                sanitize_csv_cell(a.get("id")),
                sanitize_csv_cell(a.get("title")),
                sanitize_csv_cell(a.get("category")),
                sanitize_csv_cell(a.get("crop_name")),
                sanitize_csv_cell(a.get("farm_name")),
                sanitize_csv_cell(a.get("scheduled_date")),
                sanitize_csv_cell(a.get("scheduled_time")),
                sanitize_csv_cell(a.get("priority")),
                sanitize_csv_cell(a.get("status")),
                sanitize_csv_cell(a.get("completed_date")),
                sanitize_csv_cell(a.get("description")),
            ])

    elif category == "inventory":
        writer.writerow(["Item ID", "Item Name", "Category", "Quantity", "Unit", "Unit Price (INR)", "Total Value (INR)", "Low Stock Threshold", "Expiry Date", "Location"])
        for itm in data.get("items", []):
            writer.writerow([
                sanitize_csv_cell(itm.get("id")),
                sanitize_csv_cell(itm.get("item_name")),
                sanitize_csv_cell(itm.get("category")),
                sanitize_csv_cell(itm.get("quantity")),
                sanitize_csv_cell(itm.get("unit")),
                sanitize_csv_cell(f"{float(itm.get('unit_price') or 0.0):.2f}"),
                sanitize_csv_cell(f"{float(itm.get('total_value') or 0.0):.2f}"),
                sanitize_csv_cell(itm.get("low_stock_threshold")),
                sanitize_csv_cell(itm.get("expiry_date")),
                sanitize_csv_cell(itm.get("location")),
            ])

    elif category == "alerts":
        writer.writerow(["Notification ID", "Created At", "Type", "Severity", "Title", "Message", "Is Read"])
        for n in data.get("notifications", []):
            writer.writerow([
                sanitize_csv_cell(n.get("id")),
                sanitize_csv_cell(n.get("created_at")),
                sanitize_csv_cell(n.get("type")),
                sanitize_csv_cell(n.get("severity")),
                sanitize_csv_cell(n.get("title")),
                sanitize_csv_cell(n.get("message")),
                sanitize_csv_cell("Yes" if n.get("is_read") else "No"),
            ])

    # Convert to UTF-8 with BOM bytes
    csv_str = output.getvalue()
    buf = io.BytesIO(csv_str.encode("utf-8-sig"))
    return buf


# =============================================================================
# 5. EXCEL WORKBOOK ENGINE (openpyxl)
# =============================================================================

def _style_excel_sheet(ws, title_text, metadata):
    """Apply professional AgriSmart theme to Excel worksheet."""
    # Title Banner (Row 1)
    ws.merge_cells("A1:G1")
    t_cell = ws["A1"]
    t_cell.value = f"AgriSmart — {title_text}"
    t_cell.font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    t_cell.fill = PatternFill(start_color="15803D", end_color="15803D", fill_type="solid")
    t_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Subtitle / Filter Meta (Row 2)
    ws.merge_cells("A2:G2")
    s_cell = ws["A2"]
    range_lbl = metadata.get("range_label", "All Recorded Time")
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    s_cell.value = f"Reporting Period: {range_lbl} | Generated: {gen_time} | Farm: {metadata.get('farm_name', 'All')} | Crop: {metadata.get('crop_name', 'All')}"
    s_cell.font = Font(name="Calibri", size=10, italic=True, color="475569")
    s_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20


def _style_excel_headers(ws, row_idx, headers):
    """Format table header row with bold white text on emerald green."""
    header_fill = PatternFill(start_color="166534", end_color="166534", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="medium", color="0F172A")
    )

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = thin_border
    ws.row_dimensions[row_idx].height = 24


def _auto_fit_columns(ws, min_col=1, max_col=10):
    """Auto-adjust column widths based on content length."""
    for col in range(min_col, max_col + 1):
        col_letter = get_column_letter(col)
        max_len = 0
        for cell in ws[col_letter]:
            if cell.row > 2 and cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)


def generate_excel_report(category, data, metadata, lang="en"):
    """
    Generate professional .xlsx workbook with openpyxl.
    Supports auto-filters, freeze panes, real numeric types, and currency formats.
    """
    wb = openpyxl.Workbook()
    title = _get_title(category, lang)

    # 1. OVERVIEW
    if category == "overview":
        ws = wb.active
        ws.title = "Overview_KPIs"
        _style_excel_sheet(ws, title, metadata)

        sum_m = data.get("summary", {})
        headers = ["Metric Category", "Indicator Name", "Metric Value", "Unit / Format"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        kpis = [
            ("Farms", "Total Farms", sum_m.get("total_farms", 0), "Count"),
            ("Farms", "Total Farm Area", sum_m.get("total_farm_area", 0.0), "Acres"),
            ("Crops", "Total Crops", sum_m.get("total_crops", 0), "Count"),
            ("Crops", "Active Crops", sum_m.get("active_crops", 0), "Count"),
            ("Crops", "Total Cultivated Area", sum_m.get("total_cultivated_area", 0.0), "Acres"),
            ("Finances", "Total Expenses", float(sum_m.get("total_expenses", 0.0)), "INR"),
            ("Finances", "Total Revenue", float(sum_m.get("total_revenue", 0.0)), "INR"),
            ("Finances", "Net Profit / Loss", float(sum_m.get("net_profit", 0.0)), "INR"),
            ("Finances", "Profit Margin", float(sum_m.get("margin_pct", 0.0)), "Percent"),
            ("Irrigation", "Total Water Applied", float(sum_m.get("total_water_volume_mm", 0.0)), "mm"),
            ("Irrigation", "Water Saved", float(sum_m.get("water_saved_mm", 0.0)), "mm"),
            ("Disease", "Total Scans", sum_m.get("total_diagnoses", 0), "Count"),
            ("Disease", "Foliage Health Ratio", float(sum_m.get("health_ratio_pct", 0.0)), "Percent"),
            ("Activities", "Total Tasks", sum_m.get("total_activities", 0), "Count"),
            ("Activities", "Completion Rate", float(sum_m.get("completion_rate", 0.0)), "Percent"),
            ("Inventory", "Total Stock Valuation", float(sum_m.get("total_inventory_valuation", 0.0)), "INR"),
            ("Alerts", "Total Notifications", sum_m.get("total_alerts", 0), "Count"),
        ]

        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, (cat_name, ind_name, val, unit) in enumerate(kpis, 5):
            r = [cat_name, ind_name, val, unit]
            ws.append(r)
            if idx % 2 == 0:
                for c in range(1, 5):
                    ws.cell(row=idx, column=c).fill = zebra_fill
            if unit == "INR":
                ws.cell(row=idx, column=3).number_format = "[$₹-4009] #,##0.00"
            elif unit == "Percent":
                ws.cell(row=idx, column=3).number_format = "0.0\"%\""

        ws.freeze_panes = "A5"
        ws.auto_filter.ref = f"A4:D{len(kpis) + 4}"
        _auto_fit_columns(ws, 1, 4)

    # 2. CROPS
    elif category == "crops":
        ws = wb.active
        ws.title = "Crops_Registry"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Crop ID", "Crop Name", "Variety", "Growth Stage", "Planting Date", "Expected Harvest", "Area (Acres)", "Farm Name", "Days in Ground"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        crops = data.get("crops", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, c in enumerate(crops, 5):
            ws.append([
                c.get("id"),
                c.get("crop_name"),
                c.get("variety") or "-",
                c.get("growth_status") or "-",
                str(c.get("planting_date") or "-"),
                str(c.get("expected_harvest_date") or "-"),
                float(c.get("cultivated_area") or 0.0),
                c.get("farm_name") or "-",
                int(c.get("days_in_ground") or 0),
            ])
            if idx % 2 == 0:
                for col in range(1, 10):
                    ws.cell(row=idx, column=col).fill = zebra_fill
            ws.cell(row=idx, column=7).number_format = "0.0"

        ws.freeze_panes = "A5"
        if crops:
            ws.auto_filter.ref = f"A4:I{len(crops) + 4}"
        _auto_fit_columns(ws, 1, 9)

    # 3. DISEASE
    elif category == "disease":
        ws = wb.active
        ws.title = "Disease_Diagnoses"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Scan ID", "Date", "Time", "Crop Name", "Diagnosed Condition", "Confidence (%)", "Health Status", "Recommended Guidance"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        scans = data.get("scans", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, s in enumerate(scans, 5):
            ws.append([
                s.get("id"),
                str(s.get("date") or "-"),
                str(s.get("time") or "-"),
                s.get("crop_name"),
                s.get("condition"),
                float(s.get("confidence") or 0.0),
                "Healthy" if s.get("is_healthy") else "Diseased",
                s.get("treatment_summary") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 9):
                    ws.cell(row=idx, column=col).fill = zebra_fill
            ws.cell(row=idx, column=6).number_format = "0.0\"%\""

        ws.freeze_panes = "A5"
        if scans:
            ws.auto_filter.ref = f"A4:H{len(scans) + 4}"
        _auto_fit_columns(ws, 1, 8)

    # 4. IRRIGATION
    elif category == "irrigation":
        ws = wb.active
        ws.title = "Irrigation_Telemetry"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Record ID", "Date", "Time", "Crop Name", "Soil Type", "Growth Stage", "Moisture (%)", "Temp (°C)", "Rainfall (mm)", "Action", "Volume (mm)", "Reason"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        recs = data.get("recommendations", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, r in enumerate(recs, 5):
            ws.append([
                r.get("id"),
                str(r.get("date") or "-"),
                str(r.get("time") or "-"),
                r.get("crop_name"),
                r.get("soil_type") or "-",
                r.get("growth_stage") or "-",
                float(r.get("soil_moisture") or 0.0),
                float(r.get("temperature") or 0.0),
                float(r.get("rainfall") or 0.0),
                r.get("action") or "-",
                float(r.get("water_amount_mm") or 0.0),
                r.get("reason") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 13):
                    ws.cell(row=idx, column=col).fill = zebra_fill
            ws.cell(row=idx, column=7).number_format = "0.0\"%\""
            ws.cell(row=idx, column=8).number_format = "0.0"
            ws.cell(row=idx, column=11).number_format = "0.0"

        ws.freeze_panes = "A5"
        if recs:
            ws.auto_filter.ref = f"A4:L{len(recs) + 4}"
        _auto_fit_columns(ws, 1, 12)

    # 5. FINANCIAL (Multi-Sheet: Expenses + Harvests + Crop Profitability)
    elif category == "financial":
        # Sheet 1: Expenses
        ws1 = wb.active
        ws1.title = "Expenses_Ledger"
        _style_excel_sheet(ws1, "Farm Expenses Ledger", metadata)

        headers1 = ["Expense ID", "Date", "Category", "Crop Name", "Farm Name", "Amount (INR)", "Description", "Notes"]
        ws1.append([])
        _style_excel_headers(ws1, 4, headers1)

        exps = data.get("expenses", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, e in enumerate(exps, 5):
            ws1.append([
                e.get("id"),
                str(e.get("date") or "-"),
                e.get("category"),
                e.get("crop_name"),
                e.get("farm_name"),
                float(e.get("amount") or 0.0),
                e.get("description") or "-",
                e.get("notes") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 9):
                    ws1.cell(row=idx, column=col).fill = zebra_fill
            ws1.cell(row=idx, column=6).number_format = "[$₹-4009] #,##0.00"

        ws1.freeze_panes = "A5"
        if exps:
            ws1.auto_filter.ref = f"A4:H{len(exps) + 4}"
        _auto_fit_columns(ws1, 1, 8)

        # Sheet 2: Harvests
        ws2 = wb.create_sheet(title="Harvest_and_Sales")
        _style_excel_sheet(ws2, "Harvest & Revenue Sales", metadata)

        headers2 = ["Harvest ID", "Date", "Crop Name", "Farm Name", "Quantity", "Unit", "Price / Unit (INR)", "Total Revenue (INR)", "Buyer Name"]
        ws2.append([])
        _style_excel_headers(ws2, 4, headers2)

        harvs = data.get("harvests", [])
        for idx, h in enumerate(harvs, 5):
            ws2.append([
                h.get("id"),
                str(h.get("date") or "-"),
                h.get("crop_name"),
                h.get("farm_name"),
                float(h.get("quantity") or 0.0),
                h.get("unit") or "kg",
                float(h.get("price_per_unit") or 0.0),
                float(h.get("total_revenue") or 0.0),
                h.get("buyer_name") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 10):
                    ws2.cell(row=idx, column=col).fill = zebra_fill
            ws2.cell(row=idx, column=5).number_format = "#,##0.0"
            ws2.cell(row=idx, column=7).number_format = "[$₹-4009] #,##0.00"
            ws2.cell(row=idx, column=8).number_format = "[$₹-4009] #,##0.00"

        ws2.freeze_panes = "A5"
        if harvs:
            ws2.auto_filter.ref = f"A4:I{len(harvs) + 4}"
        _auto_fit_columns(ws2, 1, 9)

        # Sheet 3: Crop Profitability
        ws3 = wb.create_sheet(title="Crop_Profitability")
        _style_excel_sheet(ws3, "Crop-Wise Profitability Analysis", metadata)

        headers3 = ["Crop Name", "Expenses (INR)", "Revenue (INR)", "Net Profit / Loss (INR)", "Margin (%)"]
        ws3.append([])
        _style_excel_headers(ws3, 4, headers3)

        cprofs = data.get("crop_profitability", [])
        for idx, cp in enumerate(cprofs, 5):
            ws3.append([
                cp.get("crop_name"),
                float(cp.get("expenses") or 0.0),
                float(cp.get("revenue") or 0.0),
                float(cp.get("net_profit") or 0.0),
                float(cp.get("margin_pct") or 0.0),
            ])
            if idx % 2 == 0:
                for col in range(1, 6):
                    ws3.cell(row=idx, column=col).fill = zebra_fill
            ws3.cell(row=idx, column=2).number_format = "[$₹-4009] #,##0.00"
            ws3.cell(row=idx, column=3).number_format = "[$₹-4009] #,##0.00"
            ws3.cell(row=idx, column=4).number_format = "[$₹-4009] #,##0.00"
            ws3.cell(row=idx, column=5).number_format = "0.0\"%\""

        ws3.freeze_panes = "A5"
        if cprofs:
            ws3.auto_filter.ref = f"A4:E{len(cprofs) + 4}"
        _auto_fit_columns(ws3, 1, 5)

    # 6. HARVEST
    elif category == "harvest":
        ws = wb.active
        ws.title = "Harvest_and_Sales"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Harvest ID", "Date", "Crop Name", "Farm Name", "Quantity", "Unit", "Price / Unit (INR)", "Total Revenue (INR)", "Buyer Name", "Notes"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        harvs = data.get("harvests", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, h in enumerate(harvs, 5):
            ws.append([
                h.get("id"),
                str(h.get("date") or "-"),
                h.get("crop_name"),
                h.get("farm_name"),
                float(h.get("quantity") or 0.0),
                h.get("unit") or "kg",
                float(h.get("price_per_unit") or 0.0),
                float(h.get("total_revenue") or 0.0),
                h.get("buyer_name") or "-",
                h.get("notes") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 11):
                    ws.cell(row=idx, column=col).fill = zebra_fill
            ws.cell(row=idx, column=5).number_format = "#,##0.0"
            ws.cell(row=idx, column=7).number_format = "[$₹-4009] #,##0.00"
            ws.cell(row=idx, column=8).number_format = "[$₹-4009] #,##0.00"

        ws.freeze_panes = "A5"
        if harvs:
            ws.auto_filter.ref = f"A4:J{len(harvs) + 4}"
        _auto_fit_columns(ws, 1, 10)

    # 7. ACTIVITIES
    elif category == "activities":
        ws = wb.active
        ws.title = "Farm_Activities"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Activity ID", "Title", "Category", "Crop Name", "Farm Name", "Scheduled Date", "Time", "Priority", "Status", "Completed Date"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        acts = data.get("activities", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, a in enumerate(acts, 5):
            ws.append([
                a.get("id"),
                a.get("title"),
                a.get("category"),
                a.get("crop_name") or "-",
                a.get("farm_name") or "-",
                str(a.get("scheduled_date") or "-"),
                str(a.get("scheduled_time") or "-"),
                a.get("priority") or "-",
                a.get("status") or "-",
                str(a.get("completed_date") or "-"),
            ])
            if idx % 2 == 0:
                for col in range(1, 11):
                    ws.cell(row=idx, column=col).fill = zebra_fill

        ws.freeze_panes = "A5"
        if acts:
            ws.auto_filter.ref = f"A4:J{len(acts) + 4}"
        _auto_fit_columns(ws, 1, 10)

    # 8. INVENTORY
    elif category == "inventory":
        ws = wb.active
        ws.title = "Inventory_Stock"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Item ID", "Item Name", "Category", "Quantity", "Unit", "Unit Price (INR)", "Total Value (INR)", "Buffer Threshold", "Expiry Date", "Location"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        items = data.get("items", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, itm in enumerate(items, 5):
            ws.append([
                itm.get("id"),
                itm.get("item_name"),
                itm.get("category"),
                float(itm.get("quantity") or 0.0),
                itm.get("unit") or "units",
                float(itm.get("unit_price") or 0.0),
                float(itm.get("total_value") or 0.0),
                float(itm.get("low_stock_threshold") or 0.0),
                str(itm.get("expiry_date") or "-"),
                itm.get("location") or "-",
            ])
            if idx % 2 == 0:
                for col in range(1, 11):
                    ws.cell(row=idx, column=col).fill = zebra_fill
            ws.cell(row=idx, column=4).number_format = "#,##0.0"
            ws.cell(row=idx, column=6).number_format = "[$₹-4009] #,##0.00"
            ws.cell(row=idx, column=7).number_format = "[$₹-4009] #,##0.00"

        ws.freeze_panes = "A5"
        if items:
            ws.auto_filter.ref = f"A4:J{len(items) + 4}"
        _auto_fit_columns(ws, 1, 10)

    # 9. ALERTS
    elif category == "alerts":
        ws = wb.active
        ws.title = "Alerts_Log"
        _style_excel_sheet(ws, title, metadata)

        headers = ["Notification ID", "Created At", "Type", "Severity", "Title", "Message", "Is Read"]
        ws.append([])
        _style_excel_headers(ws, 4, headers)

        notifs = data.get("notifications", [])
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, n in enumerate(notifs, 5):
            ws.append([
                n.get("id"),
                str(n.get("created_at") or "-"),
                n.get("type"),
                n.get("severity"),
                n.get("title"),
                n.get("message"),
                "Yes" if n.get("is_read") else "No",
            ])
            if idx % 2 == 0:
                for col in range(1, 8):
                    ws.cell(row=idx, column=col).fill = zebra_fill

        ws.freeze_panes = "A5"
        if notifs:
            ws.auto_filter.ref = f"A4:G{len(notifs) + 4}"
        _auto_fit_columns(ws, 1, 7)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
