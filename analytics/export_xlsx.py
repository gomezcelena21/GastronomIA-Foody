"""
Gastro IA - XLSX Export
Creates an Excel file with all tables for Power BI.
"""

import os
import psycopg2
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from pathlib import Path

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "gastro_ia",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", ""),  # antes: contraseña escrita acá. Usá: set PGPASSWORD=tu_clave
}

def export_xlsx():
    """Export all data to a single XLSX file."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    wb = Workbook()
    
    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="7A8B6F", end_color="7A8B6F", fill_type="solid")
    
    # 1. Restaurants sheet
    ws = wb.active
    ws.title = "Restaurantes"
    
    cur.execute("""
        SELECT 
            r.restaurant_id,
            r.name,
            r.province,
            r.city,
            r.neighborhood,
            r.address,
            r.latitude,
            r.longitude,
            r.category,
            r.phone,
            r.price_range,
            r.rating,
            r.source_type,
            r.confidence_level,
            rf.has_gluten_free_options,
            rf.has_vegetarian_options,
            rf.has_vegan_options,
            s.name as source_name
        FROM restaurants r
        LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
        LEFT JOIN sources s ON r.source_id = s.source_id
        WHERE r.is_active = TRUE
        ORDER BY r.province, r.city, r.name
    """)
    
    # Headers
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    # Data
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Auto-fit columns
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 30)
    
    print(f"Restaurantes: {ws.max_row - 1} rows")
    
    # 2. By Province sheet
    ws2 = wb.create_sheet("Por Provincia")
    cur.execute("""
        SELECT 
            province,
            COUNT(*) as total,
            COUNT(CASE WHEN geom IS NOT NULL THEN 1 END) as con_coordenadas,
            COUNT(CASE WHEN phone IS NOT NULL THEN 1 END) as con_telefono,
            ROUND(AVG(price_range)::numeric, 1) as precio_promedio
        FROM restaurants WHERE is_active = TRUE
        GROUP BY province ORDER BY total DESC
    """)
    
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws2.cell(row=row_idx, column=col_idx, value=value)
    
    for column in ws2.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value)
        ws2.column_dimensions[column[0].column_letter].width = min(max_length + 2, 30)
    
    print(f"Por Provincia: {ws2.max_row - 1} rows")
    
    # 3. By Cuisine sheet
    ws3 = wb.create_sheet("Por Tipo Cocina")
    cur.execute("""
        SELECT 
            unnest(cuisine_type) as cuisine,
            COUNT(*) as total
        FROM restaurants WHERE is_active = TRUE AND cuisine_type IS NOT NULL
        GROUP BY cuisine ORDER BY total DESC
    """)
    
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws3.cell(row=row_idx, column=col_idx, value=value)
    
    for column in ws3.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value)
        ws3.column_dimensions[column[0].column_letter].width = min(max_length + 2, 30)
    
    print(f"Por Tipo Cocina: {ws3.max_row - 1} rows")
    
    # 4. By Category sheet
    ws4 = wb.create_sheet("Por Categoria")
    cur.execute("""
        SELECT 
            category,
            COUNT(*) as total,
            ROUND(AVG(price_range)::numeric, 1) as precio_promedio
        FROM restaurants WHERE is_active = TRUE AND category IS NOT NULL
        GROUP BY category ORDER BY total DESC
    """)
    
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws4.cell(row=row_idx, column=col_idx, value=value)
    
    for column in ws4.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value)
        ws4.column_dimensions[column[0].column_letter].width = min(max_length + 2, 30)
    
    print(f"Por Categoria: {ws4.max_row - 1} rows")
    
    # 5. Dietary Features sheet
    ws5 = wb.create_sheet("Caracteristicas Dietarias")
    cur.execute("""
        SELECT 
            r.province,
            COUNT(CASE WHEN rf.has_gluten_free_options = TRUE THEN 1 END) as sin_tacc,
            COUNT(CASE WHEN rf.has_vegetarian_options = TRUE THEN 1 END) as vegetariano,
            COUNT(CASE WHEN rf.has_vegan_options = TRUE THEN 1 END) as vegano,
            COUNT(CASE WHEN rf.has_lactose_free_options = TRUE THEN 1 END) as sin_lactosa,
            COUNT(*) as total
        FROM restaurants r
        LEFT JOIN restaurant_features rf ON r.restaurant_id = rf.restaurant_id
        WHERE r.is_active = TRUE
        GROUP BY r.province ORDER BY total DESC
    """)
    
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws5.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws5.cell(row=row_idx, column=col_idx, value=value)
    
    for column in ws5.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value)
        ws5.column_dimensions[column[0].column_letter].width = min(max_length + 2, 30)
    
    print(f"Caracteristicas Dietarias: {ws5.max_row - 1} rows")
    
    # 6. Sources sheet
    ws6 = wb.create_sheet("Fuentes")
    cur.execute("""
        SELECT 
            s.name,
            s.source_type,
            s.reliability,
            COUNT(r.restaurant_id) as restaurantes
        FROM sources s
        LEFT JOIN restaurants r ON s.source_id = r.source_id AND r.is_active = TRUE
        GROUP BY s.source_id, s.name, s.source_type, s.reliability
        ORDER BY restaurantes DESC
    """)
    
    headers = [desc[0] for desc in cur.description]
    for col, header in enumerate(headers, 1):
        cell = ws6.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
    
    for row_idx, row in enumerate(cur.fetchall(), 2):
        for col_idx, value in enumerate(row, 1):
            ws6.cell(row=row_idx, column=col_idx, value=value)
    
    for column in ws6.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value)
        ws6.column_dimensions[column[0].column_letter].width = min(max_length + 2, 30)
    
    print(f"Fuentes: {ws6.max_row - 1} rows")
    
    # Save file
    analytics_dir = Path(__file__).parent
    wb.save(analytics_dir / "GastroIA_PowerBI.xlsx")
    print("\nXLSX file saved: analytics/GastroIA_PowerBI.xlsx")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    export_xlsx()
