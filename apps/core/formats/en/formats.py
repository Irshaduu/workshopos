"""Indian dates and numbers on every screen (docs/DESIGN.md).

Django has no formats for Indian English. Its English ones are American: they
show Oct. 3, 2026 and 150,000.00, and read a typed 10/11/2026 as 11 October.
Django's own filters read this file: floatformat for numbers, date for dates.

The folder name is the language, so en also covers en-in, our LANGUAGE_CODE. A
second language needs its own copy (ml), and a test fails until it has one.
"""

DATE_FORMAT = "j M Y"  # 3 Oct 2026
SHORT_DATE_FORMAT = "d/m/Y"  # 03/10/2026
TIME_FORMAT = "g:i A"  # 3:05 PM
DATETIME_FORMAT = "j M Y, g:i A"  # 3 Oct 2026, 3:05 PM
SHORT_DATETIME_FORMAT = "d/m/Y, g:i A"  # 03/10/2026, 3:05 PM
YEAR_MONTH_FORMAT = "F Y"  # October 2026
MONTH_DAY_FORMAT = "j M"  # 3 Oct

# 1,50,000: the last three digits, then pairs.
NUMBER_GROUPING = (3, 2, 0)

# What a person may type: the day first, never the month first. A form's date
# box shows a saved date in the first style of the list, and a browser's date
# box reads only the year-first one, so that one stays first.
DATE_INPUT_FORMATS = [
    "%Y-%m-%d",  # 2026-10-03
    "%d/%m/%Y",  # 03/10/2026
    "%d-%m-%Y",  # 03-10-2026
    "%d/%m/%y",  # 03/10/26
    "%d %b %Y",  # 3 Oct 2026
    "%d %B %Y",  # 3 October 2026
]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
]
