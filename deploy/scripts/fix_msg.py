#!/usr/bin/env python3
"""
git filter-branch --msg-filter で呼び出されるスクリプト
文字化けしたコミットメッセージを修正する
"""
import sys

msg = sys.stdin.buffer.read()

# 文字化けパターン → 正しい日本語に置換
replacements = [
    (b'\xe8\xad\x81\xe3\x81\xbd\xe8\x9f\xbe\xe9\x82\x84\xe9\x80\x85\xe3\x83\xbb'
     b'\xe3\x81\x99\xe7\xb9\xa7\xe3\x82\xb9\xe3\x83\x86\xe3\x83\xbb\xce\x92',
     '施工管理システム完全版'.encode('utf-8')),
    # Shift-JIS 化けパターン
    ('譁ｽ蟾･邂｡逅・す繧ｹ繝・Β'.encode('utf-8'),
     '施工管理システム完全版'.encode('utf-8')),
]

result = msg
for old, new in replacements:
    result = result.replace(old, new)

# デコードして再エンコード（文字化け修正）
try:
    decoded = result.decode('utf-8')
except UnicodeDecodeError:
    try:
        decoded = result.decode('cp932')
    except UnicodeDecodeError:
        decoded = result.decode('latin-1')

# 文字化けパターンの文字列置換
garbled = 'feat: BuildeeMgr v1.0.0 -- 譁ｽ蟾･邂｡逅・す繧ｹ繝・Β'
correct = 'feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版'
if '譁' in decoded or '繧' in decoded:
    decoded = correct + '\n'

sys.stdout.buffer.write(decoded.encode('utf-8'))
