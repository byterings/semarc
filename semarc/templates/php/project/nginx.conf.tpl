# Every request is handled by public/index.php in the php-fpm container (service "app").
server {
    listen 8000;
    server_name _;
    client_max_body_size 10m;

    location / {
        include fastcgi_params;
        fastcgi_pass app:9000;
        fastcgi_param SCRIPT_FILENAME /app/public/index.php;
        fastcgi_param SCRIPT_NAME /index.php;
        fastcgi_param HTTP_AUTHORIZATION $http_authorization;
    }
}
