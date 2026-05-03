import sys
msg = sys.stdin.buffer.read().decode("utf-8", errors="replace")
garbled = ["譁ｽ", "蟾･", "繧ｹ繝", "邂｡逅"]
if any(p in msg for p in garbled):
    msg = "feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版\n"
sys.stdout.buffer.write(msg.encode("utf-8"))
