FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SECRET_KEY=canvia-aquesta-clau

EXPOSE 5000

CMD ["waitress-serve", "--port=5000", "app:app"]
