import os
import sys

def get_exports_dir():
    # Verifica se está rodando como executável (congelado)
    if getattr(sys, 'frozen', False):
        # Se for .exe, pega a pasta onde o .exe está
        base_dir = os.path.dirname(sys.executable)
    else:
        # Se for código normal, pega a pasta do arquivo
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    export_dir = os.path.join(base_dir, "exports") # Salva numa pasta 'exports' visível
    
    if not os.path.exists(export_dir):
        os.makedirs(export_dir, exist_ok=True)
        
    return export_dir

def get_download_url(filename):
    # No Desktop, retornamos o caminho completo do arquivo para o OS abrir
    return os.path.join(get_exports_dir(), filename)