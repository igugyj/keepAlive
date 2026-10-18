import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from utils import describe_active


@pytest.mark.parametrize(
    "weeks,expected",
    [
        (0, "within 1 week"),
        (1, "1 week ago"),
        (2, "2 weeks ago"),
        (3, "3 weeks ago"),
        (4, "1 month ago"),
        (5, "1 month 1 week ago"),
        (7, "1 month 3 weeks ago"),
        (8, "2 months ago"),
        (11, "2 months 3 weeks ago"),
        (12, "3 months ago"),
        (51, "12 months 3 weeks ago"),
        (52, "1 year ago"),
        (53, "1 year 1 week ago"),
        (55, "1 year 3 weeks ago"),
        (56, "1 year 1 month ago"),
        (57, "1 year 1 month 1 week ago"),
        (104, "2 years ago"),
        (108, "2 years 1 month ago"),
    ],
)
def test_describe_active(weeks, expected):
    assert describe_active(weeks) == expected
