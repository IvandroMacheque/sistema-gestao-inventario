import database
import psycopg2
from datetime import datetime
from psycopg2 import extras

def init_db():
    global connection_error
    try:
        database.init_db()
        connection_error = None
    except Exception as e:
        connection_error = f"Erro na inicialização: {str(e)}"
        print(f"DB Init Error: {e}")

connection_error = None
last_failure_time = None
RETRY_INTERVAL = 5 # Seconds

def reset_connection():
    global connection_error, last_failure_time
    connection_error = None
    last_failure_time = None

def _query(sql, params=None, fetch=True):
    global connection_error, last_failure_time
    
    # Auto-Recovery / Circuit Breaker
    if connection_error:
        # If enough time has passed, let's try to reconnect nicely
        if last_failure_time and (datetime.now() - last_failure_time).total_seconds() > RETRY_INTERVAL:
            # Allow one attempt (we'll see if it works in the try block below)
            pass 
        else:
            # Still in "cooldown", fail fast
            return [] if fetch else None

    try:
        conn = database.get_connection()
        connection_error = None # Reset on success
        last_failure_time = None
        # Use RealDictCursor to get results as dictionaries automatically
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        # Use RealDictCursor to get results as dictionaries automatically
        cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
        try:
            cursor.execute(sql, params)
            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = None
        finally:
            cursor.close()
            conn.close()
        return result
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        connection_error = str(e)
        last_failure_time = datetime.now()
        return [] if fetch else None
    except Exception as e:
        connection_error = f"Erro inesperado: {str(e)}"
        last_failure_time = datetime.now()
        return [] if fetch else None

def get_apartment_stock(apt_id):
    """
    Busca o estoque completo de um apartamento em UMA única consulta.
    Retorna apenas itens com saldo > 0.
    """
    sql = """
        SELECT 
            i.id, 
            i.nome, 
            c.nome as categoria,
            (COALESCE(SUM(CASE WHEN m.destino_id = %s THEN m.quantidade ELSE 0 END), 0) - 
             COALESCE(SUM(CASE WHEN m.origem_id = %s THEN m.quantidade ELSE 0 END), 0)) as saldo
        FROM items i
        LEFT JOIN movements m ON i.id = m.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE i.ativo = TRUE
        GROUP BY i.id, i.nome, c.nome
        HAVING (COALESCE(SUM(CASE WHEN m.destino_id = %s THEN m.quantidade ELSE 0 END), 0) - 
                COALESCE(SUM(CASE WHEN m.origem_id = %s THEN m.quantidade ELSE 0 END), 0)) > 0
        ORDER BY c.nome ASC, i.nome ASC
    """
    return _query(sql, (apt_id, apt_id, apt_id, apt_id))

def get_items(limit=None, offset=None, filters=None):
    sql = """
        SELECT i.*, c.nome as categoria 
        FROM items i 
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE i.ativo = TRUE
    """
    params = []
    
    if filters:
        if filters.get("search"):
            sql += " AND (LOWER(i.nome) LIKE LOWER(%s) OR LOWER(c.nome) LIKE LOWER(%s))"
            params.append(f"%{filters['search']}%")
            params.append(f"%{filters['search']}%")
        
        if filters.get("categoria") and filters["categoria"] != "Todas":
            sql += " AND c.nome = %s"
            params.append(filters["categoria"])

    sql += " ORDER BY i.nome ASC"

    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    if offset is not None:
        sql += " OFFSET %s"
        params.append(offset)

    return _query(sql, tuple(params))

def get_critical_items(limit=10):
    """Busca itens abaixo do mínimo usando uma única query SQL de alta performance."""
    sql = """
        SELECT 
            i.id, 
            i.nome, 
            i.quantidade_minima as min,
            (COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND destino_id = 1), 0) - 
             COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND origem_id = 1), 0)) as balance
        FROM items i
        WHERE i.ativo = TRUE
        GROUP BY i.id, i.nome, i.quantidade_minima
        HAVING (COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND destino_id = 1), 0) - 
                COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND origem_id = 1), 0)) <= i.quantidade_minima
        ORDER BY (i.quantidade_minima - (COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND destino_id = 1), 0) - 
                                         COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND origem_id = 1), 0))) DESC
        LIMIT %s
    """
    return _query(sql, (limit,))

def get_total_critical_count():
    """Retorna o número total de itens abaixo do mínimo no banco todo."""
    sql = """
        SELECT COUNT(*) as total FROM (
            SELECT i.id
            FROM items i
            WHERE i.ativo = TRUE
            GROUP BY i.id, i.quantidade_minima
            HAVING (COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND destino_id = 1), 0) - 
                    COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND origem_id = 1), 0)) <= i.quantidade_minima
        ) as subquery
    """
    res = _query(sql)
    return res[0]['total'] if res else 0

def get_locations():
    return _query("SELECT * FROM locations")

def get_movements(limit=None, offset=None, filters=None):
    sql = "SELECT * FROM movements"
    params = []
    where_clauses = []
    
    if filters:
        if filters.get("tipo") and filters["tipo"] != "Todos":
            where_clauses.append("tipo = %s")
            params.append(filters["tipo"])
        
        if filters.get("item_id") and filters["item_id"] != "0":
            where_clauses.append("item_id = %s")
            params.append(int(filters["item_id"]))
            
        if filters.get("apt_id") and filters["apt_id"] != "0":
            where_clauses.append("(origem_id = %s OR destino_id = %s)")
            params.append(int(filters["apt_id"]))
            params.append(int(filters["apt_id"]))

        if filters.get("date_start"):
            where_clauses.append("created_at >= %s")
            params.append(filters["date_start"])
            
        if filters.get("date_end"):
            where_clauses.append("created_at <= %s")
            params.append(filters["date_end"])

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    
    sql += " ORDER BY created_at DESC"
    
    if limit is not None:
        sql += " LIMIT %s"
        # Ensure params is a list before appending
        params.append(limit)
        
    if offset is not None:
        sql += " OFFSET %s"
        params.append(offset)
        
    return _query(sql, tuple(params))

def get_categories():
    return _query("SELECT * FROM categories ORDER BY nome")

def add_category(nome):
    _query("INSERT INTO categories (nome) VALUES (%s)", (nome,), fetch=False)

def update_category(cat_id, nome):
    _query("UPDATE categories SET nome=%s WHERE id=%s", (nome, cat_id), fetch=False)

def delete_category(cat_id):
    # Optional: check if items use this category
    _query("DELETE FROM categories WHERE id=%s", (cat_id,), fetch=False)

def get_item_category_name(item):
    if item.get("category_id"):
        res = _query("SELECT nome FROM categories WHERE id=%s", (item["category_id"],))
        return res[0]['nome'] if res else "Geral"
    return item.get("categoria") or "Geral"

def __getattr__(name):
    if name == "items":
        return get_items()
    if name == "locations":
        return get_locations()
    if name == "movements":
        return get_movements()
    if name == "categories":
        return get_categories()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def get_balance(item_id, location_id):
    if location_id is None:
        return 0
    
    total_in = _query("SELECT SUM(quantidade) as total FROM movements WHERE item_id = %s AND destino_id = %s", (item_id, location_id))
    total_in = total_in[0]['total'] or 0
    
    total_out = _query("SELECT SUM(quantidade) as total FROM movements WHERE item_id = %s AND origem_id = %s", (item_id, location_id))
    total_out = total_out[0]['total'] or 0
    
    return total_in - total_out

def add_movement(item_id, origem_id, destino_id, quantidade, tipo, observacao=""):
    _query("""
        INSERT INTO movements (item_id, origem_id, destino_id, quantidade, tipo, observacao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (item_id, origem_id, destino_id, quantidade, tipo, observacao), fetch=False)

def update_movement(movement_id, item_id, origem_id, destino_id, quantidade, tipo, observacao=""):
    _query("""
        UPDATE movements SET item_id=%s, origem_id=%s, destino_id=%s, quantidade=%s, tipo=%s, observacao=%s
        WHERE id=%s
    """, (item_id, origem_id, destino_id, quantidade, tipo, observacao, movement_id), fetch=False)

def add_apartment(nome, status="DISPONIVEL"):
    _query("INSERT INTO locations (nome, tipo, status_ocupacao) VALUES (%s, %s, %s)", (nome, "APARTAMENTO", status), fetch=False)

def toggle_apartment_status(apt_id):
    current = _query("SELECT status_ocupacao FROM locations WHERE id=%s", (apt_id,))
    if current:
        new_status = "OCUPADO" if current[0]['status_ocupacao'] == "DISPONIVEL" else "DISPONIVEL"
        _query("UPDATE locations SET status_ocupacao=%s WHERE id=%s", (new_status, apt_id), fetch=False)

def toggle_apartment_active(apt_id):
    current = _query("SELECT ativo FROM locations WHERE id=%s", (apt_id,))
    if current:
        _query("UPDATE locations SET ativo=%s WHERE id=%s", (not current[0]['ativo'], apt_id), fetch=False)

def add_item(nome, category_id, quantidade_minima):
    _query("INSERT INTO items (nome, category_id, quantidade_minima) VALUES (%s, %s, %s)", (nome, category_id, quantidade_minima), fetch=False)

def update_item(item_id, nome, category_id, quantidade_minima):
    _query("UPDATE items SET nome=%s, category_id=%s, quantidade_minima=%s WHERE id=%s", (nome, category_id, quantidade_minima, item_id), fetch=False)

def toggle_item_active(item_id):
    current = _query("SELECT ativo FROM items WHERE id=%s", (item_id,))
    if current:
        _query("UPDATE items SET ativo=%s WHERE id=%s", (not current[0]['ativo'], item_id), fetch=False)

def item_has_movements(item_id):
    res = _query("SELECT 1 FROM movements WHERE item_id=%s LIMIT 1", (item_id,))
    return len(res) > 0

def get_item_name(item_id):
    if not item_id: return "-"
    res = _query("SELECT nome FROM items WHERE id=%s", (item_id,))
    return res[0]['nome'] if res else "Desconhecido"

def item_count():
    res = _query("SELECT * FROM items")
    return len(res)

def get_location_name(location_id):
    if not location_id: return "-"
    res = _query("SELECT nome FROM locations WHERE id=%s", (location_id,))
    return res[0]['nome'] if res else "Desconhecido"

def get_total_balances():
    """Returns a dict {item_id: total_balance} for all items."""
    sql = """
        SELECT i.id, 
               COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND destino_id IS NOT NULL), 0) -
               COALESCE((SELECT SUM(quantidade) FROM movements WHERE item_id = i.id AND origem_id IS NOT NULL), 0) as balance
        FROM items i
    """
    results = _query(sql)
    return {r['id']: r['balance'] for r in results}
