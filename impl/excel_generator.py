import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from io import BytesIO
import pandas as pd
from io import BytesIO

def generate_feeder_pole_excel(feeder_name,subdivision, poles):
    data = []
    for idx, pole in enumerate(poles, start=1):
        existing = pole.existing_info
        proposed = pole.proposed_materials

        row = [
            idx,
            subdivision,
            feeder_name,
            pole.lat,
            pole.long,
            pole.tc.tc_number,
            pole.tc.name,
            existing.get("Type of Arrangement", ""),
            pole.span_length,
            existing.get("Span Three Phase", ""),
            existing.get("Span Single Phase", ""),
            existing.get("Type of Conductor", ""),
            existing.get("Type of Pole", ""),
            existing.get("Condition of Pole", ""),
            existing.get("Danger Board", ""),
            existing.get("Barbed Wire", ""),
            existing.get("LT Cross Arm", ""),
            existing.get("C Type L T cross arm", ""),
            existing.get("L T Porcelain Pin Insulators", ""),
            existing.get("Connection Box", ""),
            existing.get("Stay set (GUY SET)", ""),
            existing.get("Coil Earthing", ""),
            existing.get("Guarding", ""),
            existing.get("TREE CUTTING", ""),
            # Proposed section
            proposed.get("8mtr PSC", ""),
            proposed.get("Danger Board", ""),
            proposed.get("Barbed Wire", ""),
            proposed.get("Stay set (GUY SET)", ""),
            proposed.get("Coil Earthing", ""),
            proposed.get("Self-Tightening Anchoring Clamp", ""),
            proposed.get("Suspension Clamp", ""),
            proposed.get("Mid‐span Joints", ""),
            proposed.get("Stainless steel-20mm*0.7mm", ""),
            proposed.get("IPC", ""),
            proposed.get("EYE HOOKS", ""),
            proposed.get("3Core Wire", ""),
            proposed.get("1Core Wire", ""),
            proposed.get("1PH Connection Box(8 connections)", ""),
            proposed.get("3PH Connection Box(4 connections)", ""),
            proposed.get("4Cx10 mm2 LT PVC Cable", ""),
            proposed.get("4Cx16 mm2 LT PVC Cable", ""),
        ]
        data.append(row)

    # Step 5: Create DataFrame
    df = pd.DataFrame(data)

    # Step 6: Create Excel file with 4 header rows
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Pole Schedule")
        writer.sheets["Pole Schedule"] = worksheet
        basic_formater = {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1}
        # Header formatting
        title_format = basic_formater.copy()
        title_format['bg_color'] = '#F4B084'
        bold_center = workbook.add_format(title_format)
        
        existing_format = basic_formater.copy()
        existing_format['bg_color'] = '#FFFF00'
        existing_title_workbook = workbook.add_format(existing_format)
        
        new_format = basic_formater.copy()
        new_format['bg_color'] = '#B4C6E7'
        new_title_workbook = workbook.add_format(new_format)
        subHeader_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        pass
        # First Row: Main Title
        worksheet.merge_range('D1:AR1', "ACTUAL POLE SCHEDULE", bold_center)

        # Second Row: Blank
        pass

        # Third Row: Two Sections
        worksheet.merge_range('D3:AA3', 'Existing Data', existing_title_workbook)
        worksheet.merge_range('AB3:AR3', 'New Arrangement', new_title_workbook)

        # Fourth Row: Column Names
        headers = [
            "Sr no.", "SUB-DIVISION", "FEEDER NAME & CODE", "LATITUDE", "LONGITUDE", "TC LOCATION NO", "TC NAME",
            "Type of Arrangement", "SPAN LENGTH", "Span Three Phase", "Span Single Phase",
            "Type of Conductor(Weasel/Rabbit/Dog)", "Type of PSC/RSJ", "Condition of Pole(Good,Damage /Rusted/Bend etc.)",
            "Danger Board", "Barbedwire", "LT Cross Arm", "C Type L T cross arm", "L T Procelain Pin Insulators",
            "Connection Box", "Stay set (GUY SET)", "Coil Earthing", "Guarding", "REQUIREMENTS OF TREE CUTTING (YES/NO)",
            # New Arrangements
            "8mtr PSC", "Danger Board", "Barbed wire", "Stay set (GUY SET)", "Coil Earthing",
            "Self-Tightening Anchoring", "Self-locking suspensionclam with pole bracket &buckle",
            "Mid-span Tension Joints", "Stainless steel of size strap 20mm*0.7mm& Buckle width 20 mm", "Insulation piercing connector  (I P C)",
            "EYE HOOKS", "AB XLPE CABLE 1.1 KV 3C X 50 SQ.MM+1Cx25 SQ. MM.+1x35 SQ. MM.", "AB XLPE CABLE 1.1 KV 1Cx 35 SQ MM + 1CX16 SQ MM + 25 SQ MM ", "Supply of 1-ph Pole mounted service connection box for LT connections (8 connections)", "Supply of 3-ph Pole mounted service connection box for LT connections (4 connections)",
            "Supply of 4Cx10 mm2 LT PVC Cable", "Supply of 4Cx16 mm2 LT PVC Cable"
        ]
        start_column = 3
        for col_num, col_title in enumerate(headers):
            colIndex = col_num + start_column
            worksheet.merge_range(3, colIndex, 5, colIndex,col_title,subHeader_format)
        # Fifth Row: Units (manually set as needed)
        units = ["Unit"]+ [""] * 6 + ["Type", "MTR", "MTR", "MTR", "Type", "Type", "Type", "No", "KG", "NO", "No", "No", "NO", "No", "No", "MTR", "NO", "NO", "NO"] + \
                ["No", "No", "No", "No", "No", "No", "No", "No", "No", "MTR", "MTR", "NO", "NO", "MTR", "MTR"]
        for col_num, unit in enumerate(units):
            colIndex = col_num + start_column
            worksheet.write(6, colIndex, unit)
        
        # Step 7: Write Data
        for row_num, row_data in enumerate(data, start=7):  # Start after 5 header rows
            for col_num, cell in enumerate(row_data):
                colIndex = col_num + start_column
                worksheet.write(row_num, colIndex, cell)

        # writer.close()

    output.seek(0)
    return output