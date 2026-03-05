import flet as ft

def SettingsView(page: ft.Page):
    def toggle_theme(e):
        is_dark = e.control.value
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        theme_icon.name = ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE
        
        # Update container styling immediately
        appearance_container.bgcolor = "#1E1E1E" if is_dark else ft.Colors.WHITE
        appearance_container.border = ft.border.all(1, ft.Colors.GREY_800 if is_dark else ft.Colors.GREY_300)
        
        page.update()

    theme_icon = ft.Icon(
        ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.LIGHT_MODE,
        color=ft.Colors.BLUE_700
    )

    theme_switch = ft.Switch(
        label="Modo Escuro",
        value=page.theme_mode == ft.ThemeMode.DARK,
        on_change=toggle_theme
    )

    appearance_container = ft.Container(
        content=ft.Column([
            ft.Text("Aparência", size=20, weight=ft.FontWeight.W_500),
            ft.Row([
                theme_icon,
                theme_switch
            ], spacing=20),
        ], spacing=10),
        padding=20,
        border=ft.border.all(1, ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.GREY_300),
        border_radius=10,
        bgcolor="#1E1E1E" if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.WHITE
    )

    return ft.Container(
        content=ft.Column([
            ft.Text("Configurações", size=30, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            appearance_container,
            ft.Container(
                content=ft.Text("Versão do Sistema: 1.1", color=ft.Colors.GREY_500),
                margin=ft.margin.only(top=20)
            )
        ], expand=True),
        padding=20,
        expand=True
    )
