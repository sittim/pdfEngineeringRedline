from pdfredline.annotations.base import AnnotationItem

_REGISTRY: dict[str, type[AnnotationItem]] = {}


def register_annotation(type_name: str, cls: type[AnnotationItem]):
    """Register an annotation class for deserialization."""
    _REGISTRY[type_name] = cls


def deserialize_annotation(data: dict) -> AnnotationItem | None:
    """Create an annotation item from serialized data."""
    type_name = data.get("type", "")
    cls = _REGISTRY.get(type_name)
    if cls is None:
        return None
    return cls.from_data(data)


def get_registered_types() -> dict[str, type[AnnotationItem]]:
    return dict(_REGISTRY)
