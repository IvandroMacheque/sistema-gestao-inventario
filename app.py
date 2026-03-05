import flet as ft
from movements_view import MovementsView
from apartments_view import ApartmentsView
from items_view import ItemsView
from dashboard_view import DashboardView
from settings_view import SettingsView
from reports_view import ReportsView
import data_service as ds
import sys
import os

def main(page: ft.Page):
    ds.init_db()
    page.title = "Sistema de Gestão de Inventário"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1350
    page.window_height = 950
    page.padding = 0
    page.spacing = 0
    if getattr(sys, 'frozen', False):
        basedir = os.path.dirname(sys.executable)
    else:
        basedir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(basedir, "assets", "icon.ico")
    page.window_icon = icon_path

    # --- Espaço para o conteúdo que muda ---
    content_area = ft.Container(expand=True, padding=20)

    # --- Banner de Erro de Conexão (Feito sob medida) ---
    def retry_connection(e):
        ds.reset_connection()
        page.change_view(rail.selected_index)

    error_banner = ft.Container(
        bgcolor=ft.Colors.RED_700,
        padding=10,
        visible=False,
        content=ft.Row(
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.STORAGE, color=ft.Colors.WHITE, size=30),
                    ft.Text(
                        "ERRO DE CONEXÃO: O servidor do banco de dados está offline.",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD,
                    ),
                ], spacing=10),
                ft.ElevatedButton(
                    "Tentar Agora", 
                    on_click=retry_connection, 
                    color=ft.Colors.RED_700, 
                    bgcolor=ft.Colors.WHITE
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
    )

    def check_connection():
        if ds.connection_error:
            # Atualiza o texto se precisar, mas o estático já resolve bem
            error_banner.visible = True
        else:
            error_banner.visible = False
        error_banner.update()

    def change_view(index, initial_data=None):
        content_area.content = None
        rail.selected_index = index
        if index == 0:
            content_area.content = ApartmentsView(page)
        elif index == 1:
            content_area.content = MovementsView(page, initial_data=initial_data)
        elif index == 2:
            content_area.content = ItemsView(page)
        elif index == 3:
            content_area.content = DashboardView(page)
        elif index == 4:
            content_area.content = ReportsView(page)
        elif index == 5:
            content_area.content = SettingsView(page)
        
        check_connection() # Dá uma conferida no status toda vez que muda de tela
        page.update()

    # Deixa o change_view acessível para outras partes do app pelo objeto page
    page.change_view = change_view

    # --- Menu Lateral ---
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        leading=ft.Container(
            content=ft.Icon(ft.Icons.INVENTORY_2, size=40, color=ft.Colors.BLUE_700),
            padding=ft.padding.all(20)
        ),
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.APARTMENT_OUTLINED,
                selected_icon=ft.Icons.APARTMENT,
                label="Apartamentos",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.MOVE_UP_OUTLINED,
                selected_icon=ft.Icons.MOVE_UP,
                label="Movimentações",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.LIST_ALT_OUTLINED,
                selected_icon=ft.Icons.LIST_ALT,
                label="Inventário",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BAR_CHART_OUTLINED,
                selected_icon=ft.Icons.BAR_CHART,
                label="Relatórios",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Configurações",
            ),
        ],
        on_change=lambda e: change_view(e.control.selected_index),
    )

    # Adicionando os elementos na página ANTES de carregar a primeira tela
    # Isso evita aquele erro chato de "Control must be added to the page first"
    page.add(
        ft.Column(
            [
                error_banner,
                ft.Row(
                    [
                        rail,
                        ft.VerticalDivider(width=1),
                        content_area,
                    ],
                    expand=True,
                )
            ],
            expand=True,
            spacing=0
        )
    )

    # Tela inicial (Apartamentos) - Agora é seguro chamar porque o banner de erro já existe
    change_view(0)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
