FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN mkdir -p /app/uploads && chmod -R 776 /app/uploads
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "run.py"]