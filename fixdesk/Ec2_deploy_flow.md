git pull
source Env/bin/activate
pip install -r requirements.txt
python manage.py migrate
sudo supervisorctl restart guni: