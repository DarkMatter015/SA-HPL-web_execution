FROM python:3.14.5-slim

WORKDIR /usr/local/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# TODO: change to gunicorn instead runserver
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]