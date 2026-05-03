import sqlite3, os

# DBファイルを探す
db_paths = ['buildee.db', 'data/buildee.db', 'instance/buildee.db']
db_path = None
for p in db_paths:
    if os.path.exists(p):
        db_path = p
        break

companies = [
    ('1',  'OKR',        'その他'),
    ('2',  'Ops',        'その他'),
    ('3',  'TKSL',       'その他'),
    ('4',  'WHS',        'その他'),
    ('5',  'ザイマックス', 'その他'),
    ('6',  'その他',      'その他'),
    ('7',  'ユアサ',      'その他'),
    ('8',  'リョウセイ',   'その他'),
    ('9',  '丸和工業',    'その他'),
    ('10', '日本ビルコン', 'その他'),
]

if not db_path:
    print('DBが見つかりません。アプリ起動時に自動登録されます。')
else:
    conn = sqlite3.connect(db_path)
    conn.execute('DELETE FROM companies')
    conn.executemany('INSERT INTO companies(id,name,type) VALUES (?,?,?)', companies)
    conn.commit()
    rows = conn.execute('SELECT id, name FROM companies ORDER BY CAST(id AS INTEGER)').fetchall()
    print('✅ 会社リストを更新しました:')
    for r in rows:
        print(f'  {r[0]:>2}: {r[1]}')
    conn.close()
