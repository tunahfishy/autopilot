FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install playwright
RUN playwright install

COPY . /app

CMD ["python", "main.py"]