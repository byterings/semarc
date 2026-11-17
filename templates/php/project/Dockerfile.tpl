FROM php:8.3-cli

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install pdo_mysql pdo_pgsql \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN mkdir -p storage

EXPOSE 8000
CMD ["sh", "-c", "php bin/migrate.php && php -S 0.0.0.0:8000 -t public public/index.php"]
