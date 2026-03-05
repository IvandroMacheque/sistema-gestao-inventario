import flet as ft
import data_service as ds

def DashboardView(page: ft.Page):
    # --- UI Refs for Dynamic Updates ---
    cards_row = ft.Row(spacing=20, wrap=True)
    critical_table_container = ft.Column()
    recent_movements_container = ft.Column()

    def build_metric_card(title, value, icon, color=None, text_color=None, is_alert=False):
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        
        # Determine colors
        if is_alert:
            bg = ft.Colors.RED_900 if is_dark else (color if color else ft.Colors.RED_50)
            txt = ft.Colors.RED_100 if is_dark else (text_color if text_color else ft.Colors.RED_900)
        else:
            bg = "#1E1E1E" if is_dark else (color if color else ft.Colors.WHITE)
            txt = ft.Colors.WHITE if is_dark else (text_color if text_color else ft.Colors.BLACK)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=txt if not is_alert else (ft.Colors.RED_100 if is_dark else ft.Colors.RED_700), size=30),
                    ft.Text(title, size=16, weight=ft.FontWeight.W_500, color=txt),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Text(value, size=35, weight=ft.FontWeight.BOLD, color=txt),
            ], spacing=5),
            bgcolor=bg,
            padding=20,
            border_radius=15,
            border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            width=280
        )

    def render_dashboard():
        # --- Data Calculations ---
        # Busca direto no banco os 10 itens mais críticos (requer a função no data_service)
        items_criticos_db = ds.get_critical_items(limit=5)

        # Contagens rápidas para os cards
        active_items = [i for i in ds.items if i.get("ativo", True)]
        active_apts = [l for l in ds.locations if l["tipo"] == "APARTAMENTO" and l["ativo"]]

        cards_row.controls = [
            build_metric_card("Total de Itens", str(active_items), ft.Icons.LIST_ALT, ft.Colors.BLUE_50),
            build_metric_card("Apartamentos", str(active_apts), ft.Icons.APARTMENT, ft.Colors.GREEN_50),
            build_metric_card(
                "Itens Críticos", 
                str(len(items_criticos_db)), # Mostra quantos dos 10 estão críticos
                ft.Icons.WARNING_ROUNDED, 
                ft.Colors.RED_50, 
                is_alert=True
            ),
            build_metric_card("Movimentações", str(len(ds.movements[:100])), ft.Icons.HISTORY, ft.Colors.GREY_50),
        ]
        
        # --- UI Helpers for Cards (Moved to top) ---
        def build_critical_card(ci):
            is_dark = page.theme_mode == ft.ThemeMode.DARK
            return ft.Container(
                content=ft.Row([
                    ft.Text(ci["item"]["nome"], size=14, weight="bold", expand=True),
                    ft.Container(content=ft.Text(str(ci["balance"]), size=14, weight="bold", color=ft.Colors.RED_400), width=60, alignment=ft.alignment.center),
                    ft.Container(content=ft.Text(str(ci["min"]), size=12, color=ft.Colors.GREY_500), width=60, alignment=ft.alignment.center),
                    ft.IconButton(ft.Icons.SHOPPING_CART_OUTLINED, icon_size=16, tooltip="Repor", on_click=lambda _: open_replenish(ci["item"]))
                ]),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
                border_radius=8, bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
            )

        def build_recent_movement_card(m):
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
                            ft.Text(m["created_at"].strftime("%d/%m/%Y %H:%M"), size=9, color=ft.Colors.GREY_500),
                            ft.Row([ft.Icon(cfg["icon"], color=cfg["color"], size=14), ft.Text(m["tipo"][:3].upper(), size=9, weight="bold", color=cfg["color"])], spacing=2),
                        ], spacing=1), width=70
                    ),
                    ft.Text(ds.get_item_name(m["item_id"]), size=13, weight="bold", expand=True),
                    ft.Container(content=ft.Text(str(m["quantidade"]), size=14, weight="bold"), width=40, alignment=ft.alignment.center),
                ]),
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                border=ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300),
                border_radius=8, bgcolor="#1E1E1E" if is_dark else ft.Colors.WHITE,
            )

        critical_cards = []
        for ci in items_criticos_db:
            critical_cards.append(
                build_critical_card({
                    "item": {"nome": ci["nome"], "id": ci["id"]},
                    "balance": ci["balance"],
                    "min": ci["min"]
                })
            )

        items_abaixo_minimo = ds.get_total_critical_count()

        # --- Update Cards ---
        cards_row.controls = [
            build_metric_card("Total de Itens", str(len(active_items)), ft.Icons.LIST_ALT, ft.Colors.BLUE_50),
            build_metric_card("Apartamentos Ativos", str(len(active_apts)), ft.Icons.APARTMENT, ft.Colors.GREEN_50),
            build_metric_card(
                "Itens Abaixo do Mínimo", 
                str(items_abaixo_minimo), 
                ft.Icons.WARNING_ROUNDED, 
                ft.Colors.RED_50, 
                text_color=ft.Colors.RED_900,
                is_alert=True
            ),
            build_metric_card("Movimentações", str(len(ds.movements)), ft.Icons.HISTORY, ft.Colors.GREY_50),
        ]

        # --- Update Critical Table ---
        # Note: build_critical_card is defined below, but visible at runtime
        
        critical_table_container.controls = [
            ft.Text("⚠️ Itens Críticos", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(content=ft.Row([
                ft.Text("ITEM", size=10, weight="bold", color=ft.Colors.GREY_500, expand=True),
                ft.Text("SALDO", size=10, weight="bold", color=ft.Colors.GREY_500, width=60, text_align=ft.TextAlign.CENTER),
                ft.Text("MÍN", size=10, weight="bold", color=ft.Colors.GREY_500, width=60, text_align=ft.TextAlign.CENTER),
                ft.Text("", width=40),
            ]), padding=ft.padding.symmetric(horizontal=12)),
            ft.Column(critical_cards, spacing=5) if critical_cards else ft.Text("Estoque saudável!", italic=True, color=ft.Colors.GREEN_700)
        ]

        # --- Update Recent Movements ---
        recent = sorted(ds.movements, key=lambda x: x["created_at"], reverse=True)[:5]
        recent_cards = []
        for m in recent:
            recent_cards.append(build_recent_movement_card(m))

        recent_movements_container.controls = [
            ft.Text("🕒 Últimas Movimentações", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(content=ft.Row([
                ft.Text("DATA/TIPO", size=10, weight="bold", color=ft.Colors.GREY_500, width=70),
                ft.Text("ITEM", size=10, weight="bold", color=ft.Colors.GREY_500, expand=True),
                ft.Text("QTDE", size=10, weight="bold", color=ft.Colors.GREY_500, width=40, text_align=ft.TextAlign.CENTER),
            ]), padding=ft.padding.symmetric(horizontal=12)),
            ft.Column(recent_cards, spacing=5)
        ]

    # --- Replenish Modal ---
    replenish_qty = ft.TextField(label="Quantidade a Repor", keyboard_type=ft.KeyboardType.NUMBER)
    replenish_obs = ft.TextField(label="Observação (Opcional)")
    current_replenish_item = None

    def save_replenish(e):
        if not replenish_qty.value:
            replenish_qty.error_text = "Campo obrigatório"
            page.update()
            return

        try:
            qty = float(replenish_qty.value)
        except ValueError:
            replenish_qty.error_text = "Número inválido"
            page.update()
            return

        # 1 = Compra type logic usually uses destination as '1' (General) or specific
        # Assuming general inventory (id 1) or handling via default logic
        # Dashboard context usually implies general stock replenishment
        
        # ds.add_movement(item_id, origin_id, dest_id, qty, type, obs)
        # Compra: Origem=None, Destino=1 (Geral) or logic dependent
        # Let's assume Destino=1 for now as per previous logic "destino_id": 1
        ds.add_movement(
            item_id=current_replenish_item["id"],
            origem_id=None,
            destino_id=1, 
            quantidade=qty,
            tipo="Compra",
            observacao=replenish_obs.value
        )
        
        page.snack_bar = ft.SnackBar(ft.Text("Reposição registrada com sucesso!"))
        page.snack_bar.open = True
        replenish_dialog.open = False
        render_dashboard()
        page.update()

    replenish_dialog = ft.AlertDialog(
        title=ft.Text("Repor Estoque"),
        content=ft.Container(
            content=ft.Column([
                ft.Text("Item: ...", ref=None, weight="bold"), # Will update dynamic
                replenish_qty, 
                replenish_obs
            ], tight=True),
            width=400
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(replenish_dialog, "open", False) or page.update()),
            ft.ElevatedButton("Confirmar Reposição", on_click=save_replenish, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        ]
    )
    page.overlay.append(replenish_dialog)

    def open_replenish(item):
        nonlocal current_replenish_item
        current_replenish_item = item
        replenish_dialog.title.value = f"Repor: {item['nome']}"
        replenish_qty.value = ""
        replenish_qty.error_text = None
        replenish_obs.value = ""
        replenish_dialog.open = True
        page.update()

    # --- UI Helpers for Cards ---


    # Initial Render
    render_dashboard()

    return ft.Container(
        content=ft.Column([
            ft.Text("Dashboard de Inventário", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            cards_row,
            ft.Divider(height=30),
            ft.Row([
                ft.Column([critical_table_container], expand=True), 
                ft.Column([recent_movements_container], expand=True), 
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START, spacing=40) 
        ], scroll=ft.ScrollMode.ALWAYS, expand=True),
        padding=40,
        expand=True
    )
