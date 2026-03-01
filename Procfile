web: cd flask_app && playwright install chromium && python -c "import os; os.system(f'gunicorn app:app --bind 0.0.0.0:{os.environ.get(\"PORT\", 5000)} --timeout 120 --workers 1 --threads 4')"
