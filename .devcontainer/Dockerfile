FROM python:3.8

# Install MySQL development libraries
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    python3-dev

RUN pip install --upgrade pip

WORKDIR /workspaces/berghain

CMD ["/bin/bash", "-c", "while true; do sleep 30; done"]
