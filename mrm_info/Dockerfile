FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir
COPY sample.jpg /server
COPY server.py /server
# CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7405"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0"]