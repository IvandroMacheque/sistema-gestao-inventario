import flet as ft
import data_service as ds
import pandas as pd
import utils
import time
import os
import re

def ApartmentsView(page: ft.Page):
    # --- State ---
    current_filter = "Todos"

    item_selecionado = [] # Usamos lista para evitar erro de nonlocal
    apto_origem = []
    
    txt_nome_item = ft.Text("", weight="bold", size=16)
    campo_qtd = ft.TextField(label="Quantidade", width=150)
    drop_destino = ft.Dropdown(label="Destino", width=250)
    campo_obs = ft.TextField(label="Observação (Opcional)")

    # Função para salvar a transferência
    def salvar_transferencia(e):
        try:
            # 1. Validação básica            campo_qtd.error_text = None
            drop_destino.error_text = None
            if not campo_qtd.value:
                campo_qtd.error_text = "Campo obrigatório"
                page.update()
                return

            try:
                qty = float(campo_qtd.value)
            except ValueError:
                campo_qtd.error_text = "Número inválido"
                page.update()
                return
            
            if not drop_destino.value:
                drop_destino.error_text = "Campo obrigatório"
                page.update()
                return

            # 2. Registra no banco de dados
            ds.add_movement(
                item_id=item_selecionado[0]["id"],
                origem_id=apto_origem[0]["id"],
                destino_id=int(drop_destino.value),
                quantidade=float(campo_qtd.value),
                tipo="Transferência",
                observacao=campo_obs.value
            )

            # 3. Sucesso!
            modal_transferir.open = False
            open_inventory(apto_origem[0]) # Recarrega a lista lá no fundo
            page.snack_bar = ft.SnackBar(ft.Text("Transferência concluída!"), bgcolor="green")
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(f"Erro: {ex}")

    # O "Caixote" (Modal)
    modal_transferir = ft.AlertDialog(
        title=ft.Text("Transferir Item"),
        content=ft.Column([txt_nome_item, campo_qtd, drop_destino, campo_obs], tight=True),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(modal_transferir, "open", False) or page.update()),
            ft.ElevatedButton("Confirmar", on_click=salvar_transferencia)
        ]
    )
    page.overlay.append(modal_transferir)

    def abrir_transferencia(item, apt):
        item_selecionado.clear()
        item_selecionado.append(item)
        apto_origem.clear()
        apto_origem.append(apt)

        txt_nome_item.value = f"Item: {item['nome']}"
        campo_qtd.value = ""
        campo_qtd.error_text = None 
        
        drop_destino.value = None 
        drop_destino.error_text = None 
        
        campo_obs.value = ""
        
        # Carrega os apartamentos destinos
        drop_destino.options = [
            ft.dropdown.Option(str(loc["id"]), loc["nome"]) 
            for loc in ds.locations if loc["id"] != apt["id"] and loc["ativo"]
        ]
        
        modal_transferir.open = True
        page.update()
    

    # --- UI Refs ---
    grid_container = ft.Container()
    
    search_field = ft.TextField(
        label="Pesquisar apartamentos...",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda _: render_list(),
        expand=True
    )
    
    # --- Modals ---
    # 1. New Apartment Modal
    new_apt_name = ft.TextField(label="Nome do Apartamento")
    new_apt_status = ft.Dropdown(
        label="Status Inicial",
        options=[ft.dropdown.Option("DISPONIVEL"), ft.dropdown.Option("OCUPADO")],
        value="DISPONIVEL"
    )

    def save_new_apartment(e):
        e.control.disabled = True
        page.update()
        
        new_apt_name.error_text = None
        if not new_apt_name.value:
            new_apt_name.error_text = "Campo obrigatório"
            e.control.disabled = False
            page.update()
            return
        ds.add_apartment(new_apt_name.value, new_apt_status.value)
        new_apt_dialog.open = False
        new_apt_name.value = ""
        render_list()
        page.snack_bar = ft.SnackBar(ft.Text("Apartamento cadastrado com sucesso!"))
        page.snack_bar.open = True
        page.update()

    new_apt_dialog = ft.AlertDialog(
        title=ft.Text("Novo Apartamento"),
        content=ft.Container(
            content=ft.Column([new_apt_name, new_apt_status], tight=True),
            width=600
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(new_apt_dialog, "open", False) or page.update()),
            ft.ElevatedButton("Salvar", on_click=save_new_apartment, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]
    )
    page.overlay.append(new_apt_dialog)

    # 2. Inventory Modal
    inventory_table = ft.Column()
    current_apt_for_export = None
    
    # Gera o arquivo Excel do inventário usando temp file + cópia
    def save_inventory_excel(apt, dest_path):
        import tempfile
        import shutil
        
        data = []
        todos_itens = ds.get_items(limit=9999)
        
        for item in todos_itens:
            balance = ds.get_balance(item["id"], apt["id"])
            if balance > 0:
                data.append({
                    "Item": item["nome"],
                    "Categoria": item.get("categoria") or "Geral",
                    "Quantidade": balance
                })
        
        if not data:
            data.append({"Item": "Nenhum item encontrado", "Categoria": "-", "Quantidade": 0})

        df = pd.DataFrame(data)
        
        # Gera num temp file primeiro, depois copia pro destino
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pd.ExcelWriter(tmp_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            shutil.copy2(tmp_path, dest_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # Estado para guardar o apartamento atual do export
    apt_para_exportar = [None]

    # Callback do FilePicker quando o usuário escolhe onde salvar
    def on_export_file_result(e: ft.FilePickerResultEvent):
        if e.path:
            try:
                # Garante que o caminho tem a extensão correta
                filepath = e.path
                if not filepath.lower().endswith(".xlsx"):
                    filepath += ".xlsx"
                
                page.snack_bar = ft.SnackBar(ft.Text("Gerando relatório..."), bgcolor=ft.Colors.BLUE_700)
                page.snack_bar.open = True
                page.update()
                
                save_inventory_excel(apt_para_exportar[0], filepath)
                
                page.snack_bar = ft.SnackBar(ft.Text("Arquivo salvo com sucesso!"), bgcolor=ft.Colors.GREEN_700)
            except Exception as ex:
                print(f"[EXPORT ERRO] {ex}")
                import traceback
                traceback.print_exc()
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {str(ex)}"), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()

    export_file_picker = ft.FilePicker(on_result=on_export_file_result)
    page.overlay.append(export_file_picker)

    def open_inventory(apt):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        
        def build_inventory_card(item, balance):
            return ft.Container(
                content=ft.Row([
                    # Nome do Item
                    ft.Text(item["nome"], size=14, weight="bold", expand=True),
                    
                    # Categoria
                    ft.Text(item["categoria"] or "Geral", size=12, color=ft.Colors.GREY_500, width=120),
                    
                    # Quantidade
                    ft.Container(
                        content=ft.Text(str(balance), size=14, weight="bold"), 
                        width=60, 
                        alignment=ft.alignment.center
                    ),
                    
                    ft.IconButton(
                        icon=ft.Icons.SEND_ROUNDED, 
                        icon_size=20, 
                        icon_color=ft.Colors.BLUE_400,
                        tooltip="Transferir este item",
                        on_click=lambda _: abrir_transferencia(item, apt)
                    ),
                    # ------------------------------------
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), # Garante alinhamento bonito
                padding=ft.padding.symmetric(horizontal=5, vertical=5),
                border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_200)) # Opcional: linha fina entre itens
            )

        cards = []
        itens_com_saldo = ds.get_apartment_stock(apt["id"])
        
        ultima_categoria = None

        for row in itens_com_saldo:
            # row já vem com: {'id': 1, 'nome': 'Cama', 'categoria': 'Móveis', 'saldo': 5}
            
            categoria_atual = row["categoria"] or "Geral"

            if categoria_atual != ultima_categoria:
                if ultima_categoria is not None:
                    cards.append(ft.Container(height=10)) 
                
                cards.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.LABEL_IMPORTANT, color=ft.Colors.BLUE_700, size=20),
                            ft.Text(categoria_atual.upper(), size=14, weight="bold", color=ft.Colors.BLUE_700),
                        ]),
                        padding=ft.padding.only(top=10, bottom=5),
                    )
                )
                cards.append(ft.Divider(height=1, color=ft.Colors.BLUE_200))
                ultima_categoria = categoria_atual

            # Passamos os dados direto para o card
            # Nota: Adaptamos o objeto 'item' para ter as chaves que o build_card espera
            item_fake = {"id": row["id"], "nome": row["nome"], "categoria": row["categoria"]}
            cards.append(build_inventory_card(item_fake, row["saldo"]))

        
        inventory_table.controls = [
            ft.Container(content=ft.Row([
                ft.Text("ITEM", size=10, weight="bold", color=ft.Colors.GREY_500, expand=True),
                ft.Text("CATEGORIA", size=10, weight="bold", color=ft.Colors.GREY_500, width=120),
                ft.Text("QTDE", size=10, weight="bold", color=ft.Colors.GREY_500, width=60, text_align=ft.TextAlign.CENTER),
                ft.Text("SEND", size=10, weight="bold", color=ft.Colors.GREY_500, width=40, text_align=ft.TextAlign.CENTER),
            ]), padding=ft.padding.symmetric(horizontal=12)) if cards else ft.Container(),
            ft.Column(cards, spacing=5, scroll=ft.ScrollMode.AUTO, height=400) if cards else ft.Text("Nenhum item neste apartamento.", italic=True)
        ]
        
        inventory_dialog.actions = [
            ft.TextButton("Fechar", on_click=lambda _: setattr(inventory_dialog, "open", False) or page.update()),
            ft.ElevatedButton(
                "Transferir Item", 
                on_click=lambda _: (
                    setattr(inventory_dialog, "open", False),
                    page.change_view(1, initial_data={
                        "origem_id": apt["id"],
                        "tipo": "Transferência"
                    })
                ),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE
            ),
            ft.ElevatedButton(
                "Exportar Relatório", 
                on_click=lambda _: export_inventory_click(apt),
                icon=ft.Icons.FILE_DOWNLOAD
            ),
        ]
        
        inventory_dialog.title = ft.Text(f"Inventário - {apt['nome']}")
        inventory_dialog.open = True
        page.update()

    def export_inventory_click(apt):
        apt_para_exportar[0] = apt
        nome_arquivo = f"inventario_{apt['nome'].replace(' ', '_').lower()}.xlsx"
        export_file_picker.save_file(
            dialog_title="Salvar Inventário como Excel",
            file_name=nome_arquivo,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["xlsx"]
        )

    inventory_dialog = ft.AlertDialog(
        title=ft.Text("Inventário"),
        content=ft.Container(content=inventory_table, width=600),
        actions=[] # Populated dynamically in open_inventory
    )
    page.overlay.append(inventory_dialog)

    # --- Actions ---
    def toggle_status(apt):
        ds.toggle_apartment_status(apt["id"])
        render_list()
        page.update()

    def toggle_active(apt):
        ds.toggle_apartment_active(apt["id"])
        render_list()
        page.update()

    def set_filter(e):
        nonlocal current_filter
        current_filter = e.control.text
        render_list()
        page.update()

    # --- Render ---
    def render_list():
        search_query = search_field.value.lower() if search_field.value else ""
        cards = []
        filtered_locations = [l for l in ds.locations if l["tipo"] == "APARTAMENTO"]
        
        # Filter by search
        if search_query:
            filtered_locations = [
                l for l in filtered_locations 
                if search_query in l["nome"].lower()
            ]

        # Ordenar por nome
        def chave_ordenacao(item):
            nome = item["nome"]
            return [int(text) if text.isdigit() else text.lower() 
                    for text in re.split('([0-9]+)', nome)]

        filtered_locations.sort(key=chave_ordenacao)

        if current_filter == "Ocupados":
            filtered_locations = [l for l in filtered_locations if l["status_ocupacao"] == "OCUPADO" and l["ativo"]]
        elif current_filter == "Disponíveis":
            filtered_locations = [l for l in filtered_locations if l["status_ocupacao"] == "DISPONIVEL" and l["ativo"]]
        elif current_filter == "Inativos":
            filtered_locations = [l for l in filtered_locations if not l["ativo"]]
        else: # Todos
            # On 'Todos', we might want to show active ones primarily or everything
            pass

        for apt in filtered_locations:
            status_color = ft.Colors.GREEN_700 if apt["status_ocupacao"] == "DISPONIVEL" else ft.Colors.ORANGE_700
            if not apt["ativo"]: status_color = ft.Colors.RED_700
            
            cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(apt["nome"], size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(
                                    "INATIVO" if not apt["ativo"] else apt["status_ocupacao"], 
                                    size=12, color=ft.Colors.WHITE
                                ),
                                bgcolor=status_color,
                                padding=ft.padding.symmetric(horizontal=10, vertical=2),
                                border_radius=10
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        ft.Row([
                            ft.TextButton("Ver Inventário", icon=ft.Icons.INVENTORY, on_click=lambda e, a=apt: open_inventory(a)),
                            ft.IconButton(
                                ft.Icons.SWAP_HORIZ, 
                                tooltip="Alterar Status", 
                                on_click=lambda e, a=apt: toggle_status(a),
                                disabled=not apt["ativo"]
                            ),
                            ft.IconButton(
                                ft.Icons.PLAY_ARROW if not apt["ativo"] else ft.Icons.DELETE_FOREVER, 
                                tooltip="Ativar" if not apt["ativo"] else "Desativar", 
                                icon_color=ft.Colors.GREEN_400 if not apt["ativo"] else ft.Colors.RED_300,
                                on_click=lambda e, a=apt: toggle_active(a),
                            ),
                        ], alignment=ft.MainAxisAlignment.END)
                    ]),
                    padding=15,
                    border=ft.border.all(1, ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_300),
                    border_radius=10,
                    bgcolor="#1E1E1E" if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.WHITE,
                    width=350,
                )
            )
        
        # Prepare the new controls
        new_content = ft.ResponsiveRow(
            [ft.Column([c], col={"sm": 12, "md": 4, "lg": 3}) for c in cards],
            spacing=20,
            run_spacing=20
        )
        
        # Update the grid container with animation
        grid_container.content = new_content
        page.update()

    # --- Filters ---
    def on_filter_change(e):
        nonlocal current_filter
        current_filter = e.control.text
        # Visual update for buttons
        for btn in filter_row.controls:
            btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700 if btn.text == current_filter else ft.Colors.TRANSPARENT,
                color=ft.Colors.WHITE if btn.text == current_filter else (ft.Colors.BLUE_200 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_700),
            )
        render_list()
        page.update()

    filter_options = ["Todos", "Ocupados", "Disponíveis", "Inativos"]
    filter_row = ft.Row(
        [
            ft.TextButton(
                text=opt, 
                on_click=on_filter_change,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_700 if opt == "Todos" else ft.Colors.TRANSPARENT,
                    color=ft.Colors.WHITE if opt == "Todos" else (ft.Colors.BLUE_200 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_700),
                    padding=15
                )
            ) for opt in filter_options
        ],
        spacing=0
    )

    render_list()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Apartamentos", size=30, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton(
                    "+ Novo Apartamento", 
                    on_click=lambda _: (
                        setattr(new_apt_dialog, "open", True),
                        setattr(new_apt_dialog.actions[1], "disabled", False),
                        page.update()
                    ),
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            filter_row,
            ft.Divider(),
            ft.Row([search_field]),
            ft.Column([grid_container], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True),
        padding=20,
        expand=True
    )
