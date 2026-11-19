FROM php:8.3-fpm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install pdo_mysql pdo_pgsql opcache \
    && rm -rf /var/lib/apt/lists/* \
    && mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && sed -i 's/^;clear_env = no/clear_env = no/' /usr/local/etc/php-fpm.d/www.conf

WORKDIR /app
COPY . .
RUN mkdir -p storage && chown -R www-data:www-data storage

# php-fpm listens on 9000; the nginx service in docker-compose.yml serves HTTP.
EXPOSE 9000
CMD ["sh", "-c", "php bin/migrate.php && chown -R www-data:www-data storage && php-fpm"]
