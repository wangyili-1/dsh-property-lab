"""Thin unary adapters around unmodified xmltodict public APIs."""

import xmltodict


def encode_comment(value):
    return xmltodict.unparse({"root": {"#comment": value}})


def decode_comment(document):
    return xmltodict.parse(
        document, process_comments=True, strip_whitespace=False
    )["root"]["#comment"]


def encode_text(value):
    return xmltodict.unparse({"root": value})


def decode_text(document):
    return xmltodict.parse(document, strip_whitespace=False)["root"]
