import subprocess, sys

# extract_msg がなければインストール
try:
    import extract_msg
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'extract_msg', '-q'])
    import extract_msg

import os

msg_path = r'C:\Users\tasayur\AppData\Local\Temp\_HSG1_ HSG1 TPE Project Construction Daily Report2026_4_8 水 【無事故・無災害・物損無・SSO無】 (1).msg'

msg = extract_msg.Message(msg_path)

print('='*60)
print('SUBJECT:', msg.subject)
print('FROM   :', msg.sender)
print('TO     :', msg.to)
print('CC     :', msg.cc)
print('='*60)
print('BODY:')
body = msg.body or ''
print(body[:5000])
print('='*60)
print('HTML BODY:')
try:
    html = msg.htmlBody
    if html:
        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='replace')
        print(html[:3000])
except:
    print('(no html)')

# 添付ファイル一覧
print('='*60)
print('ATTACHMENTS:')
for att in msg.attachments:
    print(' -', att.longFilename or att.shortFilename)

msg.close()
