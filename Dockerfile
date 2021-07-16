FROM python:3
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt update && apt install -y gdal-bin python-gdal python3-gdal
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/
