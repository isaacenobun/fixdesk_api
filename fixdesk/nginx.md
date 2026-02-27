[program:gunicorn]
directory=/home/ubuntu/fixdesk_api/fixdesk
command=/home/ubuntu/fixdesk_api/Env/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/fixdesk_api/fixdesk/app.sock fixdesk.wsgi:application  
autostart=true
autorestart=true
stderr_logfile=/var/log/gunicorn/gunicorn.err.log
stdout_logfile=/var/log/gunicorn/gunicorn.out.log

[group:guni]
programs:gunicorn


server{

	listen 80;
	server_name ;

	
	location / {

		include proxy_params;
		proxy_pass http://unix:/home/ubuntu/fixdesk_api/fixdesk/app.sock;

	}

}