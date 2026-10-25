from datetime import timedelta
from boltons import iterutils, timeutils, mathutils


def parse_seconds(value):
    result = timeutils.parse_timedelta(f'{value}s')
    return result.days * 86400 + result.seconds


def identity(value):
    return value


def windowed_three(values):
    return [list(row) for row in iterutils.windowed(values, 3, fill=None)]


def windowed_reference(values):
    return [(values[index:index + 3] + [None] * 3)[:3] for index in range(len(values))]


def bits_roundtrip(text):
    return mathutils.Bits.from_bin(text).as_bin()


def split_grouped_once(text):
    values = [None if c == ' ' else c for c in text]
    return [''.join(' ' if c is None else c for c in group)
            for group in iterutils.split(values, sep=None, maxsplit=1)]


def split_builtin_once(text):
    return text.split(None, 1)
