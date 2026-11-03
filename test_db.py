import database

print("--- ЗАПУСК ИНИЦИАЛИЗАЦИИ ---")
database.init_from_csv() 

print("\n--- ПРОВЕРКА ДАННЫХ ИЗ БАЗЫ ---")
print("Ресурсы в базе:")
for r in database.get_resources():
    print(r)

print("\nЗаказы в базе (первые 3):")
for o in database.get_orders()[:3]:
    print(o)