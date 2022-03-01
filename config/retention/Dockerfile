FROM python:3.8-slim
WORKDIR /usr/src/ret
ADD . /usr/src/ret/
RUN pip install -r req.txt
CMD [ "python", "./dump.py" ]

