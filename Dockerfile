FROM python:3.12-slim-bullseye

RUN apt-get update && \
    apt-get install -y openssh-server sqlite3 libsqlite3-dev

RUN mkdir /var/run/sshd

COPY sshd_config /etc/ssh/sshd_config

RUN useradd -m -s /app/app.sh mist && \
    echo 'mist:password' | chpasswd

COPY pyproject.toml poetry.lock ./

RUN pip install -U poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main

COPY app /app

RUN chown mist:mist /app

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
