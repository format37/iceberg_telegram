FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir
COPY 1c.json /server
COPY onec_request.py /server
COPY server.py /server
CMD ["uvicorn", \
    "server:app", \
    "--host", "0.0.0.0", \
    "--port", "7403", \
    "--ssl-keyfile=/cert/privkey.pem", \
    "--ssl-certfile=/cert/fullchain.pem"\
    ]