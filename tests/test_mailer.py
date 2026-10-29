"""测 send_ping 的登录凭据与 TLS 模式，不碰网络。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import mailer


class _FakeSMTP:
    """记录构造参数与调用序列的假 SMTP。"""

    instances: list = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.login_args = None
        self.sent = []
        self.starttls_called = False
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.starttls_called = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, msg):
        self.sent.append(msg)


def _setup(monkeypatch, port):
    _FakeSMTP.instances.clear()
    monkeypatch.setattr(mailer, "MAIL_DRY", False)
    monkeypatch.setattr(mailer, "WHITELIST", ["a@example.com"])
    monkeypatch.setattr(mailer, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(mailer, "SMTP_PORT", port)
    monkeypatch.setattr(mailer, "CONTROL_EMAIL", "ctrl@gmail.com")
    monkeypatch.setattr(mailer, "CONTROL_PASS", "app-password")


def test_port_465_uses_implicit_tls(monkeypatch):
    """465 走 SMTP_SSL，不调用 starttls（Gmail 默认配置）。"""
    _setup(monkeypatch, port=465)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", _FakeSMTP)

    ids = mailer.send_ping("ALIVE-TEST")

    smtp = _FakeSMTP.instances[0]
    assert smtp.starttls_called is False
    assert smtp.login_args == ("ctrl@gmail.com", "app-password")
    assert len(ids) == 1 and ids[0] == smtp.sent[0]["Message-ID"]


def test_port_587_uses_starttls(monkeypatch):
    """587 必须 STARTTLS。"""
    _setup(monkeypatch, port=587)
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)

    mailer.send_ping("ALIVE-TEST")

    smtp = _FakeSMTP.instances[0]
    assert smtp.starttls_called is True
    assert smtp.login_args == ("ctrl@gmail.com", "app-password")


def test_from_header_is_control_email(monkeypatch):
    """From 头是控制邮箱，回信才会落回收件箱。"""
    _setup(monkeypatch, port=587)
    monkeypatch.setattr(mailer.smtplib, "SMTP", _FakeSMTP)

    mailer.send_ping("ALIVE-TEST")

    msg = _FakeSMTP.instances[0].sent[0]
    assert "ctrl@gmail.com" in msg["From"]
