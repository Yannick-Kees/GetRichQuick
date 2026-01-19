FROM python:3.10.14-slim-bullseye   

WORKDIR /python-docker
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

COPY . .

CMD ["sh", "-c", "make install && make run"]
