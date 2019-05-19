FROM python:3.6.7

WORKDIR /app

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python && \
    /root/.poetry/bin/poetry config settings.virtualenvs.create false
COPY ./poetry.lock ./pyproject.toml /app/
RUN /root/.poetry/bin/poetry install -n

COPY . /app/
