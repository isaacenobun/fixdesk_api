[Unit]
Description=Celery Service
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/fixdesk_api/fixdesk
Environment="PATH=/home/ubuntu/fixdesk_api/Env/bin"
ExecStart=/home/ubuntu/fixdesk_api/Env/bin/celery \
          -A fixdesk worker \
          --loglevel=info \
          --concurrency=4

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
