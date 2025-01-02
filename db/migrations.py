# Инициализация alembic
import os
# from db.config import DATABASE_URL
# os.system("alembic init alembic")

# Настройка alembic.ini
# with open("alembic.ini", "r") as f:
#     config = f.read()
# config = config.replace("sqlalchemy.url = ", f"sqlalchemy.url = {DATABASE_URL}")
# with open("alembic.ini", "w") as f:
#     f.write(config)

# Создание миграции
os.system('alembic revision --autogenerate -m "Первая миграция"')

# Применение миграции
os.system("alembic upgrade head")