cd G:\serviceos
$env:ALLOWED_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 *>> G:\serviceos\db\backend_restart2.log
