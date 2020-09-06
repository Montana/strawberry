import dataclasses
from functools import partial
from typing import List, Optional, Type, cast

from strawberry.utils.typing import is_generic

from .exceptions import MissingFieldAnnotationError
from .types.type_resolver import _get_fields
from .types.types import FederationTypeParams, TypeDefinition
from .utils.str_converters import to_camel_case


def _get_interfaces(cls: Type) -> List[TypeDefinition]:
    interfaces = []

    for base in cls.__bases__:
        type_definition = cast(
            Optional[TypeDefinition], getattr(base, "_type_definition", None)
        )

        if type_definition and type_definition.is_interface:
            interfaces.append(type_definition)

    return interfaces


def _check_field_annotations(cls: Type):
    """Are any of the dataclass Fields missing type annotations?

    This replicates the check that dataclasses do during creation, but allows a
    proper Strawberry exception to be raised

    https://github.com/python/cpython/blob/6fed3c85402c5ca704eb3f3189ca3f5c67a08d19/Lib/dataclasses.py#L881-L884
    """
    cls_annotations = cls.__dict__.get("__annotations__", {})

    for field_name, value in cls.__dict__.items():
        if not isinstance(value, dataclasses.Field):
            # Not a dataclasses.Field. Ignore
            continue

        if field_name not in cls_annotations:
            # Field object exists but did not get an annotation
            raise MissingFieldAnnotationError(field_name)


def _wrap_dataclass(cls: Type):
    """Wrap a strawberry.type class with a dataclass and check for any issues
    before doing so"""

    # Ensure all Fields have been properly type-annotated
    _check_field_annotations(cls)

    return dataclasses.dataclass(cls)


def _process_type(
    cls,
    *,
    name: Optional[str] = None,
    is_input: bool = False,
    is_interface: bool = False,
    description: Optional[str] = None,
    federation: Optional[FederationTypeParams] = None
):
    name = name or to_camel_case(cls.__name__)

    wrapped = _wrap_dataclass(cls)

    interfaces = _get_interfaces(wrapped)
    fields = _get_fields(cls)

    wrapped._type_definition = TypeDefinition(
        name=name,
        is_input=is_input,
        is_interface=is_interface,
        is_generic=is_generic(cls),
        interfaces=interfaces,
        description=description,
        federation=federation or FederationTypeParams(),
        origin=cls,
        _fields=fields,
    )

    return wrapped


def type(
    cls: Type = None,
    *,
    name: str = None,
    is_input: bool = False,
    is_interface: bool = False,
    description: str = None,
    federation: Optional[FederationTypeParams] = None
):
    """Annotates a class as a GraphQL type.

    Example usage:

    >>> @strawberry.type:
    >>> class X:
    >>>     field_abc: str = "ABC"
    """

    def wrap(cls):
        return _process_type(
            cls,
            name=name,
            is_input=is_input,
            is_interface=is_interface,
            description=description,
            federation=federation,
        )

    if cls is None:
        return wrap

    return wrap(cls)


input = partial(type, is_input=True)
interface = partial(type, is_interface=True)
