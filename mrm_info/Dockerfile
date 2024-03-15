FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir
RUN pip3 install gunicorn==21.2.0
COPY config.json /server
COPY 1c.json /server
COPY *.py /server
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300", "server:app"]
