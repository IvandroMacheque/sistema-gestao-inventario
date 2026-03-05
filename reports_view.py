import flet as ft
import data_service as ds
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tempfile
import utils

def ReportsView(page: ft.Page):
    # --- State ---
    date_start = None
    date_end = None

    # --- UI Elements for Reports ---
    report_container = ft.Column(spacing=20)

    # --- Date Selection ---
    def on_start_change(e):
        nonlocal date_start
        if date_picker_start.value:
            date_start = date_picker_start.value
            start_date_btn.text = date_start.strftime("%d/%m/%Y")
            page.update()

    def on_end_change(e):
        nonlocal date_end
        if date_picker_end.value:
            date_end = date_picker_end.value
            end_date_btn.text = date_end.strftime("%d/%m/%Y")
            page.update()

    date_picker_start = ft.DatePicker(on_change=on_start_change)
    date_picker_end = ft.DatePicker(on_change=on_end_change)
    
    # --- Export Logic ---
    export_type = None # "PDF" or "EXCEL"

    def generate_bar_chart(item_counts, title, filename):
        items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        names = [ds.get_item_name(i[0]) for i in items]
        counts = [i[1] for i in items]
        
        plt.figure(figsize=(6, 4))
        plt.bar(names, counts, color='skyblue')
        plt.title(title)
        plt.ylabel('Quantidade de Movimentações')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def generate_pie_chart(filtered, title, filename):
        type_counts = {}
        for m in filtered:
            type_counts[m["tipo"]] = type_counts.get(m["tipo"], 0) + 1
        
        labels = list(type_counts.keys())
        sizes = list(type_counts.values())
        
        plt.figure(figsize=(6, 4))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
        plt.title(title)
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def generate_loss_chart(item_losses, title, filename):
        items = sorted(item_losses.items(), key=lambda x: x[1], reverse=True)[:5]
        names = [ds.get_item_name(i[0]) for i in items]
        losses = [i[1] for i in items]
        
        plt.figure(figsize=(6, 4))
        plt.bar(names, losses, color='salmon')
        plt.title(title)
        plt.ylabel('Quantidade Perdida')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def get_smart_annotations(summary, filtered):
        notes = []
        if summary["total_perda"] > 0:
            notes.append(f"• Identificado um volume de {summary['total_perda']} perdas. O item '{summary['most_lost_item']}' foi o mais afetado.")
        
        # Check for items below minimum using efficient helper
        total_balances = ds.get_total_balances()
        for item in ds.items:
            balance = total_balances.get(item["id"], 0)
            if balance < item.get("quantidade_minima", 0):
                notes.append(f"• Alerta: O item '{item['nome']}' está abaixo do mínimo ({balance}/{item['quantidade_minima']}).")
        
        if summary["top_apt"] != "-":
            notes.append(f"• O apartamento '{summary['top_apt']}' apresentou a maior rotatividade do período.")
            
        return notes

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                # Garante que o caminho tem a extensão correta
                filepath = e.path
                if export_type == "EXCEL" and not filepath.lower().endswith(".xlsx"):
                    filepath += ".xlsx"
                elif export_type == "PDF" and not filepath.lower().endswith(".pdf"):
                    filepath += ".pdf"
                
                page.snack_bar = ft.SnackBar(ft.Text("Gerando arquivo..."), bgcolor=ft.Colors.BLUE_700)
                page.snack_bar.open = True
                page.update()
                
                if export_type == "EXCEL":
                    save_excel(filepath)
                elif export_type == "PDF":
                    save_pdf(filepath)
                page.snack_bar = ft.SnackBar(ft.Text("Arquivo salvo com sucesso!"), bgcolor=ft.Colors.GREEN_700)
            except Exception as ex:
                print(f"[EXPORT ERRO] {ex}")
                import traceback
                traceback.print_exc()
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao exportar: {str(ex)}"), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.extend([date_picker_start, date_picker_end, file_picker])

    def save_excel(dest_path):
        import tempfile
        import shutil
        
        filters = get_common_filters()
        filtered = ds.get_movements(limit=5000, filters=filters)
        
        data = []
        for m in filtered:
            data.append({
                "Data": m["created_at"].strftime("%d/%m/%Y %H:%M") if m["created_at"] else "",
                "Tipo": m["tipo"],
                "Item": ds.get_item_name(m["item_id"]),
                "Origem": ds.get_location_name(m["origem_id"]),
                "Destino": ds.get_location_name(m["destino_id"]),
                "Quantidade": m["quantidade"],
                "Observação": m.get("observacao", "")
            })
        
        if not data:
            raise Exception("Não há dados para exportar com os filtros selecionados.")

        df = pd.DataFrame(data)
        
        # Gera num temp file primeiro, depois copia pro destino
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            df.to_excel(tmp_path, index=False, engine='openpyxl')
            shutil.copy2(tmp_path, dest_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def save_pdf(dest_path):
        import tempfile
        import shutil
        
        filters = get_common_filters()
        summary = generate_summary_data(filters)
        movs = summary["raw_data"]
        
        # Gera num temp file primeiro, depois copia pro destino
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            doc = SimpleDocTemplate(tmp_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph("RELATÓRIO DE MOVIMENTAÇÕES", styles['Title']))
            elements.append(Spacer(1, 12))
            
            table_data = [["Data", "Tipo", "Item", "Qtd", "Origem -> Destino"]]
            for m in movs:
                table_data.append([
                    m["created_at"].strftime("%d/%m/%y"),
                    m["tipo"],
                    ds.get_item_name(m["item_id"])[:20],
                    str(m["quantidade"]),
                    f"{ds.get_location_name(m['origem_id'])} > {ds.get_location_name(m['destino_id'])}"
                ])
            
            t = Table(table_data, colWidths=[60, 80, 120, 40, 180])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(t)
            
            doc.build(elements)
            shutil.copy2(tmp_path, dest_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def export_excel_click(e):
        nonlocal export_type
        export_type = "EXCEL"
        file_picker.save_file(
            dialog_title="Salvar Relatório Excel",
            file_name="relatorio_movimentacoes.xlsx",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx"]
        )

    def export_pdf_click(e):
        nonlocal export_type
        export_type = "PDF"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        file_picker.save_file(
            dialog_title="Salvar Relatório PDF",
            file_name=f"Relatorio_Inventario_{timestamp}.pdf",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pdf"]
        )

    def select_start_date(e):
        date_picker_start.open = True
        page.update()

    def select_end_date(e):
        date_picker_end.open = True
        page.update()

    start_date_btn = ft.OutlinedButton("Data Inicial", icon=ft.Icons.CALENDAR_MONTH, on_click=select_start_date)
    end_date_btn = ft.OutlinedButton("Data Final", icon=ft.Icons.CALENDAR_MONTH, on_click=select_end_date)

    # --- Selectors ---
    apt_dropdown = ft.Dropdown(
        label="Apartamento",
        options=[ft.dropdown.Option("0", "Todos")] + [ft.dropdown.Option(str(l["id"]), l["nome"]) for l in ds.locations if l["tipo"] == "APARTAMENTO"],
        width=200,
        value="0",
        on_change=lambda _: build_report(None)
    )

    item_dropdown = ft.Dropdown(
        label="Item",
        options=[ft.dropdown.Option("0", "Todos")] + [ft.dropdown.Option(str(i["id"]), i["nome"]) for i in ds.items],
        width=200,
        value="0",
        on_change=lambda _: build_report(None)
    )

    type_dropdown = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option("Todos"),
            ft.dropdown.Option("Compra"),
            ft.dropdown.Option("Transferência"),
            ft.dropdown.Option("Retorno"),
            ft.dropdown.Option("Perda"),
            ft.dropdown.Option("Ajuste"),
        ],
        width=150,
        value="Todos",
        on_change=lambda _: build_report(None)
    )

    # --- Logic Functions ---

    # --- Logic Functions ---

    def get_common_filters():
        filters = {}
        if date_start:
            filters["date_start"] = date_start
        if date_end:
            filters["date_end"] = date_end.replace(hour=23, minute=59, second=59)
        
        if apt_dropdown.value != "0":
            filters["apt_id"] = apt_dropdown.value
        
        if item_dropdown.value != "0":
            filters["item_id"] = item_dropdown.value
        
        if type_dropdown.value != "Todos":
            filters["tipo"] = type_dropdown.value
        return filters

    def generate_inventory_report(apt_id):
        apt_id = int(apt_id)
        rows = []
        
        estoque = ds.get_apartment_stock(apt_id)
        
        for item in estoque:
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(item["nome"])),
                    ft.DataCell(ft.Text(item["categoria"] or "Geral")),
                    ft.DataCell(ft.Text(str(item["saldo"]), weight=ft.FontWeight.BOLD))
                ])
            )
        return rows

    def generate_loss_report(filters):
        # We need all loss data for the chart/table, not just paginated
        # Force type=Perda for this specific report if not already filtered
        loss_filters = filters.copy()
        loss_filters["tipo"] = "Perda"
        
        # Fetch all losses for calculation (assuming volume isn't massive, or limit to reasonable max)
        all_losses = ds.get_movements(limit=1000, filters=loss_filters)
        
        loss_data = {}
        for m in all_losses:
            item_id = m["item_id"]
            if item_id not in loss_data: loss_data[item_id] = {"qtde": 0, "ocorrencias": 0}
            loss_data[item_id]["qtde"] += m["quantidade"]
            loss_data[item_id]["ocorrencias"] += 1
        
        sorted_losses = sorted(loss_data.items(), key=lambda x: x[1]["qtde"], reverse=True)
        rows = []
        for item_id, data in sorted_losses:
            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(ds.get_item_name(item_id))),
                    ft.DataCell(ft.Text(str(data["qtde"]), color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(str(data["ocorrencias"])))
                ])
            )
        return rows, loss_data

    def generate_summary_data(filters):
        data_chunk = ds.get_movements(limit=1000, filters=filters)
        
        # --- CORREÇÃO: Inicialize as variáveis ANTES dos loops ---
        total_movs = len(data_chunk)
        total_perda = 0
        most_mov_item_id = None
        most_lost_item_id = None
        top_apt_id = None
        item_counts = {}
        item_losses = {}
        apt_counts = {}

        if data_chunk:
            for m in data_chunk:
                # Contagem de movimentações por item
                item_counts[m["item_id"]] = item_counts.get(m["item_id"], 0) + 1
                
                # Contagem de perdas
                if m["tipo"] == "Perda":
                    item_losses[m["item_id"]] = item_losses.get(m["item_id"], 0) + m["quantidade"]
                    total_perda += m["quantidade"]
                
                # Contagem de rotatividade por apartamento
                for loc_id in [m["origem_id"], m["destino_id"]]:
                    if loc_id:
                        # Verifica se a localização é um apartamento (opcional se ds.locations for acessível)
                        apt_counts[loc_id] = apt_counts.get(loc_id, 0) + 1

            # --- Cálculos de Máximos (Só se houver dados) ---
            if item_counts:
                most_mov_item_id = max(item_counts, key=item_counts.get)
            if item_losses:
                most_lost_item_id = max(item_losses, key=item_losses.get)
            if apt_counts:
                top_apt_id = max(apt_counts, key=apt_counts.get)

        return {
            "total_movs": total_movs,
            "total_perda": total_perda,
            "most_mov_item": ds.get_item_name(most_mov_item_id),
            "most_mov_item_id": most_mov_item_id,
            "most_lost_item": ds.get_item_name(most_lost_item_id),
            "top_apt": ds.get_location_name(top_apt_id),
            "item_counts": item_counts,
            "item_losses": item_losses,
            "raw_data": data_chunk 
        }

    def generate_summary_ui(summary_data):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        bg_blue = ft.Colors.BLUE_900 if is_dark else ft.Colors.BLUE_50
        bg_red = ft.Colors.RED_900 if is_dark else ft.Colors.RED_50
        bg_grey = "#1E1E1E" if is_dark else ft.Colors.GREY_50
        txt_blue = ft.Colors.BLUE_100 if is_dark else ft.Colors.BLUE_900
        txt_red = ft.Colors.RED_100 if is_dark else ft.Colors.RED_900

        return ft.Row([
            ft.Container(
                content=ft.Column([ft.Text("Total Movs (Aprox)", size=14, color=txt_blue), ft.Text(str(summary_data['total_movs']) + ("+" if summary_data['total_movs'] == 1000 else ""), size=24, weight="bold", color=txt_blue)]),
                padding=15, border_radius=10, bgcolor=bg_blue, expand=True
            ),
            ft.Container(
                content=ft.Column([ft.Text("Total Perdas", size=14, color=txt_red), ft.Text(str(summary_data['total_perda']), size=24, weight="bold", color=txt_red)]),
                padding=15, border_radius=10, bgcolor=bg_red, expand=True
            ),
            ft.Container(
                content=ft.Column([ft.Text("Mais Movimentado", size=14), ft.Text(summary_data['most_mov_item'] if summary_data['most_mov_item'] else "-", size=16, weight="bold")]),
                padding=15, border_radius=10, bgcolor=bg_grey, expand=True
            ),
        ], spacing=10)
    
    # --- Pagination State for Reports ---
    report_offset = 0
    REPORT_LIMIT = 10
    history_list_view = ft.ListView(spacing=5, expand=False, height=500) # Fixed height for scroll inside report
    load_more_history_btn = ft.ElevatedButton("Carregar Mais Histórico", visible=False)

    # --- UI Helpers for Cards ---
    def build_movement_card(m):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        type_cfg = {
            "Compra": {"color": ft.Colors.GREEN_700, "icon": ft.Icons.ADD_SHOPPING_CART},
            "Transferência": {"color": ft.Colors.BLUE_700, "icon": ft.Icons.SWAP_HORIZ},
            "Retorno": {"color": ft.Colors.ORANGE_700, "icon": ft.Icons.KEYBOARD_RETURN},
            "Perda": {"color": ft.Colors.RED_700, "icon": ft.Icons.REPORT_PROBLEM},
            "Ajuste": {"color": ft.Colors.PURPLE_700, "icon": ft.Icons.EDIT_ATTRIBUTES},
        }
        cfg = type_cfg.get(m["tipo"], {"color": ft.Colors.GREY_700, "icon": ft.Icons.INFO})

        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text(m["created_at"].strftime("%d/%m/%Y %H:%M"), size=10, color=ft.Colors.GREY_500),
                        ft.Row([ft.Icon(cfg["icon"], color=cfg["color"], size=16), ft.Text(m["tipo"].upper(), size=10, weight="bold", color=cfg["color"])], spacing=5),
                    ], spacing=2), width=130
                ),
                ft.Text(ds.get_item_name(m["item_id"]), size=14, weight="bold", expand=True),
                ft.Row([
                    ft.Text(ds.get_location_name(m["origem_id"]), size=12, color=ft.Colors.GREY_400 if not m["origem_id"] else None),
                    ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400),
                    ft.Text(ds.get_location_name(m["destino_id"]), size=12, color=ft.Colors.GREY_400 if not m["destino_id"] else None),
                ], spacing=10, expand=True),
                ft.Container(content=ft.Text(str(m["quantidade"]), size=14, weight="bold"), width=60, alignment=ft.alignment.center),
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            border_radius=8, bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
        )

    def build_loss_card(item_id, data):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        return ft.Container(
            content=ft.Row([
                ft.Text(ds.get_item_name(item_id), size=14, weight="bold", expand=True),
                ft.Container(content=ft.Text(str(data["qtde"]), size=16, weight="bold", color=ft.Colors.RED_400), width=100, alignment=ft.alignment.center),
                ft.Container(content=ft.Text(str(data["ocorrencias"]), size=14, color=ft.Colors.GREY_500), width=100, alignment=ft.alignment.center),
            ]),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            border_radius=8, bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
        )

    def build_inventory_card(item_name, category, balance):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        return ft.Container(
            content=ft.Row([
                ft.Text(item_name, size=15, weight="bold", expand=True),
                ft.Text(category, size=13, weight="w500", color=ft.Colors.GREY_400, expand=True),
                ft.Container(
                    content=ft.Text(str(balance), size=16, weight="bold"),
                    width=80,
                    alignment=ft.alignment.center
                ),
                ft.Container(width=80) 
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            border_radius=8,
            bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
        )

    def load_more_history(filters):
        nonlocal report_offset
        new_items = ds.get_movements(limit=REPORT_LIMIT, offset=report_offset, filters=filters)
        
        if new_items:
            for m in new_items:
                history_list_view.controls.append(build_movement_card(m))
            report_offset += REPORT_LIMIT
            load_more_history_btn.visible = True
            load_more_history_btn.on_click = lambda e: load_more_history(filters)
        else:
            load_more_history_btn.visible = False
        page.update()

    def build_report(e):
        nonlocal report_offset
        report_container.controls = []
        filters = get_common_filters()
        summary_data = generate_summary_data(filters)
        
        # 1️⃣ Resumo Sempre Visível
        report_container.controls.append(ft.Text("Resumo do Período", size=18, weight="bold"))
        report_container.controls.append(generate_summary_ui(summary_data))
        report_container.controls.append(ft.Divider(height=30))

        # 3️⃣ Relatório de Perdas (Card Based)
        if type_dropdown.value == "Todos" or type_dropdown.value == "Perda":
            rows, loss_data = generate_loss_report(filters)
            
            if loss_data:
                report_container.controls.append(ft.Text("Análise de Perdas", size=18, weight="bold"))
                report_container.controls.append(ft.Container(content=ft.Row([
                    ft.Text("ITEM", size=11, weight="bold", color=ft.Colors.GREY_500, expand=True),
                    ft.Text("TOTAL PERDIDO", size=11, weight="bold", color=ft.Colors.GREY_500, width=100, text_align=ft.TextAlign.CENTER),
                    ft.Text("OCORRÊNCIAS", size=11, weight="bold", color=ft.Colors.GREY_500, width=100, text_align=ft.TextAlign.CENTER),
                ]), padding=ft.padding.symmetric(horizontal=15)))
                
                sorted_losses = sorted(loss_data.items(), key=lambda x: x[1]["qtde"], reverse=True)
                for item_id, data in sorted_losses:
                    report_container.controls.append(build_loss_card(item_id, data))
                report_container.controls.append(ft.Divider(height=30))

        # 4️⃣ Histórico Detalhado (Paginated)
        report_container.controls.append(ft.Text("Histórico Detalhado", size=18, weight="bold"))
        
        report_container.controls.append(ft.Container(content=ft.Row([
            ft.Text("DATA / TIPO", size=11, weight="bold", color=ft.Colors.GREY_500, width=130),
            ft.Text("ITEM", size=11, weight="bold", color=ft.Colors.GREY_500, expand=True),
            ft.Text("ORIGEM ➜ DESTINO", size=11, weight="bold", color=ft.Colors.GREY_500, expand=True),
            ft.Text("QTDE", size=11, weight="bold", color=ft.Colors.GREY_500, width=60, text_align=ft.TextAlign.CENTER),
        ]), padding=ft.padding.symmetric(horizontal=15)))
        
        # Reset pagination for new report build
        history_list_view.controls.clear()
        report_offset = 0
        load_more_history(filters) # Trigger initial load
        
        report_container.controls.append(history_list_view)
        report_container.controls.append(ft.Row([load_more_history_btn], alignment=ft.MainAxisAlignment.CENTER))
        
        page.update()

    is_dark = page.theme_mode == ft.ThemeMode.DARK
    
    # --- Layout ---
    filter_section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Filtros Inteligentes", weight="bold", size=16),
                ft.ElevatedButton("Atualizar Relatório", icon=ft.Icons.REFRESH, on_click=build_report, bgcolor=ft.Colors.BLUE_700, color="white"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                apt_dropdown,
                item_dropdown,
                type_dropdown,
                start_date_btn,
                end_date_btn,
            ], spacing=10, wrap=True, vertical_alignment=ft.CrossAxisAlignment.END),
        ], spacing=15),
        padding=20,
        bgcolor="#1E1E1E" if is_dark else ft.Colors.GREY_50,
        border_radius=10,
        border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300)
    )

    build_report(None)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Relatórios", size=30, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton("Exportar Excel", icon=ft.Icons.FILE_DOWNLOAD, on_click=export_excel_click),
                    ft.ElevatedButton("Exportar PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=export_pdf_click),
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Column([
                filter_section,
                ft.Divider(height=10),
                report_container
            ], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True),
        padding=20,
        expand=True
    )
