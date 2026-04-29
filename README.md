# Smartify - Developer Customer Music App



## Customer Flow
1. Customer registers account.
2. Customer logs in.
3. Customer listens to uploaded songs, likes songs, and checks history.

## Developer Flow
1. Login with admin/admin123.
2. Go to Developer Panel.
3. Upload songs with title, artist, mood and optional cover image.
4. Customers can see the songs on Home.

## Local Run
```bash
pip install -r requirements.txt
python app.py
```

Open:
http://127.0.0.1:8000

## Render Deploy
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

Environment variables optional:
SECRET_KEY=any_random_secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
