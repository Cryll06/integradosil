
FROM python:3.10-bullseye

ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    curl \
    unzip \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

ENV ORACLE_CLIENT_DIR=/opt/oracle/instantclient_21_12
ENV LD_LIBRARY_PATH=$ORACLE_CLIENT_DIR

RUN mkdir -p $ORACLE_CLIENT_DIR

RUN curl -o instantclient-basic-linux.x64-21.12.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-basic-linux.x64-21.12.0.0.0dbru.zip && \
    curl -o instantclient-sdk-linux.x64-21.12.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/2112000/instantclient-sdk-linux.x64-21.12.0.0.0dbru.zip

RUN unzip instantclient-basic-linux.x64-21.12.0.0.0dbru.zip -d $ORACLE_CLIENT_DIR && \
    unzip instantclient-sdk-linux.x64-21.12.0.0.0dbru.zip -d $ORACLE_CLIENT_DIR


RUN mv $ORACLE_CLIENT_DIR/instantclient_21_12/* $ORACLE_CLIENT_DIR/
RUN rmdir $ORACLE_CLIENT_DIR/instantclient_21_12

RUN rm instantclient-basic-linux.x64-21.12.0.0.0dbru.zip instantclient-sdk-linux.x64-21.12.0.0.0dbru.zip

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python wait_for_db.py && python manage.py makemigrations calificaciones && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]