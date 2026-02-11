FROM postgres:15

# Install HypoPG extension
RUN apt-get update \
    && apt-get install -y postgresql-15-hypopg \
    && rm -rf /var/lib/apt/lists/*
