from pdfredline.annotations.registry import deserialize_annotation
from pdfredline.annotations.text import TextAnnotation


def test_text_serialize_roundtrip(qapp):
    item = TextAnnotation("Hello World", "Courier", 18, [0, 0, 255, 255])
    data = item.serialize()
    restored = TextAnnotation.from_data(data)
    assert restored.content == "Hello World"
    assert restored.font_family == "Courier"
    assert restored.font_size == 18
    assert restored.color == [0, 0, 255, 255]


def test_text_content_setter(qapp):
    item = TextAnnotation("initial")
    item.content = "updated"
    assert item.content == "updated"


def test_text_registry(qapp):
    item = TextAnnotation("test", "Arial", 12)
    data = item.serialize()
    restored = deserialize_annotation(data)
    assert restored is not None
    assert isinstance(restored, TextAnnotation)
    assert restored.content == "test"
