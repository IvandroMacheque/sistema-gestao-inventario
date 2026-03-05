import flet as ft
import data_service as ds
from datetime import datetime

def ItemsView(page: ft.Page):
    # --- State ---
    editing_item_id = None

    # --- UI Refs ---
    grid_container = ft.Container()

    # --- State para Paginação ---
    ITEMS_LIMIT = 12 # 12 é bom porque divide por 2, 3 e 4 colunas
    current_offset = 0
    
    # Referência para a grade de cards
    grid_row = ft.ResponsiveRow(spacing=20, run_spacing=20)
    btn_load_more = ft.ElevatedButton("Carregar Mais Itens", on_click=lambda _: render_view(load_more=True), visible=False)
    
    total_items = ds.item_count()
    total_critical_items = ds.get_total_critical_count()
    total_items_text = ft.Text(total_items, size=30, weight=ft.FontWeight.BOLD)
    below_min_text = ft.Text(total_critical_items, size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)
    
    search_field = ft.TextField(
        label="Pesquisar itens...",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda _: render_view(),
        expand=True
    )

    # Dropdown para filtrar por categoria
    filter_category = ft.Dropdown(
        label="Filtrar por Categoria",
        width=200,
        options=[ft.dropdown.Option("Todas")], # Começa com a opção 'Todas'
        value="Todas",
        on_change=lambda _: render_view() # Atualiza a lista quando mudar
    )

    # Função para carregar as categorias no dropdown
    def load_filter_options():
        categories = ds.get_categories()
        # Mantém o "Todas" e adiciona as outras do banco
        filter_category.options = [ft.dropdown.Option("Todas")] + [
            ft.dropdown.Option(c["nome"]) for c in categories
        ]
        page.update()

    # Dropdown para filtrar por status
    filter_status = ft.Dropdown(
        label="Filtrar por Status",
        width=200,
        options=[
            ft.dropdown.Option("Todos"),
            ft.dropdown.Option("Abaixo do Mínimo"), # Crítico
            ft.dropdown.Option("Acima do Mínimo"),  # OK
        ],
        value="Todos",
        on_change=lambda _: render_view() # Atualiza a lista quando mudar
    )
    
    # --- Form Controls ---
    name_field = ft.TextField(label="Nome do Item")
    category_dropdown = ft.Dropdown(
        label="Categoria",
        options=[],
        expand=True
    )
    min_qty_field = ft.TextField(label="Quantidade Mínima", keyboard_type=ft.KeyboardType.NUMBER)
    
    # --- Category Management ---
    new_cat_name = ft.TextField(label="Nome da Categoria", expand=True)
    cat_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=500)

    def load_categories():
        categories = ds.get_categories()
        
        # 1. Atualiza o dropdown de CADASTRO (usa ID no valor)
        category_dropdown.options = [ft.dropdown.Option(str(c["id"]), c["nome"]) for c in categories]
        
        # 2. Atualiza o dropdown de FILTRO (usa NOME no valor)
        # Verifique se o nome da variável é filter_category
        filter_category.options = [ft.dropdown.Option("Todas")] + [
            ft.dropdown.Option(c["nome"]) for c in categories
        ]
        
        # 3. Atualiza a lista de gerenciamento (modal)
        cat_list_column.controls = [
            ft.ListTile(
                title=ft.Text(c["nome"]),
                trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda e, cid=c["id"]: delete_category(cid))
            ) for c in categories
        ]
        page.update()

    def add_category(e):
        e.control.disabled = True
        page.update()
        
        new_cat_name.error_text = None
        if not new_cat_name.value:
            new_cat_name.error_text = "Campo obrigatório"
            e.control.disabled = False
            page.update()
            return
        ds.add_category(new_cat_name.value)
        new_cat_name.value = ""
        load_categories()
        page.snack_bar = ft.SnackBar(ft.Text("Categoria adicionada!"))
        page.snack_bar.open = True
        page.update()

    def delete_category(id):
        try:
            ds.delete_category(id)
            load_categories()
            page.snack_bar = ft.SnackBar(ft.Text("Categoria removida!"))
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao remover: {str(ex)}"), bgcolor=ft.Colors.RED_700)
        page.snack_bar.open = True
        page.update()

    cat_mgmt_dialog = ft.AlertDialog(
        title=ft.Text("Gerenciar Categorias"),
        content=ft.Container(
            content=ft.Column([
                ft.Row([
                    new_cat_name, 
                    ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=add_category, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Text("Lista de Categorias", size=14, weight="bold"),
                cat_list_column
            ], tight=True),
            width=600
        ),
        actions=[ft.TextButton("Fechar", on_click=lambda _: setattr(cat_mgmt_dialog, "open", False) or page.update())]
    )
    page.overlay.append(cat_mgmt_dialog)

    # --- Actions ---
    def save_item(e):
        nonlocal editing_item_id
        
        # Disable button to prevent double-click
        e.control.disabled = True
        page.update()
        
        if not name_field.value or not min_qty_field.value or not category_dropdown.value:
            if not name_field.value: name_field.error_text = "Campo obrigatório"
            if not min_qty_field.value: min_qty_field.error_text = "Campo obrigatório"
            if not category_dropdown.value: category_dropdown.error_text = "Selecione uma categoria"
            e.control.disabled = False # Re-enable on error
            page.update()
            return
        
        try:
            min_qty = float(min_qty_field.value)
        except ValueError:
            min_qty_field.error_text = "coloque um numero valido"
            e.control.disabled = False # Re-enable on error
            page.update()
            return

        if editing_item_id:
            # Check if name exists in other items
            if any(i["nome"].lower() == name_field.value.lower() and i["id"] != editing_item_id for i in ds.items):
                name_field.error_text = "Já existe um item com este nome"
                e.control.disabled = False # Re-enable on error
                page.update()
                return
            ds.update_item(editing_item_id, name_field.value, category_dropdown.value, min_qty)
            page.snack_bar = ft.SnackBar(ft.Text("Item atualizado com sucesso!"))
        else:
            # Check if name exists
            if any(i["nome"].lower() == name_field.value.lower() for i in ds.items):
                name_field.error_text = "Já existe um item com este nome"
                e.control.disabled = False # Re-enable on error
                page.update()
                return
            ds.add_item(name_field.value, category_dropdown.value, min_qty)
            page.snack_bar = ft.SnackBar(ft.Text("Item cadastrado com sucesso!"))
        
        page.snack_bar.open = True
        item_dialog.open = False
        render_view()
        page.update()

    def open_item_modal(item=None):
        nonlocal editing_item_id
        editing_item_id = item["id"] if item else None
        
        load_categories() # Ensure options are fresh
        
        # Clear errors and re-enable save button
        name_field.error_text = None
        min_qty_field.error_text = None
        item_dialog.actions[1].disabled = False
        
        name_field.value = item["nome"] if item else ""
        category_dropdown.value = str(item["category_id"]) if item and item.get("category_id") else None
        min_qty_field.value = str(item["quantidade_minima"]) if item else ""
        
        item_dialog.title = ft.Text("Editar Item" if item else "Novo Item")
        item_dialog.open = True
        page.update()

    def toggle_active(item):
        ds.toggle_item_active(item["id"])
        render_view()
        page.update()

    # --- Movement Modal Logic ---
    mov_item_id = None
    
    mov_type = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option("Compra"),
            ft.dropdown.Option("Transferência"),
            ft.dropdown.Option("Retorno"),
            ft.dropdown.Option("Perda"),
            ft.dropdown.Option("Ajuste"),
        ],
        value="Transferência",
        on_change=lambda e: update_mov_form_logic(),
        expand=True
    )
    mov_qty = ft.TextField(label="Quantidade", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    mov_origin = ft.Dropdown(label="Origem", options=[], expand=True, on_change=lambda e: update_mov_balance())
    mov_dest = ft.Dropdown(label="Destino", options=[], expand=True)
    mov_obs = ft.TextField(label="Observação (Opcional)", expand=True)
    mov_balance_text = ft.Text("Saldo disponível na origem: -", color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD)

    def load_locations_for_modal():
        locs = ds.locations
        opts = [ft.dropdown.Option(str(l["id"]), l["nome"]) for l in locs if l["ativo"]]
        mov_origin.options = opts
        mov_dest.options = opts

    def update_mov_balance():
        if not mov_item_id or not mov_origin.value:
            mov_balance_text.value = "Saldo disponível na origem: -"
        else:
            try:
                orig_id = int(mov_origin.value)
                balance = ds.get_balance(mov_item_id, orig_id)
                mov_balance_text.value = f"Saldo disponível na origem: {balance}"
            except (ValueError, TypeError):
                mov_balance_text.value = "Saldo disponível na origem: -"
        page.update()

    def update_mov_form_logic():
        t = mov_type.value
        load_locations_for_modal()
        
        # Reset visual state
        mov_origin.disabled = False
        mov_dest.disabled = False
        
        if t == "Compra":
            mov_origin.value = ""
            mov_origin.disabled = True
            mov_dest.value = "1" # Default to General
        elif t == "Perda":
            mov_dest.value = ""
            mov_dest.disabled = True
            
        update_mov_balance()
        page.update()
        
    def open_movement_modal(item):
        nonlocal mov_item_id
        mov_item_id = item["id"]
        load_locations_for_modal()
        
        # Reset fields
        mov_type.value = "Transferência" # Default
        mov_qty.value = ""
        mov_qty.error_text = None
        mov_origin.value = "1" # Default to General Inventory
        mov_dest.value = ""
        mov_obs.value = ""
        
        update_mov_form_logic()
        
        movement_dialog.title = ft.Text(f"Movimentar: {item['nome']}")
        movement_dialog.open = True
        page.update()

    def save_movement_from_inventory(e):
        if not mov_qty.value:
            mov_qty.error_text = "Qtd obrigatória"
            page.update()
            return

        try:
            qty = int(mov_qty.value)
            if qty <= 0: raise ValueError
        except ValueError:
            mov_qty.error_text = "Número inválido"
            page.update()
            return

        origem_id = int(mov_origin.value) if mov_origin.value else None
        destino_id = int(mov_dest.value) if mov_dest.value else None

        if not origem_id and not destino_id and mov_type.value == "Transferência":
             page.snack_bar = ft.SnackBar(ft.Text("Para transferência, selecione origem ou destino."), bgcolor=ft.Colors.RED_700)
             page.snack_bar.open = True
             page.update()
             return

        ds.add_movement(
            item_id=mov_item_id,
            origem_id=origem_id,
            destino_id=destino_id,
            quantidade=qty,
            tipo=mov_type.value,
            observacao=mov_obs.value
        )
        
        movement_dialog.open = False
        render_view() # Update balances
        page.snack_bar = ft.SnackBar(ft.Text("Movimentação registrada com sucesso!"), bgcolor=ft.Colors.GREEN_700)
        page.snack_bar.open = True
        page.update()

    movement_dialog = ft.AlertDialog(
        title=ft.Text("Nova Movimentação"),
        content=ft.Container(
            content=ft.Column([
                mov_type,
                # No Item Dropdown needed, as it is fixed
                mov_origin,
                mov_dest,
                mov_qty,
                mov_obs,
                mov_balance_text
            ], tight=True, spacing=15),
            width=500
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(movement_dialog, "open", False) or page.update()),
            ft.ElevatedButton("Salvar", on_click=save_movement_from_inventory, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]
    )
    page.overlay.append(movement_dialog)

    # --- Modals ---
    item_dialog = ft.AlertDialog(
        title=ft.Text("Novo Item"),
        content=ft.Container(
            content=ft.Column([
                name_field, 
                ft.Row([
                    category_dropdown, 
                    ft.IconButton(
                        ft.Icons.SETTINGS, 
                        tooltip="Gerenciar Categorias",
                        on_click=lambda _: (load_categories(), setattr(cat_mgmt_dialog, "open", True), page.update())
                    )
                ], spacing=20),
                min_qty_field
            ], tight=True, spacing=15),
            width=600
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(item_dialog, "open", False) or page.update()),
            ft.ElevatedButton("Salvar", on_click=save_item, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ]
    )
    page.overlay.append(item_dialog)

    def build_item_card(item, balance):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        is_below = balance <= item["quantidade_minima"]
        status_text = "REPOR" if is_below else "OK"
        status_color = ft.Colors.RED_700 if is_below else ft.Colors.GREEN_700
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(item["nome"], size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700 if not is_dark else ft.Colors.BLUE_200, no_wrap=True),
                        ft.Text(ds.get_item_category_name(item), size=12, color=ft.Colors.GREY_600),
                    ], spacing=1, expand=True),
                    ft.Container(
                        content=ft.Text(status_text, size=9, weight="bold", color=ft.Colors.WHITE),
                        bgcolor=status_color,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.Column([
                        ft.Text("Saldo", size=11, color=ft.Colors.GREY_500),
                        ft.Text(str(balance), size=16, weight="bold"),
                    ], spacing=0, expand=True),
                    ft.Column([
                        ft.Text("Mínimo", size=11, color=ft.Colors.GREY_500),
                        ft.Text(str(item["quantidade_minima"]), size=16, weight="w500"),
                    ], spacing=0, expand=True, horizontal_alignment=ft.CrossAxisAlignment.END),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([
                    ft.TextButton("Editar", icon=ft.Icons.EDIT, on_click=lambda e: open_item_modal(item), style=ft.ButtonStyle(padding=0)),
                    ft.IconButton(
                        ft.Icons.SWAP_HORIZ,
                        tooltip="Nova Movimentação",
                        icon_color=ft.Colors.BLUE_400,
                        on_click=lambda e: open_movement_modal(item)
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, 
                        icon_color=ft.Colors.RED_300,
                        icon_size=18,
                        tooltip="Desativar",
                        on_click=lambda e: toggle_active(item)
                    ),
                ], alignment=ft.MainAxisAlignment.END, spacing=0)
            ], spacing=8),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            border_radius=10,
            bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
            shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK)),
        )

    # --- Render Logic ---
    def render_view(load_more=False):
        nonlocal current_offset
        
        if not load_more:
            current_offset = 0
            grid_row.controls.clear()
        
        # Filtros para a query
        filters = {
            "search": search_field.value if search_field.value else None,
            "categoria": filter_category.value,
        }

        limite_busca = ITEMS_LIMIT
        if filter_status.value != "Todos":
            limite_busca = 50

        # Busca apenas o "pedaço" necessário do banco
        batch_items = ds.get_items(limit=limite_busca, offset=current_offset, filters=filters)
        
        # ID do Inventário Geral
        gen_inv_id = 1
        itens_mostrados_nesta_leva = 0
        
        for i in batch_items:
            balance = ds.get_balance(i["id"], gen_inv_id)
            is_below = balance <= i["quantidade_minima"]
            
            # --- LÓGICA DO FILTRO DE STATUS ---
            status_selecionado = filter_status.value
            
            mostrar = True
            if status_selecionado == "Abaixo do Mínimo" and not is_below:
                mostrar = False
            elif status_selecionado == "Acima do Mínimo" and is_below:
                mostrar = False
            
            if mostrar:
                grid_row.controls.append(
                    ft.Column([build_item_card(i, balance)], col={"sm": 12, "md": 4, "lg": 3})
                )
                itens_mostrados_nesta_leva += 1
        
        # Gerencia o botão "Carregar Mais"
        if len(batch_items) == limite_busca:
            current_offset += limite_busca
            btn_load_more.visible = True
        else:
            btn_load_more.visible = False
            
        # Atualiza contadores (opcional: buscar contagem total via query separada se precisar)
        page.update()

    is_dark = page.theme_mode == ft.ThemeMode.DARK
    summary_row = ft.Row([
        ft.Container(
            content=ft.Column([
                ft.Text("Total de Itens", size=16, color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_700),
                total_items_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, 
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300), 
            border_radius=10, 
            bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE, 
            expand=True
        ),
        ft.Container(
            content=ft.Column([
                ft.Text("Abaixo do Mínimo", size=16, color=ft.Colors.GREY_400 if is_dark else ft.Colors.GREY_700),
                below_min_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, 
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300), 
            border_radius=10, 
            bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE, 
            expand=True
        ),
    ], spacing=20)

    render_view()      # Carrega os itens
    load_categories()  # Carrega as categorias nos dropdowns (Importante!)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Inventário", size=30, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Categorias", 
                        icon=ft.Icons.CATEGORY, 
                        on_click=lambda _: (
                            load_categories(), 
                            setattr(cat_mgmt_dialog, "open", True),
                            setattr(cat_mgmt_dialog.content.content.controls[0].controls[1], "disabled", False),
                            page.update()
                        ),
                        style=ft.ButtonStyle(padding=15)
                    ),
                    ft.ElevatedButton(
                        "Novo Item", 
                        icon=ft.Icons.ADD, 
                        on_click=lambda _: open_item_modal(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_700,
                            color=ft.Colors.WHITE,
                            padding=20
                        )
                    ),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            summary_row,
            ft.Divider(),
            ft.Row([search_field, filter_category, filter_status], spacing=10),
            ft.Column([
                grid_row, 
                ft.Row([btn_load_more], alignment="center")
            ], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True),
        padding=20,
        expand=True
    )
