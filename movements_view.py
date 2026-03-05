import flet as ft
import data_service as ds

def MovementsView(page: ft.Page, initial_data=None):
    # --- State Management ---
    editing_id = None
    current_filter = "Todos"
    LIMIT = 10
    current_offset = 0
    total_loaded = 0
    is_loading = False
    
    # --- UI Refs ---
    # Using ListView for better performance with large lists
    list_view = ft.ListView(expand=True, spacing=5, padding=10)
    load_more_btn = ft.ElevatedButton("Carregar Mais", on_click=lambda e: load_more(), visible=False)
    progress_ring = ft.ProgressRing(visible=False)
    
    # Container to hold list and loader
    list_container = ft.Column([
        list_view,
        ft.Row([progress_ring, load_more_btn], alignment=ft.MainAxisAlignment.CENTER, height=50)
    ], expand=True)

    # --- Form Controls ---
    type_dropdown = ft.Dropdown(
        label="Tipo",
        options=[
            ft.dropdown.Option("Compra"),
            ft.dropdown.Option("Transferência"),
            ft.dropdown.Option("Retorno"),
            ft.dropdown.Option("Perda"),
            ft.dropdown.Option("Ajuste"),
        ],
        on_change=lambda e: update_form_logic()
    )
    
    item_dropdown = ft.Dropdown(
        label="Item",
        options=[ft.dropdown.Option(str(i["id"]), i["nome"]) for i in ds.items],
        on_change=lambda e: update_balance_display()
    )
    
    origin_dropdown = ft.Dropdown(
        label="Origem",
        options=[ft.dropdown.Option(str(l["id"]), l["nome"]) for l in ds.locations if l["ativo"]],
        on_change=lambda e: update_balance_display()
    )
    
    dest_dropdown = ft.Dropdown(
        label="Destino",
        options=[ft.dropdown.Option(str(l["id"]), l["nome"]) for l in ds.locations if l["ativo"]]
    )
    
    quantity_field = ft.TextField(label="Quantidade", keyboard_type=ft.KeyboardType.NUMBER)
    obs_field = ft.TextField(label="Observação", multiline=True)
    balance_text = ft.Text("Saldo disponível na origem: -", color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD)

    # --- Helper Functions ---
    def update_balance_display():
        v_item = item_dropdown.value
        v_orig = origin_dropdown.value
        
        # Safety check: ensure values are not None and are digit strings
        if v_item and v_orig and v_item != "None" and v_orig != "None":
            try:
                balance = ds.get_balance(int(v_item), int(v_orig))
                balance_text.value = f"Saldo disponível na origem: {balance}"
            except (ValueError, TypeError):
                balance_text.value = "Saldo disponível na origem: -"
        else:
            balance_text.value = "Saldo disponível na origem: -"
        page.update()

    def update_form_logic():
        t = type_dropdown.value
        # Reset drops
        origin_dropdown.disabled = False
        dest_dropdown.disabled = False
        
        if t == "Compra":
            origin_dropdown.value = None
            origin_dropdown.disabled = True
            # Auto-select "Inventário Geral" (ID 1)
            dest_dropdown.value = "1"
        elif t == "Perda":
            dest_dropdown.value = None
            dest_dropdown.disabled = True
        
        update_balance_display()
        page.update()

    def validate():
        # Clear previous errors
        type_dropdown.error_text = None
        item_dropdown.error_text = None
        origin_dropdown.error_text = None
        dest_dropdown.error_text = None
        quantity_field.error_text = None
        
        has_error = False
        if not type_dropdown.value:
            type_dropdown.error_text = "Campo obrigatório"
            has_error = True
        if not item_dropdown.value:
            item_dropdown.error_text = "Campo obrigatório"
            has_error = True
        if not quantity_field.value:
            quantity_field.error_text = "Campo obrigatório"
            has_error = True
            
        if has_error:
            page.update()
            return "Preencha os campos obrigatórios."
        
        try:
            qty = float(quantity_field.value)
            if qty <= 0:
                quantity_field.error_text = "A quantidade deve ser maior que zero"
                page.update()
                return "Erro de validação"
        except ValueError:
            quantity_field.error_text = "coloque um numero valido"
            page.update()
            return "Erro de validação"
        
        t = type_dropdown.value
        item_id = int(item_dropdown.value)
        
        # Balance validation for exits
        if t in ["Transferência", "Perda", "Ajuste", "Retorno"]:
            if not origin_dropdown.value:
                origin_dropdown.error_text = "Origem é obrigatória"
                page.update()
                return "Erro de validação"
            
            orig_id = int(origin_dropdown.value)
            current_balance = ds.get_balance(item_id, orig_id)
            
            # If editing, we need to "refund" the current movement quantity to check valid limit
            if editing_id:
                old_m = next((m for m in ds.get_movements(limit=1, filters={"id": editing_id})), None)
                if old_m and old_m["origem_id"] == orig_id:
                     current_balance += old_m["quantidade"]

            if qty > current_balance:
                quantity_field.error_text = f"Saldo insuficiente ({current_balance})"
                page.update()
                return "Erro de validação"

        if t in ["Transferência", "Retorno"]:
            if not dest_dropdown.value:
                dest_dropdown.error_text = "Destino é obrigatório"
                page.update()
                return "Erro de validação"
            if t == "Transferência" and origin_dropdown.value == dest_dropdown.value:
                dest_dropdown.error_text = "Deve ser diferente da origem"
                page.update()
                return "Erro de validação"
        
        return None

    def save_movement(e):
        nonlocal editing_id
        
        # Disable button to prevent double-click
        e.control.disabled = True
        page.update()
        
        error = validate()
        if error:
            # Re-enable button on validation error
            e.control.disabled = False
            page.snack_bar = ft.SnackBar(ft.Text(error), bgcolor=ft.Colors.RED_700)
            page.snack_bar.open = True
            page.update()
            return

        item_id = int(item_dropdown.value)
        orig_id = int(origin_dropdown.value) if origin_dropdown.value else None
        dest_id = int(dest_dropdown.value) if dest_dropdown.value else None
        qty = float(quantity_field.value)
        
        if editing_id:
            ds.update_movement(editing_id, item_id, orig_id, dest_id, qty, type_dropdown.value, obs_field.value)
            page.snack_bar = ft.SnackBar(ft.Text("Movimentação atualizada com sucesso!"))
        else:
            ds.add_movement(item_id, orig_id, dest_id, qty, type_dropdown.value, obs_field.value)
            page.snack_bar = ft.SnackBar(ft.Text("Movimentação registrada com sucesso!"))
        
        page.snack_bar.open = True
        dialog.open = False
        reset_list() # Reload list to show new item
        page.update()

    def open_modal(m=None):
        nonlocal editing_id
        editing_id = m["id"] if m else None
        
        # Clear errors and re-enable save button
        type_dropdown.error_text = None
        item_dropdown.error_text = None
        origin_dropdown.error_text = None
        dest_dropdown.error_text = None
        quantity_field.error_text = None
        dialog.actions[1].disabled = False
        
        # Reset form
        type_dropdown.value = m["tipo"] if m else "Transferência"
        item_dropdown.value = str(m["item_id"]) if m else None
        origin_dropdown.value = str(m["origem_id"]) if m and m["origem_id"] else None
        dest_dropdown.value = str(m["destino_id"]) if m and m["destino_id"] else None
        quantity_field.value = str(m["quantidade"]) if m else ""
        obs_field.value = m["observacao"] if m else ""
        
        update_form_logic()
        dialog.title = ft.Text("Editar Movimentação" if m else "Nova Movimentação")
        dialog.open = True
        page.update()

    # --- UI Components ---

    def build_movement_card(m):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        
        # Color & Icon based on Type
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
                # Date & Type
                ft.Container(
                    content=ft.Column([
                        ft.Text(m["created_at"].strftime("%d/%m/%Y %H:%M"), size=10, color=ft.Colors.GREY_500),
                        ft.Row([
                            ft.Icon(cfg["icon"], color=cfg["color"], size=16),
                            ft.Text(m["tipo"].upper(), size=10, weight="bold", color=cfg["color"]),
                        ], spacing=5),
                    ], spacing=2),
                    width=130
                ),
                # Item
                ft.Text(ds.get_item_name(m["item_id"]), size=15, weight="bold", expand=True),
                # Path (Origin -> Destination)
                ft.Row([
                    ft.Text(ds.get_location_name(m["origem_id"]), size=13, weight="w500", color=ft.Colors.GREY_400 if not m["origem_id"] else None),
                    ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400),
                    ft.Text(ds.get_location_name(m["destino_id"]), size=13, weight="w500", color=ft.Colors.GREY_400 if not m["destino_id"] else None),
                ], spacing=10, expand=True),
                # Quantity
                ft.Container(
                    content=ft.Text(str(m["quantidade"]), size=16, weight="bold"),
                    width=80,
                    alignment=ft.alignment.center
                ),
                # Actions
                ft.Row([
                    ft.IconButton(ft.Icons.INFO_OUTLINE, icon_size=18, tooltip=m["observacao"], on_click=lambda e: open_modal(m), visible=bool(m["observacao"])),
                    # Disable edit for now or implement logic to support pagination update
                    # ft.IconButton(ft.Icons.EDIT, icon_size=18, on_click=lambda e: open_modal(m)) 
                ], spacing=0)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            border_radius=8,
            bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
        )

    # --- Header Row ---
    header_row = ft.Container(
        content=ft.Row([
            ft.Text("DATA / TIPO", size=11, weight="bold", color=ft.Colors.GREY_500, width=130),
            ft.Text("ITEM", size=11, weight="bold", color=ft.Colors.GREY_500, expand=True),
            ft.Text("ORIGEM ➜ DESTINO", size=11, weight="bold", color=ft.Colors.GREY_500, expand=True),
            ft.Text("QTDE", size=11, weight="bold", color=ft.Colors.GREY_500, width=80, text_align=ft.TextAlign.CENTER),
            ft.Text("AÇÕES", size=11, weight="bold", color=ft.Colors.GREY_500, width=80, text_align=ft.TextAlign.RIGHT),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=15, vertical=5)
    )

    # --- Pagination Logic ---
    def load_more(update_page=True):
        nonlocal current_offset, is_loading
        if is_loading: return
        
        is_loading = True
        progress_ring.visible = True
        load_more_btn.visible = False
        if update_page: page.update()
        
        # Prepare filters
        filters = {}
        if current_filter != "Todos":
            filters["tipo"] = current_filter
            
        # Fetch data
        new_items = ds.get_movements(limit=LIMIT, offset=current_offset, filters=filters)
        
        if new_items:
            for m in new_items:
                list_view.controls.append(build_movement_card(m))
            current_offset += LIMIT
            load_more_btn.visible = True
        else:
            load_more_btn.visible = False # No more items
            
        is_loading = False
        progress_ring.visible = False
        if update_page: page.update()

    def reset_list(update_page=True):
        nonlocal current_offset
        current_offset = 0
        list_view.controls.clear()
        load_more(update_page)

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
        reset_list()
        page.update()

    filter_options = ["Todos", "Compra", "Transferência", "Retorno", "Perda", "Ajuste"]
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

    # --- Initial UI Build ---
    dialog = ft.AlertDialog(
        title=ft.Text("Nova Movimentação"),
        content=ft.Container(
            content=ft.Column([
                type_dropdown,
                item_dropdown,
                origin_dropdown,
                dest_dropdown,
                quantity_field,
                obs_field,
                balance_text,
            ], tight=True, spacing=10),
            width=600
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(dialog, "open", False) or page.update()),
            ft.ElevatedButton("Salvar", on_click=save_movement, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
        ],
    )
    page.overlay.append(dialog)

    # Initial Load
    reset_list(update_page=False)

    # --- Auto-open if redirected ---
    if initial_data:
        if "tipo" in initial_data: type_dropdown.value = initial_data["tipo"]
        if "item_id" in initial_data: item_dropdown.value = str(initial_data["item_id"])
        if "origem_id" in initial_data: origin_dropdown.value = str(initial_data["origem_id"])
        if "destino_id" in initial_data: dest_dropdown.value = str(initial_data["destino_id"])
        
        update_form_logic()
        update_balance_display()
        dialog.title = ft.Text("Nova Movimentação (Preenchida)")
        dialog.open = True
        page.update()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Movimentações", size=30, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton(
                    "Nova Movimentação", 
                    icon=ft.Icons.ADD, 
                    on_click=lambda _: open_modal(),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                        padding=20
                    )
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            filter_row,
            ft.Divider(),
            header_row,
            list_container
        ], expand=True),
        padding=20,
        expand=True
    )
