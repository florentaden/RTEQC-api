FROM python:3.9-slim
WORKDIR /code
RUN apt-get -y update
COPY ./requirements.txt /code/requirements.txt 
RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./rteqc_api.py /code/rteqc_api.py
EXPOSE 8000
CMD ["fastapi",  "run", "/code/rteqc_api.py", "--host", "0.0.0.0", "--port", "8000"]

