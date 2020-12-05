FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt /tmp
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENTRYPOINT [ "python", "./transcript.py" ]
