"""临时探路：测 Gmail IMAP/SMTP 的 TCP + TLS 连通性。用完可删。"""

import socket
import ssl

for host, port in [("imap.gmail.com", 993), ("smtp.gmail.com", 465)]:
    try:
        raw = socket.create_connection((host, port), timeout=8)
        ctx = ssl.create_default_context()
        tls = ctx.wrap_socket(raw, server_hostname=host)
        peer = tls.getpeercert()["subject"]
        print(f"{host}:{port} TLS OK, subject = {peer}")
        tls.close()
    except Exception as e:
        print(f"{host}:{port} FAIL: {type(e).__name__}: {e}")
