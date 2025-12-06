import time
import os
import cx_Oracle as oracledb 
import sys

print("Iniciando script wait_for_db.py")


db_user = os.environ.get('APP_USER')
db_password = os.environ.get('APP_USER_PASSWORD')
db_dsn = "db:1521/XEPDB1"

connection_ready = False
start_time = time.time()


while not connection_ready:
    try:

        oracledb.connect(user=db_user, password=db_password, dsn=db_dsn)
        connection_ready = True
        print("Conexión a la base de datos Oracle exitosa")
    except Exception as e:
        print(f"Base de datos no está lista... reintentando en 5 segundos. Error: {e}")
       
        if time.time() - start_time > 300: 
            print("Error: Se superó el tiempo de espera para la base de datos")
            sys.exit(1)
        time.sleep(5)