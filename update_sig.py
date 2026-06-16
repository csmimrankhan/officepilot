import sys
sys.path.insert(0, '.')
from app.db import SessionLocal
from sqlalchemy import text
sig = sys.argv[1]
db = SessionLocal()
db.execute(text('UPDATE app_releases SET updater_signature = :sig WHERE version = :ver'), {'sig': sig, 'ver': '0.36.1'})
db.commit()
row = db.execute(text('SELECT version, updater_signature FROM app_releases WHERE version = :ver'), {'ver': '0.36.1'}).fetchone()
print(f'Updated: version={row[0]}, sig_len={len(row[1])}')
db.close()
