FROM python:3.10-slim-buster
WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt --no-cache-dir
COPY webhook_cert.pem /app
COPY webhook_pkey.pem /app
# COPY Telegram_phoneConfirmation.py /app
# COPY iceberg.py /app
COPY server.py /app
# ENTRYPOINT ["python"]
# CMD ["server.py"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-keyfile=webhook_pkey.pem", "--ssl-certfile=webhook_cert.pem"]