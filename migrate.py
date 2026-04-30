# =============================================================
#  migrate.py — data.json → buildee.db 移行スクリプト
#  使い方: python migrate.py
# =============================================================
import json, os, sys, shutil
from datetime import datetime
import database as db

DATA_FILE = 'data.json'
DB_PATH   = 'buildee.db'

def migrate():
    print("=" * 50)
    print("  BuildeeMgr — JSON → SQLite 移行ツール")
    print("=" * 50)

    # ① DB初期化
    print("\n[1/7] データベースを初期化...")
    db.init_db()
    print(f"      ✓ {DB_PATH} を作成しました")

    # data.json が無ければスキップ
    if not os.path.exists(DATA_FILE):
        print(f"\n[INFO] {DATA_FILE} が見つかりません。サンプルデータのみで起動します。")
        print("\n✅ 移行完了（新規DB）")
        return

    # ② data.json を読み込む
    print(f"\n[2/7] {DATA_FILE} を読み込み...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"      ✓ 読み込み完了")

    # ③ 会社
    companies = data.get('companies', [])
    print(f"\n[3/7] 協力会社 {len(companies)} 件を移行...")
    ok = 0
    for c in companies:
        try:
            db.add_company(c['id'], c['name'], c.get('type', ''))
            ok += 1
        except Exception as e:
            print(f"      ⚠ SKIP {c.get('name')}: {e}")
    print(f"      ✓ {ok} 件移行")

    # ④ 作業予定
    schedules = data.get('work_schedules', [])
    print(f"\n[4/7] 作業予定 {len(schedules)} 件を移行...")
    ok = 0
    for s in schedules:
        try:
            db.add_schedule(s)
            ok += 1
        except Exception as e:
            print(f"      ⚠ SKIP {s.get('id', '?')}: {e}")
    print(f"      ✓ {ok} 件移行")

    # ⑤ 揚重機予約
    equips = data.get('equipment_reservations', [])
    print(f"\n[5/7] 揚重機予約 {len(equips)} 件を移行...")
    ok = 0
    for e in equips:
        try:
            db.add_equipment(e)
            ok += 1
        except Exception as e:
            print(f"      ⚠ SKIP {e}")
    print(f"      ✓ {ok} 件移行")

    # ⑥ KY記録
    ky_records = data.get('ky_records', [])
    print(f"\n[6/7] KY記録 {len(ky_records)} 件を移行...")
    ok = 0
    for k in ky_records:
        try:
            db.add_ky(k)
            if k.get('status') == '承認済':
                db.approve_ky(k['id'])
            ok += 1
        except Exception as e:
            print(f"      ⚠ SKIP {k.get('id', '?')}: {e}")
    print(f"      ✓ {ok} 件移行")

    # ⑦ 作業員
    workers = data.get('workers', [])
    print(f"\n[7/7] 作業員 {len(workers)} 件を移行...")
    ok = 0
    for w in workers:
        try:
            db.add_worker(w)
            ok += 1
        except Exception as e:
            print(f"      ⚠ SKIP {w.get('name', '?')}: {e}")
    print(f"      ✓ {ok} 件移行")

    # ⑧ 入退場記録（worker_id が DB に存在する場合のみ）
    attendance = data.get('attendance', [])
    if attendance:
        print(f"\n[+] 入退場記録 {len(attendance)} 件を移行...")
        ok = 0
        import uuid
        conn = db.get_conn()
        for a in attendance:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO attendance
                        (id, worker_id, date, checkin_time, checkout_time)
                    VALUES (?,?,?,?,?)
                """, (
                    a.get('id', str(uuid.uuid4())),
                    a['worker_id'], a['date'],
                    a.get('checkin_time'), a.get('checkout_time')
                ))
                ok += 1
            except Exception as e:
                print(f"      ⚠ SKIP: {e}")
        conn.commit()
        conn.close()
        print(f"      ✓ {ok} 件移行")

    # バックアップ
    backup = DATA_FILE + '.bak'
    shutil.copy2(DATA_FILE, backup)
    print(f"\n✅ 移行完了！  バックアップ → {backup}")
    print(f"   DBファイル  → {DB_PATH}")
    print(f"\n   ※ 問題があれば {backup} から再移行できます\n")

if __name__ == '__main__':
    migrate()
