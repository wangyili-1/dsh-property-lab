"""Independent public-API observations; no adapter or property runner imports."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
from xml.dom import Node, minidom

import xmltodict


def dom_comment(document):
    parsed = minidom.parseString(document)
    return [child.data for child in parsed.documentElement.childNodes
            if child.nodeType == Node.COMMENT_NODE][0]


def observe(value):
    reference = minidom.Document()
    root = reference.createElement("root")
    reference.appendChild(root)
    root.appendChild(reference.createComment(value))
    original_xml = reference.toxml()
    original_parsed = xmltodict.parse(
        original_xml, process_comments=True, strip_whitespace=False
    )
    # The source is real XML parsed by xmltodict; unparse sees its own output shape.
    encoded = xmltodict.unparse(original_parsed)
    roundtrip = xmltodict.parse(
        encoded, process_comments=True, strip_whitespace=False
    )["root"]["#comment"]
    direct = xmltodict.unparse({"root": {"#comment": value}})
    text_encoded = xmltodict.unparse({"root": value})
    text_roundtrip = xmltodict.parse(text_encoded, strip_whitespace=False)["root"]
    return {
        "original": value,
        "dom_reference_xml": original_xml,
        "dom_reference_comment": dom_comment(original_xml),
        "xmltodict_initial_parse": original_parsed["root"]["#comment"],
        "xmltodict_encoded": encoded,
        "xmltodict_roundtrip": roundtrip,
        "dom_parse_of_xmltodict_encoded": dom_comment(encoded),
        "public_dict_unparse_matches_xml_roundtrip": direct == encoded,
        "comment_preserved": roundtrip == value,
        "text_control_preserved": text_roundtrip == value,
    }


def main():
    values = ["<", ">", "&", "<head> & <body>", "ordinary", " \t\n", "中文éΩ"]
    source = Path(xmltodict.__file__)
    records = [observe(value) for value in values]
    assert all(row["dom_reference_comment"] == row["original"] for row in records)
    assert all(row["xmltodict_initial_parse"] == row["original"] for row in records)
    assert all(row["public_dict_unparse_matches_xml_roundtrip"] for row in records)
    assert all(row["text_control_preserved"] for row in records)
    print(json.dumps({
        "xmltodict_version": importlib.metadata.version("xmltodict"),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "observations": records,
    }, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
