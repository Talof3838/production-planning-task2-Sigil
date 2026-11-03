import psycopg2
import csv
import os

# --- НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ---
DB_NAME = "production_planning_restored_SIGIL" 
DB_USER = "postgres"
from config import DB_PASSWORD
DB_HOST = "127.0.0.1"
DB_PORT = "5432"

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ИЗ CSV ---
def init_from_csv(csv_dir="data"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM resource;")
    if cur.fetchone()[0] > 0:
        print("База уже содержит данные. Пропускаем загрузку.")
        cur.close()
        conn.close()
        return

    print("База пуста. Начинаем загрузку из CSV...")

    try:
        with open(os.path.join(csv_dir, 'resources.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    is_machine = row['is_machine'].strip().lower() in ('true', '1', 'yes')
                    cur.execute(
                        "INSERT INTO resource (id, name, is_machine) VALUES (%s, %s, %s)",
                        (int(row['id']), row['name'].strip(), is_machine)
                    )
                except Exception as e:
                    print(f"[ОШИБКА] Пропущена строка ресурса: {row}. Причина: {e}")
    except FileNotFoundError:
        print("Файл resources.csv не найден!")

    try:
        with open(os.path.join(csv_dir, 'products.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur.execute(
                        "INSERT INTO technical_process (id, name) VALUES (%s, %s)",
                        (int(row['id']), row['name'].strip())
                    )
                except Exception as e:
                    print(f"[ОШИБКА] Пропущена строка изделия: {row}. Причина: {e}")
    except FileNotFoundError:
        pass

    try:
        with open(os.path.join(csv_dir, 'operations.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur.execute(
                        "INSERT INTO operation (id, name, duration) VALUES (%s, %s, %s)",
                        (int(row['id']), row['name'].strip(), int(row['duration']))
                    )
                    cur.execute(
                        "INSERT INTO tp_operation (tp_id, operation_id, step_order) VALUES (%s, %s, %s)",
                        (int(row['product_id']), int(row['id']), int(row['step_order']))
                    )
                except Exception as e:
                    print(f"[ОШИБКА] Пропущена строка операции: {row}. Причина: {e}")
    except FileNotFoundError:
        pass

    try:
        with open(os.path.join(csv_dir, 'orders.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur.execute(
                        """INSERT INTO orders (id, order_date, date_start, deadline, fine, tp_id, weight) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (int(row['id']), row['order_date'], row['date_start'], 
                         row['deadline'], int(row['fine']), int(row['tp_id']), int(row['weight']))
                    )
                except Exception as e:
                    print(f"[ОШИБКА] Пропущена строка заказа: {row}. Причина: {e}")
    except FileNotFoundError:
        pass

    conn.commit()
    cur.close()
    conn.close()
    print("Загрузка завершена!")

# --- ФУНКЦИИ ПОЛУЧЕНИЯ ДАННЫХ ---
def get_resources():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, is_machine FROM resource ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_operations_for_tp(tp_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT operation_id FROM tp_operation WHERE tp_id = %s ORDER BY step_order", (tp_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]

def get_orders():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, order_date, date_start, deadline, fine, tp_id, weight FROM orders ORDER BY id")
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def get_all_operations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, duration FROM operation ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# --- СОХРАНЕНИЕ И ЗАГРУЗКА РАСПИСАНИЯ ---
def save_schedule(schedule_items):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("TRUNCATE TABLE schedule_item RESTART IDENTITY;")
        
        for item in schedule_items:
            cur.execute(
                """INSERT INTO schedule_item (order_id, operation_id, worker_id, machine_id, start_time, end_time) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (item['order_id'], item['operation_id'], item['worker_id'], item['machine_id'], item['start_time'], item['end_time'])
            )
        
        conn.commit()
        print("Расписание успешно сохранено в базу.")
    except Exception as e:
        conn.rollback()
        print(f"[ОШИБКА] Не удалось сохранить расписание: {e}")
    finally:
        cur.close()
        conn.close()

def get_last_schedule():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_id, operation_id, worker_id, machine_id, start_time, end_time 
        FROM schedule_item 
        ORDER BY order_id, start_time
    """)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows