"""测 mask_email 的脱敏规则。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from utils import mask_email


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("alice@163.com", "a***@163.com"),
        ("123456@qq.com", "1***@qq.com"),
        ("a@b.com", "a***@b.com"),
        ("", "***"),
        ("not-an-email", "***"),
        ("@only-domain.com", "***@only-domain.com"),
    ],
)
def test_mask_email(raw, expected):
    assert mask_email(raw) == expected
