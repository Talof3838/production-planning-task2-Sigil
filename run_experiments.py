import time
import database
import main
import tkinter as tk

def clear_db():
    conn = database.get_connection()
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE schedule_item, orders, tp_operation, operation, technical_process, resource CASCADE;")
    conn.commit()
    cur.close()
    conn.close()

datasets = ["data_small", "data_medium", "data_large"]
rules = ["FIFO", "EDD", "SPT", "LPT", "WSPT"]

print(f"{'Правило':<8} | {'Набор':<12} | {'Штраф':<12} | {'Просрочено':<11} | {'Макс.просрочка':<15} | {'Окончание':<17} | {'Время (с)':<10}")
print("-" * 105)

for dataset in datasets:
    clear_db()
    database.init_from_csv(csv_dir=dataset)
    
    root = tk.Tk()
    root.withdraw() 
    app = main.SchedulerApp(root)
    
    for rule in rules:
        start_time = time.time()
        sorted_orders = main.sort_orders(app.orders, rule, app.tps_dict)
        schedule = main.build_schedule(sorted_orders, app.machines, app.workers, app.tps_dict, app.ops_dict)
        fine, late_count, max_tard, end_time = main.evaluate_schedule(schedule, app.orders_dict)
        elapsed = time.time() - start_time
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M") if end_time != main.datetime.datetime.min else "-"
        
        print(f"{rule:<8} | {dataset:<12} | {fine:<12.2f} | {late_count:<11} | {max_tard:<15.1f} | {end_time_str:<17} | {elapsed:<10.4f}")
    
    root.destroy()

print("-" * 105)
print("Тестирование завершено! Скопируй эту таблицу в отчет.")