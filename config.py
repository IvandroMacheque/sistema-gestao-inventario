import os
import configparser

config = configparser.ConfigParser()
config_file = 'config.ini'

DB_CONFIG = {
    "dbname": "inventario",
    "user": "postgres",
    "password": "senha_padrao_segura",
    "host": "localhost",
    "port": "5432"
}

if os.path.exists(config_file):
    config.read(config_file)
    if 'DATABASE' in config:
        DB_CONFIG["dbname"] = config['DATABASE'].get('dbname', 'inventario')
        DB_CONFIG["user"] = config['DATABASE'].get('user', 'postgres')
        DB_CONFIG["password"] = config['DATABASE'].get('password', '')
        DB_CONFIG["host"] = config['DATABASE'].get('host', 'localhost')
        DB_CONFIG["port"] = config['DATABASE'].get('port', '5432')
else:
    DB_CONFIG["password"] = os.environ.get("DB_PASS", "senha_indefinida")