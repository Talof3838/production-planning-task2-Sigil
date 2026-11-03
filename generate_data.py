import csv
import os
import random
from datetime import datetime, timedelta

def generate_orders(count, folder_name):
    os.makedirs(folder_name, exist_ok=True)
    
    # Копируем ресурсы и продукты из основной папки data
    import shutil
    shutil.copy("data/resources.csv", os.path.join(folder_name, "resources.csv"))
    shutil.copy("data/products.csv", os.path.join(folder_name, "products.csv"))
    shutil.copy("data/operations.csv", os.path.join(folder_name, "operations.csv"))
    
    # Генерируем заказы
    orders = []
    base_date = datetime(2025, 3, 1)
    
    # Фиксируем seed, чтобы данные каждый раз получались одинаковыми!
    random.seed(42) 
    
    for i in range(1, count + 1):
        order_date = base_date + timedelta(days=random.randint(0, 5))
        date_start = order_date + timedelta(days=2, hours=8)
        
        # Делаем сроки разными, чтобы были и просрочки
        deadline = date_start + timedelta(days=random.randint(1, 4), hours=random.randint(8, 18))
        
        fine = random.choice([5000, 10000, 15000, 30000, 50000])
        tp_id = random.randint(1, 3)
        weight = random.randint(1, 5)
        
        orders.append([
            i, 
            order_date.strftime("%Y-%m-%d %H:%M:%S"),
            date_start.strftime("%Y-%m-%d %H:%M:%S"),
            deadline.strftime("%Y-%m-%d %H:%M:%S"),
            fine, 
            tp_id, 
            weight
        ])
        
    with open(os.path.join(folder_name, "orders.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "order_date", "date_start", "deadline", "fine", "tp_id", "weight"])
        writer.writerows(orders)
    
    print(f"Сгенерирован набор {folder_name} ({count} заказов)")

# Генерируем 3 набора
generate_orders(5, "data_small")
generate_orders(15, "data_medium")
generate_orders(30, "data_large")