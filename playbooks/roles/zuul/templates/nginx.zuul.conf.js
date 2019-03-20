upstream scheduler {
    server scheduler:8001
}

upstream web {
    server web:9000
}

server {
    listen       80;
    server_name  {{ zuul_servername }};

    access_log  /var/log/nginx/zuul.access.log main;

    location / {
        root   /usr/share/nginx/html;
        index  index.html;
    }

    location ~ ^/keys/(.*) {
        proxy_pass http://scheduler/opencontrail/keys/$1;
    }

    location /status.json {
        proxy_pass http://scheduler/opencontrail/status.json;
    }

    location ~ ^/status/(.*) {
        proxy_pass http://scheduler/opencontrail/status/$1;
    }

    location /console-stream {
        proxy_pass ws://web/console-stream;
    }

    location ~ ^/static/(.*) {
        proxy_pass http://web/static/$1;
    }

    location ~ ^/jobs/(.*) {
        proxy_pass http://web/jobs/$1;
    }
}