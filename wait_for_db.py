import time
import os
import psycopg2
from psycopg2 import OperationalError

print("Esperando a PostgreSQL...")

db_name = os.environ.get('DB_NAME')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_port = os.environ.get('DB_PORT')

while True:
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.close()
        print("¡PostgreSQL está listo!")
        break
    except OperationalError as e:
        print(f"PostgreSQL no está listo todavía... reintentando ({e})")
        time.sleep(1)