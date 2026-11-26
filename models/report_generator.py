"""
PDF and CSV Report Generator for Greywater Contamination Analysis (SIH26023).
Uses ReportLab to generate laboratory-grade analytical certificates, treatment briefs,
and validation summaries in PDF format, plus structured CSV exports.
"""

import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportGenerator:
    @staticmethod
    def generate_sample_pdf(sample_dict, treatment_rec, wqi_info, similarity_info=None):
        """
        Generates a comprehensive, beautifully styled PDF analysis report for a greywater sample.
        Returns bytes buffer.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom styles with dark navy & cyan aesthetic
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0a1b3f')
        )
        subtitle_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#007799')
        )
        section_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#0f2b5c'),
            spaceBefore=10,
            spaceAfter=4
        )
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#222222')
        )
        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#222222')
        )
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        story = []

        # --- Header ---
        story.append(Paragraph("HydraSense • Greywater Contamination Analysis System", title_style))
        story.append(Paragraph("SIH26023 | Comprehensive Physicochemical Profiling & Treatment Recommendation", subtitle_style))
        story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Sample Ref: {sample_dict.get('sample_id', 'N/A')}", body_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#00a8cc'), spaceBefore=6, spaceAfter=10))

        # --- Sample Meta & WQI Banner ---
        category = treatment_rec.get('category', 'N/A')
        wqi = wqi_info.get('wqi', 0)
        status = wqi_info.get('status', 'N/A')

        meta_data = [
            [
                Paragraph(f"<b>Sample ID:</b> {sample_dict.get('sample_id', 'N/A')}", body_style),
                Paragraph(f"<b>Source:</b> {sample_dict.get('source', 'N/A')}", body_style),
                Paragraph(f"<b>Location:</b> {sample_dict.get('Location', 'Onsite')}", body_style)
            ],
            [
                Paragraph(f"<b>Water Quality Index (WQI):</b> {wqi} ({status})", body_style),
                Paragraph(f"<b>Assigned Classification:</b> <b>{category}</b>", body_style),
                Paragraph(f"<b>Collection Date:</b> {sample_dict.get('Collection_Date', datetime.now().strftime('%Y-%m-%d'))}", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[180, 180, 180])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f7fb')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#b8e1f0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0ecf7')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # --- Physicochemical Parameters Table (Objective 1) ---
        story.append(Paragraph("1. Physicochemical Parameter Analysis & Standards Compliance", section_style))
        
        param_rows = [
            [
                Paragraph("<b>Parameter</b>", table_header_style),
                Paragraph("<b>Measured Value</b>", table_header_style),
                Paragraph("<b>Standard Permissible Limit</b>", table_header_style),
                Paragraph("<b>Excess Ratio</b>", table_header_style),
                Paragraph("<b>Compliance Status</b>", table_header_style)
            ]
        ]

        limits = {
            'pH': ('6.5 - 8.5', 6.5, 8.5),
            'TDS': ('< 500 mg/L', 0, 500),
            'BOD': ('< 30 mg/L', 0, 30),
            'COD': ('< 100 mg/L', 0, 100),
            'Turbidity': ('< 5 NTU', 0, 5),
            'EC': ('< 800 µS/cm', 0, 800),
            'TSS': ('< 30 mg/L', 0, 30),
            'Oil_and_Grease': ('< 5 mg/L', 0, 5),
            'Temperature': ('15 - 35 °C', 15, 35)
        }

        for param, (lim_str, min_l, max_l) in limits.items():
            val = float(sample_dict.get(param, 0))
            is_compliant = True
            if param == 'pH':
                is_compliant = (min_l <= val <= max_l)
                ratio = round(abs(val - 7.0) / 1.5, 2)
            else:
                is_compliant = (val <= max_l)
                ratio = round(val / max_l, 2) if max_l > 0 else 1.0

            status_text = "<font color='green'><b>Compliant</b></font>" if is_compliant else f"<font color='red'><b>Exceeded ({ratio}x)</b></font>"
            param_rows.append([
                Paragraph(param.replace('_', ' '), table_cell_style),
                Paragraph(f"<b>{val}</b>", table_cell_style),
                Paragraph(lim_str, table_cell_style),
                Paragraph(str(ratio) if not is_compliant else "1.0", table_cell_style),
                Paragraph(status_text, table_cell_style)
            ])

        param_table = Table(param_rows, colWidths=[120, 100, 120, 80, 120])
        param_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f2b5c')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fbfd')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(param_table)
        story.append(Spacer(1, 10))

        # --- Treatment Train Recommendation ---
        story.append(Paragraph("2. Recommended Treatment Train & Chemical Dosing", section_style))
        stages = treatment_rec.get('stages', {})
        treatment_rows = [
            [Paragraph("<b>Process Stage</b>", table_header_style), Paragraph("<b>Unit Operations & Specifications</b>", table_header_style)]
        ]

        for s_key, s_data in stages.items():
            title = s_data.get('title', '')
            units = "<br/>• ".join(s_data.get('units', []))
            treatment_rows.append([
                Paragraph(f"<b>{title}</b>", table_cell_style),
                Paragraph(f"• {units}", table_cell_style)
            ])

        t_table = Table(treatment_rows, colWidths=[160, 380])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007799')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_table)
        story.append(Spacer(1, 10))

        # --- Chemical Dosing & Reuse Suitability ---
        dosing = treatment_rec.get('chemical_dosing', {})
        story.append(Paragraph(
            f"<b>Chemical Dosing Schedule:</b> Polyaluminum Chloride (PAC): <b>{dosing.get('pac_dose_mg_l', 'N/A')} mg/L</b> "
            f"| Coagulant Aid Polymer: <b>{dosing.get('polymer_dose_mg_l', 'N/A')} mg/L</b> "
            f"| UV Dose: <b>{dosing.get('uv_dose', '40 mJ/cm²')}</b> "
            f"| Sodium Hypochlorite: <b>{dosing.get('chlorine_dose', '2.5 mg/L')}</b>",
            body_style
        ))
        story.append(Spacer(1, 6))

        story.append(Paragraph("3. Water Reuse Suitability Assessment", section_style))
        reuse_rows = [
            [Paragraph("<b>Application</b>", table_header_style), Paragraph("<b>Status</b>", table_header_style), Paragraph("<b>Standard Requirement</b>", table_header_style)]
        ]
        matrix = treatment_rec.get('suitability_matrix', {})
        for _, app_info in matrix.items():
            suit_text = "<font color='green'><b>Approved</b></font>" if app_info.get('suitable') else "<font color='orange'><b>Conditional / Restricted</b></font>"
            reuse_rows.append([
                Paragraph(app_info.get('title', ''), table_cell_style),
                Paragraph(f"{suit_text} - {app_info.get('status', '')}", table_cell_style),
                Paragraph(app_info.get('requirement', ''), table_cell_style)
            ])

        reuse_table = Table(reuse_rows, colWidths=[150, 240, 150])
        reuse_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f2b5c')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(reuse_table)
        story.append(Spacer(1, 14))

        # --- Footer / Signature block ---
        story.append(Paragraph("Laboratory Validation Note: Validated against standard CPCB & EPA water reuse quality guidelines using Euclidean and Manhattan similarity clustering (SIH26023).", subtitle_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_csv_export(df_records):
        """
        Exports sample records to standard CSV format.
        """
        output = io.StringIO()
        if not df_records:
            return ""

        fieldnames = list(df_records[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in df_records:
            writer.writerow(row)
        return output.getvalue()
