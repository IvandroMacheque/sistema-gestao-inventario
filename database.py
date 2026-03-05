import psycopg2
from psycopg2 import extras
import os
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 0. Funçãozinha camarada para ver se a coluna já existe
        def column_exists(table, column):
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{column}'")
            return cursor.fetchone() is not None

        # 1. Função e Gatilho para atualizar o 'updated_at' automaticamente
        cursor.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """)

        # --- Gatilho para Sincronizar o Nome da Categoria ---
        cursor.execute("""
        CREATE OR REPLACE FUNCTION sync_item_category_name()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.category_id IS NOT NULL THEN
                SELECT nome INTO NEW.categoria FROM categories WHERE id = NEW.category_id;
            ELSE
                NEW.categoria = NULL;
            END IF;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """)

        # 2. Tabelas Principais (Garante que elas existam)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            categoria TEXT,
            category_id INTEGER,
            quantidade_minima REAL DEFAULT 0,
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            status_ocupacao TEXT DEFAULT 'DISPONIVEL',
            ativo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movements (
            id SERIAL PRIMARY KEY,
            item_id INTEGER NOT NULL,
            origem_id INTEGER,
            destino_id INTEGER,
            quantidade REAL NOT NULL,
            tipo TEXT NOT NULL,
            observacao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id),
            FOREIGN KEY (origem_id) REFERENCES locations (id),
            FOREIGN KEY (destino_id) REFERENCES locations (id)
        )
        """)

        # 3. Migrações (Adiciona colunas que faltam ou renomeia)
        for table in ["items", "locations", "movements", "categories"]:
            if table != "categories" and not column_exists(table, "created_at"):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if table != "categories" and not column_exists(table, "updated_at"):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        if not column_exists("items", "category_id"):
            cursor.execute("ALTER TABLE items ADD COLUMN category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL")
        else:
            # Atualiza a restrição existente para fazer o SET NULL ao deletar
            cursor.execute("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'items'::regclass 
                AND confrelid = 'categories'::regclass
            """)
            constraint = cursor.fetchone()
            if constraint:
                conname = constraint[0]
                cursor.execute(f"ALTER TABLE items DROP CONSTRAINT {conname}")
                cursor.execute("ALTER TABLE items ADD CONSTRAINT items_category_id_fkey FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL")

        # Sincroniza o nome da categoria de volta para manter a consistência
        cursor.execute("""
            UPDATE items i 
            SET categoria = c.nome 
            FROM categories c 
            WHERE i.category_id = c.id AND (i.categoria IS NULL OR i.categoria = '')
        """)
        cursor.execute("SELECT DISTINCT categoria FROM items WHERE categoria IS NOT NULL")
        existing_cats = cursor.fetchall()
        for row in existing_cats:
            cat_name = row[0]
            cursor.execute("INSERT INTO categories (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (cat_name,))
        
        # Atualiza o category_id com base no texto da categoria
        cursor.execute("""
            UPDATE items i 
            SET category_id = c.id 
            FROM categories c 
            WHERE i.categoria = c.nome AND i.category_id IS NULL
        """)

        if column_exists("movements", "data") and not column_exists("movements", "created_at_new"):
            try:
                cursor.execute("UPDATE movements SET created_at = CAST(data AS TIMESTAMP) WHERE data IS NOT NULL")
                cursor.execute("ALTER TABLE movements DROP COLUMN data")
            except:
                cursor.execute("ALTER TABLE movements DROP COLUMN data")

        # 4. Gatilhos (Triggers)
        for table in ["items", "locations", "movements"]:
            cursor.execute(f"DROP TRIGGER IF EXISTS set_timestamp ON {table}")
            cursor.execute(f"""
            CREATE TRIGGER set_timestamp
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE update_updated_at_column();
            """)

        # Gatilho de Sincronização Especial para itens
        cursor.execute("DROP TRIGGER IF EXISTS trg_sync_category_name ON items")
        cursor.execute("""
        CREATE TRIGGER trg_sync_category_name
        BEFORE INSERT OR UPDATE OF category_id ON items
        FOR EACH ROW
        EXECUTE PROCEDURE sync_item_category_name();
        """)

        conn.commit()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    try:
        init_db()
        print("Database initialized successfully on PostgreSQL.")
    except Exception as e:
        print(f"Error initializing database: {e}")
