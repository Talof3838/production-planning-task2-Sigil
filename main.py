import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass
from typing import List, Optional
import datetime
import csv
import os  # <--- ДОБАВЛЕНО ДЛЯ ПУТЕЙ
import database  # Наш модуль для работы с БД

# --- СТРУКТУРЫ ---

@dataclass
class Order:
    id: int
    order_date: datetime.datetime
    date_start: datetime.datetime
    deadline: datetime.datetime
    fine: int
    tp_id: int
    weight: int

@dataclass
class Operation:
    id: int
    name: str
    duration: int

@dataclass
class Resource:
    id: int
    name: str
    is_machine: bool

@dataclass
class ScheduleItem:
    order_id: int
    operation_id: int
    worker_id: Optional[int]
    machine_id: Optional[int]
    start_time: datetime.datetime
    end_time: datetime.datetime

# --- ПРАВИЛА ПРИОРИТЕТА (Часть 2, п.1) ---
def get_order_duration(order, tps_dict):
    """Считает суммарную длительность техпроцесса для заказа"""
    op_ids = tps_dict.get(order.tp_id, [])
    all_ops = {op[0]: op[2] for op in database.get_all_operations()}
    return sum(all_ops.get(op_id, 0) for op_id in op_ids)

def sort_orders(orders, rule, tps_dict):
    if rule == "FIFO":
        return sorted(orders, key=lambda x: x.id)
    elif rule == "EDD":
        return sorted(orders, key=lambda x: x.deadline)
    elif rule == "SPT":
        return sorted(orders, key=lambda x: get_order_duration(x, tps_dict))
    elif rule == "LPT":
        return sorted(orders, key=lambda x: get_order_duration(x, tps_dict), reverse=True)
    elif rule == "WSPT":
        return sorted(orders, key=lambda x: x.weight / max(1, get_order_duration(x, tps_dict)), reverse=True)
    return orders

# --- ОЦЕНКА РАСПИСАНИЯ (Часть 2, п.3) ---
def evaluate_schedule(schedule_items, orders_dict):
    total_weighted_fine = 0
    late_orders = set()
    max_tardiness = 0
    last_end_time = datetime.datetime.min

    for item in schedule_items:
        order = orders_dict.get(item.order_id)
        if not order:
            continue
            
        if item.end_time > last_end_time:
            last_end_time = item.end_time

        if item.end_time > order.deadline:
            tardiness = (item.end_time - order.deadline).total_seconds() / 3600.0
            total_weighted_fine += tardiness * order.fine * order.weight
            late_orders.add(order.id)
            if tardiness > max_tardiness:
                max_tardiness = tardiness

    return total_weighted_fine, len(late_orders), max_tardiness, last_end_time

# --- ПОСТРОЕНИЕ РАСПИСАНИЯ ---
def build_schedule(sorted_orders, machines, workers, tps_dict, ops_dict):
    result = []
    machine_busy = {m.id: [] for m in machines}
    worker_busy = {w.id: [] for w in workers}

    def is_free(busy_intervals, start, end):
        for s, e in busy_intervals:
            if start < e and end > s:
                return False
        return True

    for order in sorted_orders:
        op_ids = tps_dict.get(order.tp_id, [])
        current_time = order.date_start

        for op_id in op_ids:
            op = ops_dict.get(op_id)
            if not op:
                continue
            
            placed = False
            while not placed:
                end_time = current_time + datetime.timedelta(hours=op.duration)
                
                free_machine = next((m for m in machines if is_free(machine_busy[m.id], current_time, end_time)), None)
                free_worker = next((w for w in workers if is_free(worker_busy[w.id], current_time, end_time)), None)

                if free_machine and free_worker:
                    result.append(ScheduleItem(
                        order_id=order.id,
                        operation_id=op.id,
                        worker_id=free_worker.id,
                        machine_id=free_machine.id,
                        start_time=current_time,
                        end_time=end_time
                    ))
                    machine_busy[free_machine.id].append((current_time, end_time))
                    worker_busy[free_worker.id].append((current_time, end_time))
                    current_time = end_time
                    placed = True
                else:
                    current_time += datetime.timedelta(hours=1)
    return result

# --- ЭКСПОРТ В CSV (п.12, п.13) ---
def export_to_csv(schedule_items, orders_dict, ops_dict, resources_dict):
    sorted_items = sorted(schedule_items, key=lambda x: (x.order_id, x.start_time))
    
    # ИСПРАВЛЕННЫЙ ПУТЬ: сохраняем файл ровно туда, где лежит main.py
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.csv")
    
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(["Заказ", "Операция", "Сотрудник", "Станок", "Начало", "Окончание", "Просрочено"])
        
        for item in sorted_items:
            order = orders_dict.get(item.order_id)
            op_name = ops_dict.get(item.operation_id).name if item.operation_id in ops_dict else "?"
            worker_name = resources_dict.get(item.worker_id, "Нет")
            machine_name = resources_dict.get(item.machine_id, "Нет")
            
            is_late = "Да" if item.end_time > order.deadline else "Нет"
            
            writer.writerow([
                f"#{item.order_id}", op_name, worker_name, machine_name,
                item.start_time.strftime("%Y-%m-%d %H:%M"), 
                item.end_time.strftime("%Y-%m-%d %H:%M"), is_late
            ])
    print(f"Расписание выгружено в {file_path}")


class SchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Планировщик 3.0 (с БД)")
        self.root.geometry("650x600")

        self.load_data()

        tk.Label(root, text="Правило приоритета:").place(x=20, y=20)
        self.rule_var = tk.StringVar(value="FIFO")
        self.rule_combo = ttk.Combobox(root, textvariable=self.rule_var, state="readonly")
        self.rule_combo['values'] = ("FIFO", "EDD", "SPT", "LPT", "WSPT")
        self.rule_combo.place(x=150, y=20, width=100)

        self.btn_build = tk.Button(root, text="Рассчитать и сохранить", command=self.on_build)
        self.btn_build.place(x=270, y=18, width=180, height=25)

        self.listbox = tk.Listbox(root)
        self.listbox.place(x=20, y=60, width=600, height=150)

        self.metrics_text = tk.Text(root, height=3, width=70)
        self.metrics_text.place(x=20, y=220)

        self.canvas = tk.Canvas(root, bg="white", highlightthickness=0)
        self.canvas.place(x=20, y=290, width=600, height=250)

    def load_data(self):
        res_rows = database.get_resources()
        self.machines = [Resource(r[0], r[1], r[2]) for r in res_rows if r[2] is True]
        self.workers = [Resource(r[0], r[1], r[2]) for r in res_rows if r[2] is False]
        self.resources_dict = {r[0]: r[1] for r in res_rows}
        
        self.orders = []
        for o in database.get_orders():
            self.orders.append(Order(
                id=o['id'], order_date=o['order_date'], date_start=o['date_start'],
                deadline=o['deadline'], fine=o['fine'], tp_id=o['tp_id'], weight=o['weight']
            ))
        self.orders_dict = {o.id: o for o in self.orders}

        op_rows = database.get_all_operations()
        self.ops_dict = {r[0]: Operation(r[0], r[1], r[2]) for r in op_rows}

        self.tps_dict = {}
        for tp_id in set(o.tp_id for o in self.orders):
            self.tps_dict[tp_id] = database.get_operations_for_tp(tp_id)

    def on_build(self):
        self.listbox.delete(0, tk.END)
        rule = self.rule_var.get()
        
        sorted_orders = sort_orders(self.orders, rule, self.tps_dict)
        schedule = build_schedule(sorted_orders, self.machines, self.workers, self.tps_dict, self.ops_dict)
        
        db_items = []
        for item in schedule:
            db_items.append({
                'order_id': item.order_id,
                'operation_id': item.operation_id,
                'worker_id': item.worker_id,
                'machine_id': item.machine_id,
                'start_time': item.start_time,
                'end_time': item.end_time
            })
        database.save_schedule(db_items)
        
        for item in schedule:
            res_name = self.resources_dict.get(item.machine_id, "?")
            op_name = self.ops_dict.get(item.operation_id).name
            s = f"Заказ #{item.order_id} | {op_name} | {res_name} | {item.start_time.strftime('%H:%M')} - {item.end_time.strftime('%H:%M')}"
            self.listbox.insert(tk.END, s)

        fine, late_count, max_tard, end_time = evaluate_schedule(schedule, self.orders_dict)
        self.metrics_text.delete(1.0, tk.END)
        self.metrics_text.insert(tk.END, 
            f"Правило: {rule}\n"
            f"Суммарный взвешенный штраф: {fine:.2f}\n"
            f"Просрочено заказов: {late_count} | Макс. просрочка: {max_tard:.1f} ч.\n"
            f"Окончание последней операции: {end_time.strftime('%Y-%m-%d %H:%M')}"
        )

        export_to_csv(schedule, self.orders_dict, self.ops_dict, self.resources_dict)
        self.draw_gantt(schedule)

    def draw_gantt(self, schedule):
        self.canvas.delete("all")
        if not schedule: return
        
        min_time = min(item.start_time for item in schedule)
        max_time = max(item.end_time for item in schedule)
        
        colors = ["#6496ff", "#ff8c64", "#64ff8c", "#ff64c8", "#c864ff"]
        
        y_offset = 20
        for m in self.machines:
            self.canvas.create_text(10, y_offset + 10, anchor="w", text=m.name)
            
            m_items = [i for i in schedule if i.machine_id == m.id]
            for i, item in enumerate(m_items):
                delta_start = (item.start_time - min_time).total_seconds()
                delta_end = (item.end_time - min_time).total_seconds()
                total_span = (max_time - min_time).total_seconds()
                if total_span == 0: total_span = 1
                
                x1 = 150 + (delta_start / total_span) * 430
                x2 = 150 + (delta_end / total_span) * 430
                
                color = colors[item.order_id % len(colors)]
                self.canvas.create_rectangle(x1, y_offset, x2, y_offset + 20, fill=color, outline="black")
                self.canvas.create_text((x1+x2)/2, y_offset + 10, text=f"#{item.order_id}", font=("Arial", 7))
            
            y_offset += 40

if __name__ == "__main__":
    database.init_from_csv() 
    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()