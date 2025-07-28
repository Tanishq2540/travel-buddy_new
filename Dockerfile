
FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt


ENV PORT 8080
EXPOSE 8080

CMD ["python", "main.py"]
