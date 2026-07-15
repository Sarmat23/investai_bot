FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Директория для персистентных данных (SQLite и т.д.). Смонтируйте сюда
# внешний том при запуске — иначе данные исчезнут при пересоздании контейнера.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

CMD ["python", "main.py"]
