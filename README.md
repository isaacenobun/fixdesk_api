# helpdesk_api
Api for IT Helpdesk

#####
uvicorn helpdesk.asgi:application --reload

gcloud app deploy app.yaml
gcloud app logs tail -s default