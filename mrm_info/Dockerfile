FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir
RUN pip3 install gunicorn==21.2.0
COPY server.py /server
# CMD ["uvicorn", "server:app", "--host", "0.0.0.0"]
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker your_fastapi_app:app
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "server:app"]
# With host 0.0.0.0
# CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "server:app"]
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "server:app"]
