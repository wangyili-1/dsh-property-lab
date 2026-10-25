"""Unary adapters only; all serialization and parsing is upstream toml."""

import toml


def encode_value(value):
    return toml.dumps({"value": value})


def decode_value(document):
    return toml.loads(document)["value"]
