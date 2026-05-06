# =============================================================
#  app.py -- BuildeeMgr Flask (SQLite + Excel + QR + Auth + HTTPS)
# =============================================================
from flask import (Flask, render_template, request, jsonify,
                   send_file, redirect, url_for, flash)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, date
from functools import wraps
import uuid, io, threading

# ---- Config first (loads .env) ----
import config as cfg
C = cfg.Config

import database as db
import excel_export as xls
import qr_utils as qr
import auth
import notifier
import mail_utils as mu
import backup_utils as bu
import certbot_manager as cbm

# =============================================================
#  Flask app
# =============================================================
app = Flask(__name__)

# ProxyFix: Nginx リバースプロキシ下で X-Forwarded-* を正しく解釈
# x_for=1, x_proto=1 → Nginx 1段のみ信頼（セキュリティ上重要）
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key                        = C.SECRET_KEY
app.config['SESSION_COOKIE_SECURE']   = C.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = C.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = C.SESSION_COOKIE_SAMESITE
app.config['PERMANENT_SESSION_LIFETIME'] = C.PERMANENT_SESSION_LIFETIME

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view             = 'login_page'
login_manager.login_message          = 'ログインが必要です'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(uid):
    return auth.get_user_by_id(uid)

# DB init
with app.app_context():
    db.init_db()
    auth.init_auth_db()
    notifier.init_notification_db()
    bu.init_backup_db()
    cbm.init_cert_log_db()
    notifier.start_daily_scheduler()

# =============================================================
#  Security headers + HTTPS redirect
# =============================================================
@app.before_request
def enforce_https():
    """Redirect plain HTTP to HTTPS when HTTP_REDIRECT is enabled."""
    if not C.HTTPS_ENABLED or not C.HTTP_REDIRECT:
        return
    # Already HTTPS (X-Forwarded-Proto set by reverse proxy, or direct SSL)
    proto = request.headers.get('X-Forwarded-Proto', '')
    if proto == 'https':
        return
    # Running directly under SSL — scheme == 'https'
    if request.scheme == 'https':
        return
    # Redirect
    https_url = request.url.replace('http://', 'https://', 1)
    # Adjust port: replace :HTTP_PORT with :HTTPS_PORT if present
    if f':{C.HTTP_PORT}' in https_url:
        https_url = https_url.replace(f':{C.HTTP_PORT}', f':{C.HTTPS_PORT}', 1)
    return redirect(https_url, code=301)


@app.after_request
def add_security_headers(response):
    """Add security + PWA headers to every response."""

    # HSTS (only over HTTPS)
    if C.HTTPS_ENABLED and request.scheme == 'https':
        hsts = f"max-age={C.HSTS_MAX_AGE}; includeSubDomains" \
               if C.HSTS_SUBDOMAINS else f"max-age={C.HSTS_MAX_AGE}"
        response.headers['Strict-Transport-Security'] = hsts

    # CSP — allow self + CDN used by the app
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "style-src  'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "font-src   'self' https://cdnjs.cloudflare.com; "
        "img-src    'self' data: blob:; "
        "connect-src 'self'; "
        "media-src  'self' blob:; "
        "frame-ancestors 'none';"
    )
    response.headers['Content-Security-Policy'] = csp

    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options']        = 'DENY'
    response.headers['X-XSS-Protection']       = '1; mode=block'
    response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']      = (
        'camera=(self), microphone=(), geolocation=()'
    )

    # PWA / Service Worker
    if request.path == '/static/js/sw.js':
        response.headers['Service-Worker-Allowed'] = '/'
        response.headers['Cache-Control']           = 'no-cache'
    if request.path == '/static/manifest.json':
        response.headers['Cache-Control'] = 'no-cache'

    return response

# =============================================================
#  Role decorators
# =============================================================
def write_required(f):
    @wraps(f)
    @login_required
    def dec(*a, **kw):
        if not current_user.can_write():
            if request.path.startswith('/api/'):
                return jsonify({'error': 'forbidden'}), 403
            flash('書き込み権限がありません', 'error')
            return redirect(url_for('index'))
        return f(*a, **kw)
    return dec

def admin_required(f):
    @wraps(f)
    @login_required
    def dec(*a, **kw):
        if not current_user.is_admin():
            if request.path.startswith('/api/'):
                return jsonify({'error': 'forbidden'}), 403
            flash('管理者権限が必要です', 'error')
            return redirect(url_for('index'))
        return f(*a, **kw)
    return dec

# =============================================================
#  Auth pages
# =============================================================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = auth.verify_password(username, password)
        if user:
            login_user(user, remember=remember)
            auth.log_login(user.id, username, 'login', request.remote_addr, True)
            return redirect(request.args.get('next') or url_for('index'))
        auth.log_login(None, username, 'login_fail', request.remote_addr, False)
        flash('ユーザー名またはパスワードが正しくありません', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    auth.log_login(current_user.id, current_user.username,
                   'logout', request.remote_addr, True)
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('login_page'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        cp = request.form.get('current_password', '')
        np = request.form.get('new_password', '')
        cf = request.form.get('confirm_password', '')
        if not auth.verify_password(current_user.username, cp):
            flash('現在のパスワードが正しくありません', 'error')
        elif np != cf:
            flash('新しいパスワードが一致しません', 'error')
        else:
            ok, msg = auth.change_password(current_user.id, np)
            if ok:
                flash('パスワードを変更しました', 'success')
                return redirect(url_for('index'))
            flash(msg, 'error')
    return render_template('change_password.html')

# =============================================================
#  Admin — user management
# =============================================================
#  Admin pages
# =============================================================
@app.route('/admin/notifications')
@admin_required
def admin_notifications():
    return render_template('admin_notifications.html')

@app.route('/admin/cert')
@admin_required
def admin_cert():
    return render_template('admin_cert.html')


@app.route('/admin/users')
@admin_required
def admin_users():
    import cert_utils
    return render_template('admin_users.html',
                           users=auth.get_all_users(),
                           log=auth.get_login_log(30),
                           role_labels=auth.ROLE_LABELS,
                           cert_info=cert_utils.get_cert_info(),
                           https_enabled=C.HTTPS_ENABLED)

@app.route('/api/admin/users',          methods=['GET'])
@admin_required
def api_list_users():
    return jsonify(auth.get_all_users())

@app.route('/api/admin/users',          methods=['POST'])
@admin_required
def api_create_user():
    d = request.json
    uid, err = auth.create_user(d['username'], d['display_name'], d['password'],
                                d.get('role','viewer'), d.get('company',''))
    return (jsonify({'status':'ok','id':uid}), 201) if uid \
        else (jsonify({'status':'error','message':err}), 400)

@app.route('/api/admin/users/<uid>',    methods=['PUT'])
@admin_required
def api_update_user(uid):
    return jsonify({'status':'ok'}) if auth.update_user(uid, request.json) \
        else (jsonify({'status':'not found'}), 404)

@app.route('/api/admin/users/<uid>',    methods=['DELETE'])
@admin_required
def api_delete_user(uid):
    ok, err = auth.delete_user(uid)
    return jsonify({'status':'ok'}) if ok \
        else (jsonify({'status':'error','message':err}), 400)

@app.route('/api/admin/users/<uid>/reset-password', methods=['POST'])
@admin_required
def api_reset_password(uid):
    ok, err = auth.change_password(uid, request.json.get('password',''))
    return jsonify({'status':'ok'}) if ok \
        else (jsonify({'status':'error','message':err}), 400)

@app.route('/api/admin/cert-info')
@admin_required
def api_cert_info():
    return jsonify(cbm.get_all_cert_status())

@app.route('/api/admin/cert-regenerate', methods=['POST'])
@admin_required
def api_cert_regen():
    import cert_utils
    try:
        cert_utils.generate_self_signed()
        return jsonify({'status': 'ok', 'message': '自己署名証明書を再生成しました。再起動後に有効になります。'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Let's Encrypt API
@app.route('/api/admin/certbot/status', methods=['GET'])
@admin_required
def api_certbot_status():
    return jsonify(cbm.get_all_cert_status())

@app.route('/api/admin/certbot/renew', methods=['POST'])
@admin_required
def api_certbot_renew():
    body    = request.json or {}
    dry_run = bool(body.get('dry_run', False))
    result  = cbm.run_certbot_renew(dry_run=dry_run)
    cbm.log_cert_action('renew', result)
    return jsonify(result), (200 if result.get('success') else 500)

@app.route('/api/admin/certbot/obtain', methods=['POST'])
@admin_required
def api_certbot_obtain():
    body    = request.json or {}
    domain  = body.get('domain', '').strip()
    email   = body.get('email', '').strip()
    staging = bool(body.get('staging', False))
    if not domain or not email:
        return jsonify({'error': 'domain と email は必須です'}), 400
    result = cbm.run_certbot_obtain(domain, email, staging=staging)
    cbm.log_cert_action('obtain', result)
    return jsonify(result), (200 if result.get('success') else 500)

@app.route('/api/admin/certbot/nginx-reload', methods=['POST'])
@admin_required
def api_nginx_reload():
    ok, msg = cbm.reload_nginx()
    return jsonify({'success': ok, 'message': msg}), (200 if ok else 500)

@app.route('/api/admin/certbot/log', methods=['GET'])
@admin_required
def api_certbot_log():
    return jsonify(cbm.get_cert_renewal_log(30))

# =============================================================
#  Pages
# =============================================================
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.route('/export')
@login_required
def export_page():
    return render_template('export.html')

@app.route('/qr-gate')
@login_required
def qr_gate():
    return render_template('qr_gate.html', today=date.today().isoformat())

@app.route('/coordination')
@login_required
def coordination():
    return render_template('coordination.html',
                           companies=db.get_companies(), today=date.today().isoformat())


@app.route('/floorplan')
@login_required
def floorplan():
    return render_template('floorplan.html')

@app.route('/input')
@login_required
def input_page():
    companies = db.get_companies()
    today = date.today().isoformat()
    return render_template('input.html', companies=companies, today=today)

@app.route('/stepmap')
@login_required
def stepmap():
    today = date.today().isoformat()
    companies = db.get_companies()
    return render_template('stepmap.html', today=today, companies=companies)

@app.route('/daily-report')
@login_required
def daily_report():
    today = date.today().isoformat()
    return render_template('daily_report.html', today=today)

@app.route('/api/daily-report-data')
@login_required
def api_daily_report_data():
    """日報用データ: 当日・翌日の作業予定+累計人数"""
    from datetime import date as dt, timedelta
    target = request.args.get('date', dt.today().isoformat())
    next_day = (dt.fromisoformat(target) + timedelta(days=1)).isoformat()

    today_sch  = db.get_schedules(target)
    next_sch   = db.get_schedules(next_day)

    # 累計人数（全期間の workers_count 合計）
    with db.get_conn() as conn:
        prev_total = conn.execute(
            "SELECT COALESCE(SUM(workers_count),0) FROM work_schedules WHERE date < ?",
            (target,)
        ).fetchone()[0]
        today_total = sum(s['workers_count'] for s in today_sch)

    return jsonify({
        'date': target,
        'next_date': next_day,
        'today_schedules': today_sch,
        'next_schedules': next_sch,
        'today_count': today_total,
        'prev_cumulative': int(prev_total),
        'cumulative': int(prev_total) + today_total,
    })


@app.route('/ky')
@login_required
def ky():
    return render_template('ky.html',
                           ky_records=db.get_ky_records(), companies=db.get_companies())

@app.route('/safety')
@login_required
def safety():
    return render_template('safety.html', workers=db.get_workers(),
                           companies=db.get_companies(), docs=db.get_safety_docs())

@app.route('/attendance')
@login_required
def attendance():
    today = date.today().isoformat()
    return render_template('attendance.html', attendance=db.get_attendance(today),
                           workers=db.get_workers(), companies=db.get_companies(), today=today)

# =============================================================
#  API — me / export / QR / schedules / equipment / KY /
#         workers / safety_docs / attendance / dashboard / companies
# =============================================================
@app.route('/api/me')
@login_required
def api_me():
    return jsonify(current_user.to_dict())

# --- Export ---
@app.route('/api/export', methods=['POST'])
@login_required
def api_export():
    body = request.json or {}
    try:
        xlsx = xls.build_excel(body.get('sheets',['all']), body.get('date'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    label = '_'.join(body.get('sheets',['all']))
    fname = f"BuildeeMgr_{label}_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(io.BytesIO(xlsx),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=fname)

@app.route('/api/export/quick/<sn>', methods=['GET'])
@login_required
def api_export_quick(sn):
    if sn not in {'all','schedules','equipment','ky','workers','attendance','safety_docs'}:
        return jsonify({'error':'invalid sheet'}), 400
    try:
        xlsx = xls.build_excel([sn], request.args.get('date'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return send_file(io.BytesIO(xlsx),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"BuildeeMgr_{sn}_{date.today().strftime('%Y%m%d')}.xlsx")

# --- QR ---
@app.route('/api/qr/worker/<wid>')
@login_required
def api_qr_get(wid):
    try:    return jsonify({'status':'ok', **qr.ensure_worker_qr(wid)})
    except ValueError as e: return jsonify({'status':'not found','message':str(e)}), 404

@app.route('/api/qr/worker/<wid>/regenerate', methods=['POST'])
@write_required
def api_qr_regen(wid):
    try:    return jsonify({'status':'ok', **qr.regenerate_worker_qr(wid)})
    except ValueError as e: return jsonify({'status':'not found','message':str(e)}), 404

@app.route('/api/qr/scan', methods=['POST'])
@login_required
def api_qr_scan():
    body = request.json or {}
    raw  = body.get('payload','').strip()
    att_date = body.get('date', date.today().isoformat())
    try:   worker_id, token = qr.parse_qr_payload(raw)
    except ValueError: return jsonify({'status':'error','message':'無効なQRコードです'}), 400
    worker = db.get_worker_by_qr(token)
    if not worker or worker['id'] != worker_id:
        return jsonify({'status':'error','message':'QRコードが無効または期限切れです'}), 401
    current = db.get_current_status(worker_id, att_date)
    now_str = datetime.now().strftime('%H:%M')
    if current and not current.get('checkout_time'):
        db.checkout(worker_id, att_date, method='qr'); action = 'checkout'
        msg = f"{worker['name']} さん、退場しました（{now_str}）"
    else:
        db.checkin(worker_id, att_date, str(uuid.uuid4()), method='qr'); action = 'checkin'
        msg = f"{worker['name']} さん、入場しました（{now_str}）"
    # 通知: QR入退場
    notifier.notify_attendance(dict(worker), action, att_date, now_str)
    return jsonify({'status':'ok','action':action,'message':msg,
        'worker':{'id':worker['id'],'name':worker['name'],
                  'company':worker['company'],'job':worker.get('job',''),'ccus':worker.get('ccus','')},
        'time':now_str,'date':att_date})

@app.route('/api/qr/bulk-generate', methods=['POST'])
@write_required
def api_qr_bulk():
    workers = db.get_workers()
    gen = sum(1 for w in workers if not w.get('qr_token') and qr.ensure_worker_qr(w['id']))
    return jsonify({'status':'ok','generated':gen,'total':len(workers)})

# --- Schedules ---
@app.route('/api/schedules',       methods=['GET'])
@login_required
def api_get_schedules(): return jsonify(db.get_schedules(request.args.get('date')))

@app.route('/api/schedules/floor/<floor>', methods=['GET'])
@login_required
def api_get_schedules_floor(floor):
    return jsonify(db.get_schedules_by_floor(floor))

@app.route('/api/schedules',       methods=['POST'])
@write_required
def api_add_schedule():
    s=request.json; s['id']=str(uuid.uuid4()); db.add_schedule(s)
    return jsonify({'status':'ok','id':s['id']}), 201

@app.route('/api/schedules/<sid>', methods=['PUT'])
@write_required
def api_upd_schedule(sid):
    return jsonify({'status':'ok'}) if db.update_schedule(sid,request.json) \
        else (jsonify({'status':'not found'}),404)

@app.route('/api/schedules/<sid>', methods=['DELETE'])
@write_required
def api_del_schedule(sid):
    db.delete_schedule(sid); return jsonify({'status':'ok'})

# --- Equipment ---

# --- Equipment ---
@app.route('/api/equipment',       methods=['GET'])
@login_required
def api_get_equip(): return jsonify(db.get_equipment(request.args.get('date')))

@app.route('/api/equipment',       methods=['POST'])
@write_required
def api_add_equip():
    r=request.json
    r['id']=str(uuid.uuid4()); db.add_equipment(r)
    return jsonify({'status':'ok','id':r['id']}),201
    return jsonify({'status':'ok','id':r['id']}),201

@app.route('/api/equipment/<eid>', methods=['PUT'])
@write_required
def api_update_equip(eid):
    data = request.get_json() or {}
    db.update_equipment(eid, data)
    return jsonify({'status':'ok'})

@app.route('/api/equipment/<eid>', methods=['DELETE'])
@write_required
def api_del_equip(eid):
    db.delete_equipment(eid); return jsonify({'status':'ok'})

# --- KY ---
# --- KY ---
@app.route('/api/ky',              methods=['GET'])
@login_required
def api_get_ky():
    return jsonify(db.get_ky_records(request.args.get('date'),request.args.get('status')))

@app.route('/api/ky',              methods=['POST'])
@write_required
def api_add_ky():
    r=request.json; r['id']=str(uuid.uuid4()); db.add_ky(r)
    return jsonify({'status':'ok','id':r['id']}),201

@app.route('/api/ky/<kid>/approve',methods=['PUT'])
@write_required
def api_approve_ky(kid):
    if not db.approve_ky(kid):
        return jsonify({'status': 'not found'}), 404
    # 通知: KY承認
    ky_records = db.get_ky_records()
    ky = next((r for r in ky_records if r.get('id') == kid), {})
    notifier.notify_ky_approved(kid, ky, current_user.display_name)
    return jsonify({'status': 'ok'})

# --- Workers ---
@app.route('/api/workers',         methods=['GET'])
@login_required
def api_get_workers(): return jsonify(db.get_workers(request.args.get('company')))

@app.route('/api/workers',         methods=['POST'])
@write_required
def api_add_worker():
    w=request.json; w['id']=str(uuid.uuid4()); db.add_worker(w)
    return jsonify({'status':'ok','id':w['id']}),201

@app.route('/api/workers/<wid>',   methods=['DELETE'])
@write_required
def api_del_worker(wid):
    db.delete_worker(wid); return jsonify({'status':'ok'})

# --- Safety docs ---
@app.route('/api/safety_docs',     methods=['GET'])
@login_required
def api_get_sdocs(): return jsonify(db.get_safety_docs())

@app.route('/api/safety_docs',     methods=['POST'])
@write_required
def api_add_sdoc():
    d=request.json; d['id']=str(uuid.uuid4()); db.add_safety_doc(d)
    return jsonify({'status':'ok','id':d['id']}),201

# --- Attendance ---
@app.route('/api/attendance',      methods=['GET'])
@login_required
def api_get_att():
    return jsonify(db.get_attendance(request.args.get('date',date.today().isoformat())))

@app.route('/api/attendance/checkin',  methods=['POST'])
@login_required
def api_checkin():
    p = request.json; rid = str(uuid.uuid4())
    if not db.checkin(p['worker_id'], p['date'], rid):
        return jsonify({'status': 'already_checked_in', 'message': '既に入場済みです'}), 400
    # 通知: 入場
    worker = next((w for w in db.get_workers() if w['id'] == p['worker_id']), {})
    notifier.notify_attendance(worker, 'checkin', p['date'],
                               datetime.now().strftime('%H:%M'))
    return jsonify({'status': 'ok', 'id': rid}), 201

@app.route('/api/attendance/checkout', methods=['POST'])
@login_required
def api_checkout():
    p = request.json
    if not db.checkout(p['worker_id'], p['date']):
        return jsonify({'status': 'not found', 'message': '入場記録が見つかりません'}), 404
    # 通知: 退場
    worker = next((w for w in db.get_workers() if w['id'] == p['worker_id']), {})
    notifier.notify_attendance(worker, 'checkout', p['date'],
                               datetime.now().strftime('%H:%M'))
    return jsonify({'status': 'ok'})

# --- Dashboard / Companies ---
@app.route('/api/dashboard')
@login_required
def api_dashboard(): return jsonify(db.get_dashboard_stats(date.today().isoformat()))

@app.route('/api/companies',       methods=['GET'])
@login_required
def api_get_cos(): return jsonify(db.get_companies())

@app.route('/api/companies',       methods=['POST'])
@write_required
def api_add_co():
    c=request.json; cid=str(uuid.uuid4()); db.add_company(cid,c['name'],c.get('type',''))
    return jsonify({'status':'ok','id':cid}),201

# =============================================================
#  Error handlers

# =============================================================
#  Notification API
# =============================================================
@app.route('/api/notifications/settings', methods=['GET'])
@admin_required
def api_get_notif_settings():
    return jsonify(notifier.get_all_settings())

@app.route('/api/notifications/settings', methods=['POST'])
@admin_required
def api_save_notif_settings():
    for key, val in (request.json or {}).items():
        notifier.set_setting(key, str(val))
    # Update MailConfig cache
    mu.MailConfig.refresh()
    return jsonify({'status': 'ok'})

@app.route('/api/notifications/log', methods=['GET'])
@admin_required
def api_notif_log():
    limit = min(int(request.args.get('limit', 50)), 200)
    return jsonify({
        'log':   notifier.get_notification_log(limit),
        'stats': notifier.get_notification_stats(),
    })

@app.route('/api/notifications/test', methods=['POST'])
@admin_required
def api_notif_test():
    to = request.json.get('to', '').strip()
    if not to or '@' not in to:
        return jsonify({'status': 'error', 'message': '有効なメールアドレスを入力してください'}), 400
    ok, err = mu.send_test_mail(to)
    if ok and err != 'disabled':
        return jsonify({'status': 'ok', 'message': f'{to} にテストメールを送信しました'})
    elif err == 'disabled':
        return jsonify({'status': 'disabled', 'message': 'MAIL_ENABLED=false のため送信されません。.env を確認してください。'})
    return jsonify({'status': 'error', 'message': err}), 500

@app.route('/api/notifications/run-cert-check', methods=['POST'])
@admin_required
def api_run_cert_check():
    count = notifier.check_cert_expiry_and_notify()
    return jsonify({'status': 'ok', 'alerted': count,
                    'message': f'資格期限チェック完了 — {count}名にアラート送信'})

@app.route('/api/notifications/mail-status', methods=['GET'])
@admin_required
def api_mail_status():
    return jsonify(mu.MailConfig.summary())


# =============================================================
#  Backup API
# =============================================================
@app.route('/admin/backup')
@admin_required
def admin_backup():
    return render_template('admin_backup.html')

@app.route('/api/backup/list', methods=['GET'])
@admin_required
def api_backup_list():
    return jsonify({
        'backups': bu.list_backups(),
        'stats':   bu.get_backup_stats(),
    })

@app.route('/api/backup/run', methods=['POST'])
@admin_required
def api_backup_run():
    body  = request.json or {}
    kind  = body.get('kind', bu.KIND_MANUAL)
    label = body.get('label', current_user.username)
    if kind not in (bu.KIND_MANUAL, bu.KIND_DAILY, bu.KIND_WEEKLY, bu.KIND_MONTHLY):
        kind = bu.KIND_MANUAL
    import threading, time
    result_holder = {}
    def _run():
        t0 = time.monotonic()
        r  = bu.create_backup(kind, label)
        r['duration_s'] = round(time.monotonic() - t0, 2)
        bu.prune_old_backups()
        bu.log_backup_result(r, r['duration_s'])
        result_holder.update(r)
    t = threading.Thread(target=_run, daemon=True); t.start(); t.join(timeout=60)
    if not result_holder:
        return jsonify({'success': False, 'error': 'タイムアウト（60秒）'}), 500
    return jsonify(result_holder), (200 if result_holder.get('success') else 500)

@app.route('/api/backup/log', methods=['GET'])
@admin_required
def api_backup_log():
    return jsonify(bu.get_backup_log(50))

@app.route('/api/backup/verify/<filename>', methods=['GET'])
@admin_required
def api_backup_verify(filename):
    if not filename.endswith('.zip') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    return jsonify(bu.verify_backup(filename))

@app.route('/api/backup/download/<filename>', methods=['GET'])
@admin_required
def api_backup_download(filename):
    if not filename.endswith('.zip') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    p = bu.BACKUP_DIR / filename
    if not p.exists():
        return jsonify({'error': 'not found'}), 404
    return send_file(str(p), as_attachment=True, download_name=filename,
                     mimetype='application/zip')

@app.route('/api/backup/restore', methods=['POST'])
@admin_required
def api_backup_restore():
    body     = request.json or {}
    filename = body.get('filename', '')
    targets  = body.get('targets', ['buildee.db'])
    if not filename.endswith('.zip') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    # 許可ターゲットのみ
    allowed = {'buildee.db', '.env', 'certs/buildee.crt', 'certs/buildee.key'}
    targets = [t for t in targets if t in allowed]
    if not targets:
        return jsonify({'error': '復元対象が指定されていません'}), 400
    result = bu.restore_backup(filename, targets)
    return jsonify(result), (200 if result.get('success') else 500)

@app.route('/api/backup/delete/<filename>', methods=['DELETE'])
@admin_required
def api_backup_delete(filename):
    if not filename.endswith('.zip') or '/' in filename or '..' in filename:
        return jsonify({'error': 'invalid filename'}), 400
    p = bu.BACKUP_DIR / filename
    if not p.exists():
        return jsonify({'error': 'not found'}), 404
    p.unlink()
    meta = bu.BACKUP_DIR / f"{filename}.meta.json"
    if meta.exists(): meta.unlink()
    return jsonify({'status': 'ok'})

@app.route('/api/backup/settings', methods=['GET'])
@admin_required
def api_backup_settings_get():
    return jsonify({
        'backup_enabled':        notifier.get_setting('backup_enabled', 'true'),
        'backup_hour':           notifier.get_setting('backup_hour', '2'),
        'backup_notify_success': notifier.get_setting('backup_notify_success', 'false'),
        'backup_keep_daily':     notifier.get_setting('backup_keep_daily', '7'),
        'backup_keep_weekly':    notifier.get_setting('backup_keep_weekly', '4'),
        'backup_keep_monthly':   notifier.get_setting('backup_keep_monthly', '3'),
    })

@app.route('/api/backup/settings', methods=['POST'])
@admin_required
def api_backup_settings_post():
    allowed = {'backup_enabled','backup_hour','backup_notify_success',
                'backup_keep_daily','backup_keep_weekly','backup_keep_monthly'}
    for k, v in (request.json or {}).items():
        if k in allowed:
            notifier.set_setting(k, str(v))
    return jsonify({'status': 'ok'})
    return jsonify({'status': 'ok'})

# ------------------------------------------------------------------
# Floorplan Markers API
# ------------------------------------------------------------------
@app.route('/api/markers', methods=['GET'])
@login_required
def api_get_markers():
    floor = request.args.get('floor')
    return jsonify(db.get_markers(floor))

@app.route('/api/markers', methods=['POST'])
@login_required
def api_add_marker():
    data = request.get_json()
    if not data or not data.get('id') or not data.get('floor'):
        return jsonify({'error': 'invalid data'}), 400
    data['created_by'] = current_user.username
    db.add_marker(data)
    return jsonify({'status': 'ok', 'id': data['id']})

@app.route('/api/markers/<mid>', methods=['PUT'])
@login_required
def api_update_marker(mid):
    data = request.get_json() or {}
    db.update_marker(mid, data)
    return jsonify({'status': 'ok'})

@app.route('/api/markers/<mid>', methods=['DELETE'])
@login_required
def api_delete_marker(mid):
    db.delete_marker(mid)
    return jsonify({'status': 'ok'})

@app.route('/api/markers/floor/<floor>', methods=['DELETE'])
@login_required
def api_clear_floor(floor):
    db.delete_markers_by_floor(floor)
    return jsonify({'status': 'ok'})

@app.errorhandler(401)
def e401(e):
    return (jsonify({'error':'unauthorized'}),401) if request.path.startswith('/api/') \
        else redirect(url_for('login_page', next=request.url))

@app.errorhandler(403)
def e403(e):
    return (jsonify({'error':'forbidden'}),403) if request.path.startswith('/api/') \
        else (render_template('offline.html'),403)

@app.errorhandler(404)
def e404(e):
    return (jsonify({'error':'not found'}),404) if request.path.startswith('/api/') \
        else (render_template('offline.html'),404)

@app.errorhandler(500)
def e500(e):
    return (jsonify({'error':'internal server error','detail':str(e)}),500) \
        if request.path.startswith('/api/') else (render_template('offline.html'),500)


# =============================================================
#  HTTP redirect server (port 5000 → 5443)
# =============================================================
def _run_http_redirect(http_port, https_port):
    """Lightweight Flask app that 301-redirects all HTTP → HTTPS."""
    from flask import Flask as _Flask, redirect as _redirect, request as _req
    redir = _Flask('http_redirect')

    @redir.route('/', defaults={'path': ''})
    @redir.route('/<path:path>')
    def _do_redirect(path):
        url = _req.url.replace('http://', 'https://', 1)
        if f':{http_port}' in url:
            url = url.replace(f':{http_port}', f':{https_port}', 1)
        return _redirect(url, 301)

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    redir.run(host='0.0.0.0', port=http_port, debug=False, use_reloader=False)


# =============================================================
#  Entry point
# =============================================================
if __name__ == '__main__':
    import cert_utils, logging

    print("\n" + "="*50)
    print("  BuildeeMgr 施工管理システム")
    print("="*50)
    print(C.summary())

    if C.HTTPS_ENABLED:
        cert_file, key_file = cert_utils.get_or_create_certs(
            C.CERT_FILE or None, C.KEY_FILE or None
        )

        # Start HTTP→HTTPS redirect thread
        if C.HTTP_REDIRECT:
            t = threading.Thread(
                target=_run_http_redirect,
                args=(C.HTTP_PORT, C.HTTPS_PORT),
                daemon=True
            )
            t.start()
            print(f"\n[HTTP ] Redirect server: http://localhost:{C.HTTP_PORT} → https")

        print(f"[HTTPS] Main server   : https://localhost:{C.HTTPS_PORT}")
        print(f"\n  ブラウザで https://localhost:{C.HTTPS_PORT} を開いてください")
        print("  ※ 自己署名証明書の場合はブラウザの警告を承認してください\n")

        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_file, key_file)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2

        app.run(
            host='0.0.0.0',
            port=C.HTTPS_PORT,
            ssl_context=ctx,
            debug=C.DEBUG,
            use_reloader=False,
        )
    else:
        print(f"\n[HTTP ] Server: http://localhost:{C.HTTP_PORT}")
        app.run(host='0.0.0.0', port=C.HTTP_PORT, debug=C.DEBUG)
