FROM python:latest
COPY . .
RUN pip3 install -U -r requirements.txt && pip3 install -U pip
CMD python3 main.py
