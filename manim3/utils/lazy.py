# TODO: The document is outdated.

"""
This module implements a basic class with lazy properties.

The functionality of `LazyBase` is to save resource as much as it can.
On one hand, all data of `lazy_object` and `lazy_property` are shared among
instances. On the other hand, these data will be restocked (recursively) if
they themselves are instances of `LazyBase`. One may also define custom
restockers for individual data.

Every child class of `LazyBase` shall be declared with an empty `__slots__`,
and all methods shall be sorted in the following way:
- magic methods
- lazy_variable_shared
- lazy_object
- lazy_property
- lazy_slot
- private class methods
- private methods
- public methods

All methods decorated by any of `lazy_object`, `lazy_variable_shared`,
`lazy_property` and `lazy_slot` should be static methods, and so are their
restockers. Type annotation is strictly applied to reduce chances of running
into unexpected behaviors.

Methods decorated by `lazy_object` should be named with underscores appeared
on both sides, i.e. `_data_`. Each should not take any argument and return
the *initial* value for this data. `NotImplemented` may be an alternative for
the value returned, as long as the data is initialized in `__new__` method.
In principle, the data can be of any type including mutable ones, but one must
keep in mind that data *cannot be mutated* as they are shared. The only way to
change the value is to reset the data via `__set__`, and the new value shall
be wrapped up with `LazyWrapper`. This makes it possible to manually share data
which is not the initial value. Note, the `__get__` method will return the
unwrapped data. One shall use `instance.__class__._data_._get_data(instance)`
to obtain the wrapped data if one wishes to share it with other instances.

Methods decorated by `lazy_variable_shared` are pretty much similar to ones
decorated by `lazy_object`, except that an argument `hasher` should be
additionally passed to the decorator. Data handled in these methods are
expected to be light-weighted and have much duplicated usage so that caching
can take effect. Data wrapping is not necessary when calling `__set__`.

Methods decorated by `lazy_property` should be named with the same style of
`lazy_object`. They should take *at least one* argument, and all names of
arguments should be matched with any `lazy_object` or other `lazy_property`
where underscores on edges are eliminated. Data is immutable, and calling
`__set__` method will trigger an exception. As the name `lazy` suggests, if
any correlated `lazy_object` is altered, as long as the calculation is never
done before, the recalculation will be executed when one calls `__get__`.

Methods decorated by `lazy_slot` should be named with an underscore inserted
at front, i.e. `_data`. They behave like a normal attribute of the class.
Again, each should not take any argument and return the *initial* value for
this data, with `NotImplemented` as an alternative if the data is set in
`__new__`. Data can be freely mutated because they are no longer shared
(as long as one does not do something like `b._data = a._data`, or calls the
`_copy` method). Data wrapping is not necessary when calling `__set__`.
"""


__all__ = [
    "LazyCollection",
    "LazyCollectionDescriptor",
    "LazyObject",
    "LazyObjectDescriptor",
    "LazyPropertyDescriptor",
    "LazyWrapper",
    "lazy_collection",
    "lazy_object",
    "lazy_object_shared",
    "lazy_object_raw",
    "lazy_property",
    "lazy_property_shared",
    "lazy_property_raw"
]


from abc import ABC
from functools import wraps
#from abc import (
#    ABC,
#    abstractmethod
#)
#from dataclasses import (
#    field,
#    make_dataclass
#)
import inspect
import re
#from types import GenericAlias
from typing import (
    Any,
    Callable,
    ClassVar,
    Generator,
    Generic,
    Hashable,
    Iterator,
    #Iterator,
    #Never,
    TypeVar,
    Union,
    overload
)

from bidict import bidict
#from ordered_set import OrderedSet

from ..utils.dag import DAGNode


#_DAGNodeT = TypeVar("_DAGNodeT", bound="DAGNode")
_T = TypeVar("_T")
_KeyT = TypeVar("_KeyT", bound=Hashable)
#_LazyBaseT = TypeVar("_LazyBaseT", bound="LazyBase")
_LazyEntityT = TypeVar("_LazyEntityT", bound="LazyEntity")
_LazyObjectT = TypeVar("_LazyObjectT", bound="LazyObject")
_ParameterElementsT = TypeVar("_ParameterElementsT", bound=Hashable)
#_ObjT = TypeVar("_ObjT", bound="LazyObject")
_InstanceT = TypeVar("_InstanceT", bound="LazyObject")
#_Annotation = Any


#class LazyObjectNode(DAGNode):
#    __slots__ = ("_lazy_object", "_expired")
#
#    def __init__(self, *, lazy_object: "LazyObject" = NotImplemented, expired: bool = True):
#        super().__init__()
#        self._lazy_object: LazyObject = lazy_object
#        self._expired: bool = expired


#def _get_type_from_annotation(annotation: _Annotation) -> "type[DAGNode]":
#    return annotation.__origin__ if isinstance(annotation, GenericAlias) else annotation


#class LazyParameterNode(DAGNode):
#    __slots__ = ("_parameter",)
#
#    def __init__(self, instance: "LazyInstance") -> None:
#        super().__init__()
#        self._parameter: LazyInstance = instance


class LazyNode(DAGNode):
    __slots__ = ("_ref",)

    def __init__(self, instance: "LazyBase") -> None:
        super().__init__()
        self._ref: LazyBase = instance


class LazyBase(ABC):
    __slots__ = (
        "_dependency_node",
        "_parameter_node",
        #"_readonly",
        "_restock_callbacks"
    )

    _VACANT_INSTANCES: "ClassVar[list[LazyBase]]"
    #_VARIABLE_DESCRS: "ClassVar[list[LazyObjectDescriptor]]"

    def __init_subclass__(cls) -> None:
        cls._VACANT_INSTANCES = []
        #return super().__init_subclass__()

    def __new__(cls, *args, **kwargs):
        if (instances := cls._VACANT_INSTANCES):
            instance = instances.pop()
            assert isinstance(instance, cls)
        else:
            instance = super().__new__(cls)
        return instance

    def __init__(self) -> None:
        super().__init__()
        self._dependency_node: LazyNode = LazyNode(self)
        self._parameter_node: LazyNode = LazyNode(self)
        #self._readonly: bool = False
        self._restock_callbacks: list[Callable[[LazyBase], None]] | None = []

    def _iter_dependency_children(self) -> "Generator[LazyBase, None, None]":
        for child in self._dependency_node._children:
            yield child._ref

    def _iter_dependency_parents(self) -> "Generator[LazyBase, None, None]":
        for parent in self._dependency_node._parents:
            yield parent._ref

    def _iter_dependency_descendants(self) -> "Generator[LazyBase, None, None]":
        for descendant in self._dependency_node._iter_descendants():
            yield descendant._ref

    def _iter_dependency_ancestors(self) -> "Generator[LazyBase, None, None]":
        for ancestor in self._dependency_node._iter_ancestors():
            yield ancestor._ref

    def _bind_dependency_children(self, *instances: "LazyBase"):
        self._dependency_node._bind_children(*(
            instance._dependency_node
            for instance in instances
        ))
        return self

    def _unbind_dependency_children(self, *instances: "LazyBase"):
        self._dependency_node._unbind_children(*(
            instance._dependency_node
            for instance in instances
        ))
        for instance in instances:
            if not instance._iter_dependency_parents():
                instance._restock()
        return self

    def _iter_parameter_children(self) -> "Generator[LazyBase, None, None]":
        for child in self._parameter_node._children:
            yield child._ref

    def _iter_parameter_parents(self) -> "Generator[LazyBase, None, None]":
        for parent in self._parameter_node._parents:
            yield parent._ref

    def _iter_parameter_descendants(self) -> "Generator[LazyBase, None, None]":
        for descendant in self._parameter_node._iter_descendants():
            yield descendant._ref

    def _iter_parameter_ancestors(self) -> "Generator[LazyBase, None, None]":
        for ancestor in self._parameter_node._iter_ancestors():
            yield ancestor._ref

    def _bind_parameter_children(self, *instances: "LazyBase"):
        self._parameter_node._bind_children(*(
            instance._parameter_node
            for instance in instances
        ))
        return self

    def _unbind_parameter_children(self, *instances: "LazyBase"):
        self._parameter_node._unbind_children(*(
            instance._parameter_node
            for instance in instances
        ))
        return self

    def _restock(self) -> None:
        # TODO: check refcnt
        for instance in self._iter_dependency_descendants():
            if (callbacks := instance._restock_callbacks) is None:
                continue
            for callback in callbacks:
                callback(instance)
            callbacks.clear()
            instance.__class__._VACANT_INSTANCES.append(instance)

    def _at_restock(self, callback: "Callable[[LazyBase], None]") -> None:
        if (callbacks := self._restock_callbacks) is not None:
            callbacks.append(callback)


class LazyEntity(LazyBase):
    __slots__ = ()

    def _is_readonly(self) -> bool:
        return not any(
            isinstance(instance, LazyProperty)
            for instance in self._iter_dependency_ancestors()
        )

    def _expire_properties(self) -> None:
        assert not self._is_readonly()
        for expired_property in self._iter_parameter_ancestors():
            if not isinstance(expired_property, LazyProperty):
                continue
            expired_property._set(None)


class LazyObject(LazyEntity):
    __slots__ = ()

    #_LAZY_DESCRIPTORS: "ClassVar[list[LazyDescriptor[LazyEntity, LazyObject]]]"
    _OBJECT_DESCRIPTORS: "ClassVar[list[LazyObjectDescriptor]]"
    _COLLECTION_DESCRIPTORS: "ClassVar[list[LazyCollectionDescriptor]]"
    _PROPERTY_DESCRIPTORS: "ClassVar[list[LazyPropertyDescriptor]]"
    _PARAMETER_DESCRIPTORS: "ClassVar[list[LazyParameterDescriptor]]"

    def __init_subclass__(cls) -> None:
        attrs: dict[str, Any] = {
            name: attr
            for parent_cls in reversed(cls.__mro__)
            for name, attr in parent_cls.__dict__.items()
        }
        object_descriptors = {
            name: attr
            for name, attr in attrs.items()
            if isinstance(attr, LazyObjectDescriptor)
        }
        collection_descriptors = {
            name: attr
            for name, attr in attrs.items()
            if isinstance(attr, LazyCollectionDescriptor)
        }
        property_descriptors = {
            name: attr
            for name, attr in attrs.items()
            if isinstance(attr, LazyPropertyDescriptor)
        }
        descriptors: dict[str, LazyObjectDescriptor | LazyCollectionDescriptor | LazyPropertyDescriptor] = {
            **object_descriptors,
            **collection_descriptors,
            **property_descriptors
        }
        assert all(
            re.fullmatch(r"_\w+_", name)
            for name in descriptors
        )

        #def construct_obj_from_descriptor_chain(
        #    descriptor_chain: tuple[LazyObjectDescriptor | LazyCollectionDescriptor | LazyPropertyDescriptor, ...],
        #    obj: Any
        #) -> Any:
        #    for descriptor in descriptor_chain:
        #        if isinstance(descriptor, LazyCollectionDescriptor):
        #            obj = apply_deepest(lambda instance: tuple(descriptor.__get__(instance)._node_children), obj)
        #        else:
        #            obj = apply_deepest(lambda instance: descriptor.__get__(instance), obj)
        #    return obj


        #descrs: dict[str, LazyDescriptor] = {
        #    name: attr
        #    for name, attr in attrs.items()
        #    if isinstance(attr, LazyDescriptor)
        #}
        #cls._LAZY_DESCRIPTORS = list(descrs.values())

        parameter_descriptors: dict[str, LazyParameterDescriptor] = {}

        for property_descriptor in property_descriptors.values():
            method = property_descriptor.method
            property_parameters: list[LazyParameterDescriptor] = []
            for parameter_name in inspect.signature(method).parameters:
                if (parameter_descriptor := parameter_descriptors.get(parameter_name)) is None:
                    is_lazy_value = False
                    if not re.fullmatch(r"_\w+_", parameter_name):
                        is_lazy_value = True
                        parameter_name = f"_{parameter_name}_"
                    descriptor_chain = tuple(
                        descriptors[name]
                        for name in re.findall(r"_\w+?_(?=_|$)", parameter_name)
                    )
                    parameter_descriptor = LazyParameterDescriptor()
                    parameter_descriptor.descriptor_chain = descriptor_chain
                    parameter_descriptor.is_lazy_value = is_lazy_value
                    #parameter_descriptor.get_parameter_from_instance = implement_get_parameter_from_instance(parameter_name)
                    parameter_descriptors[parameter_name] = parameter_descriptor
                property_parameters.append(parameter_descriptor)
            property_descriptor.parameter_descriptors = tuple(property_parameters)

            #descr._setup_callables(descrs)

        super().__init_subclass__()
        cls._OBJECT_DESCRIPTORS = list(object_descriptors.values())
        cls._COLLECTION_DESCRIPTORS = list(collection_descriptors.values())
        cls._PARAMETER_DESCRIPTORS = list(parameter_descriptors.values())
        cls._PROPERTY_DESCRIPTORS = list(property_descriptors.values())

    def __init__(self) -> None:
        super().__init__()

        cls = self.__class__
        for object_descriptor in cls._OBJECT_DESCRIPTORS:
            object_descriptor.initialize(self)
        for collection_descriptor in cls._COLLECTION_DESCRIPTORS:
            collection_descriptor.initialize(self)
        for parameter_descriptor in cls._PARAMETER_DESCRIPTORS:
            parameter_descriptor.initialize(self)
        for property_descriptor in cls._PROPERTY_DESCRIPTORS:
            property_descriptor.initialize(self)
            
        #for descr in self.__class__._LAZY_DESCRIPTORS:
        #    if isinstance(descr, LazyObjectDescriptor):
        #        if (default_object := descr._default_object) is None:
        #            default_object = descr.method()
        #            default_object._restock_callbacks = None  # Never restock
        #            descr._default_object = default_object
        #        descr.initialize(self, default_object)
        #        children.append(default_object)
        #    elif isinstance(descr, LazyCollectionDescriptor):
        #        default_collection = descr.method()
        #        descr.initialize(self, default_collection)
        #        children.append(default_collection)
        #self._bind_dependency_children(*children)

    def _copy(self):
        cls = self.__class__
        result = cls.__new__(cls)
        for object_descriptor in cls._OBJECT_DESCRIPTORS:
            object_descriptor.copy_initialize(result, self)
        for collection_descriptor in cls._COLLECTION_DESCRIPTORS:
            collection_descriptor.copy_initialize(result, self)
        for parameter_descriptor in cls._PARAMETER_DESCRIPTORS:
            parameter_descriptor.copy_initialize(result, self)
        for property_descriptor in cls._PROPERTY_DESCRIPTORS:
            property_descriptor.copy_initialize(result, self)
        return result


class LazyCollection(Generic[_LazyEntityT], LazyEntity):
    __slots__ = ("_entities",)

    def __init__(self) -> None:
        super().__init__()
        self._entities: list[_LazyEntityT] = []

    def __iter__(self) -> Iterator[_LazyEntityT]:
        return self._entities.__iter__()

    def __len__(self) -> int:
        return self._entities.__len__()

    @overload
    def __getitem__(self, index: int) -> _LazyEntityT:
        ...

    @overload
    def __getitem__(self, index: slice) -> list[_LazyEntityT]:
        ...

    def __getitem__(self, index: int | slice) -> _LazyEntityT | list[_LazyEntityT]:
        #if isinstance(index, int):
        #    return self._reference_node._children.__getitem__(index)._instance
        return self._entities.__getitem__(index)

    def add(self, *entities: _LazyEntityT):
        if not entities:
            return self
        self._expire_properties()
        self._entities.extend(entities)
        self._bind_dependency_children(*entities)
        return self

    def remove(self, *entities: _LazyEntityT):
        if not entities:
            return self
        self._expire_properties()
        for entity in entities:
            self._entities.remove(entity)
        self._unbind_dependency_children(*entities)
        return self


class LazyParameter(Generic[_ParameterElementsT], LazyBase):
    __slots__ = ("_elements",)

    def __init__(self) -> None:
        super().__init__()
        self._elements: _ParameterElementsT | None = None

    def _get(self) -> _ParameterElementsT | None:
        return self._elements

    def _set(self, elements: _ParameterElementsT | None) -> None:
        self._elements = elements

    #def _bind_entities(self, *entities: LazyEntity):
    #    self._bind_parameter_children(*entities)
    #    return self

    #def _bind_properties(self, *properties: "LazyProperty"):
    #    self._bind_parameter_children(*properties)
    #    return self


class LazyProperty(Generic[_LazyEntityT], LazyBase):
    #__slots__ = ()
    __slots__ = ("_entity",)

    def __init__(self) -> None:
        super().__init__()
        self._entity: _LazyEntityT | None = None

    def _get(self) -> _LazyEntityT | None:
        return self._entity
        #try:
        #    return next(self._iter_reference_children())
        #except StopIteration:
        #    return None

    def _set(self, entity: _LazyEntityT | None) -> None:
        self._entity = entity
        #old_entity = self._entity
        #if old_entity is entity:
        #    return
        #self._entity = entity
        #if old_entity is not None:
        #    self._unbind_dependency_children(old_entity)
        #if entity is not None:
        #    self._bind_dependency_children(entity)

    #def _bind_parameters(self, *parameters: LazyParameter):
    #    self._bind_parameter_children(*parameters)
    #    return self


#class LazyDescriptor(Generic[_LazyInstanceT, _ObjT]):
#    __slots__ = (
#        "name",
#        "values_dict"
#    )

#    def __init__(self, name: str) -> None:
#        self.name: str = name
#        self.values_dict: dict[_ObjT, _LazyInstanceT] = {}

#    @overload
#    def __get__(
#        self,
#        obj: None,
#        owner: type[_ObjT] | None = None
#    ): ...

#    @overload
#    def __get__(
#        self,
#        obj: _ObjT,
#        owner: type[_ObjT] | None = None
#    ) -> _LazyInstanceT: ...

#    def __get__(
#        self,
#        obj: _ObjT | None,
#        owner: type[_ObjT] | None = None
#    )  | _LazyInstanceT:
#        if obj is None:
#            return self
#        if (value := self.get(obj)) is None:
#            value = self.missing(obj)
#            self.values_dict[obj] = value
#        return value

#    def __set__(
#        self,
#        obj: _ObjT,
#        value: _LazyInstanceT
#    ) -> None:
#        self.values_dict[obj] = value

#    def initialize(
#        self,
#        obj: _ObjT,
#        value: _LazyInstanceT
#    ) -> None:
#        assert obj not in self.values_dict
#        self.values_dict[obj] = value

#    def pop(
#        self,
#        obj: _ObjT
#    ) -> _LazyInstanceT:
#        return self.values_dict.pop(obj)

#    def get(
#        self,
#        obj: _ObjT
#    ) -> _LazyInstanceT | None:
#        return self.values_dict.get(obj)

#    def missing(
#        self,
#        obj: _ObjT
#    ) -> _LazyInstanceT:
#        raise KeyError


class LazyObjectDescriptor(Generic[_LazyObjectT, _InstanceT]):
    __slots__ = (
        "method",
        "instance_to_object_dict",
        "_default_object"
    )

    def __init__(
        self,
        method: Callable[[], _LazyObjectT]
    ) -> None:
        #super().__init__(method.__name__)
        self.method: Callable[[], _LazyObjectT] = method
        self.instance_to_object_dict: dict[_InstanceT, _LazyObjectT] = {}
        self._default_object: _LazyObjectT | None = None

    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyObjectDescriptor[_LazyObjectT, _InstanceT]": ...  # TODO: typing

    @overload
    def __get__(
        self,
        instance: _InstanceT,
        owner: type[_InstanceT] | None = None
    ) -> _LazyObjectT: ...

    def __get__(
        self,
        instance: _InstanceT | None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyObjectDescriptor[_LazyObjectT, _InstanceT] | _LazyObjectT":
        if instance is None:
            return self
        return self.instance_to_object_dict[instance]

    def __set__(
        self,
        instance: _InstanceT,
        lazy_object: _LazyObjectT
    ) -> None:
        old_object = self.instance_to_object_dict[instance]
        old_object._expire_properties()
        instance._unbind_dependency_children(old_object)
        self.instance_to_object_dict[instance] = lazy_object
        instance._bind_dependency_children(lazy_object)

    def initialize(
        self,
        instance: _InstanceT
    ) -> None:
        if (default_object := self._default_object) is None:
            default_object = self.method()
            default_object._restock_callbacks = None  # Never restock
            self._default_object = default_object
        self.instance_to_object_dict[instance] = default_object
        instance._bind_dependency_children(default_object)

    def copy_initialize(
        self,
        dst: _InstanceT,
        src: _InstanceT
    ) -> None:
        self.initialize(dst)
        dst._unbind_dependency_children(self.instance_to_object_dict[dst])
        dst._bind_dependency_children(self.instance_to_object_dict[src])


class LazyCollectionDescriptor(Generic[_LazyEntityT, _InstanceT]):
    __slots__ = (
        "method",
        "instance_to_collection_dict"
    )

    def __init__(
        self,
        method: Callable[[], LazyCollection[_LazyEntityT]]
    ) -> None:
        #super().__init__(method.__name__)
        self.method: Callable[[], LazyCollection[_LazyEntityT]] = method
        self.instance_to_collection_dict: dict[_InstanceT, LazyCollection[_LazyEntityT]] = {}

    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyCollectionDescriptor[_LazyEntityT, _InstanceT]": ...

    @overload
    def __get__(
        self,
        instance: _InstanceT,
        owner: type[_InstanceT] | None = None
    ) -> LazyCollection[_LazyEntityT]: ...

    def __get__(
        self,
        instance: _InstanceT | None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyCollectionDescriptor[_LazyEntityT, _InstanceT] | LazyCollection[_LazyEntityT]":
        if instance is None:
            return self
        return self.instance_to_collection_dict[instance]

    def initialize(
        self,
        instance: _InstanceT
    ) -> None:
        default_object = self.method()
        self.instance_to_collection_dict[instance] = default_object
        instance._bind_dependency_children(default_object)

    def copy_initialize(
        self,
        dst: _InstanceT,
        src: _InstanceT
    ) -> None:
        self.initialize(dst)
        self.instance_to_collection_dict[dst].add(*self.instance_to_collection_dict[src])

    #def __set__(
    #    self,
    #    instance: _InstanceT,
    #    value: Never
    #) -> None:
    #    raise RuntimeError("Attempting to set a collection object directly")


class LazyParameterDescriptor(Generic[_ParameterElementsT, _InstanceT]):
    __slots__ = (
        "descriptor_chain",
        "is_lazy_value",
        "instance_to_parameter_dict"
    )

    def __init__(self) -> None:
        self.descriptor_chain: tuple[Union[
            LazyObjectDescriptor[LazyObject, _InstanceT],
            LazyCollectionDescriptor[LazyEntity, _InstanceT],
            LazyPropertyDescriptor[LazyEntity, _InstanceT]
        ], ...] = NotImplemented
        self.is_lazy_value: bool = NotImplemented
        #self.get_parameter_from_instance: Callable[[_InstanceT], _ParameterElementsT] = NotImplemented
        self.instance_to_parameter_dict: dict[_InstanceT, LazyParameter[_ParameterElementsT]] = {}

    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyParameterDescriptor[_ParameterElementsT, _InstanceT]": ...

    @overload
    def __get__(
        self,
        instance: _InstanceT,
        owner: type[_InstanceT] | None = None
    ) -> _ParameterElementsT: ...

    def __get__(
        self,
        instance: _InstanceT | None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyParameterDescriptor[_ParameterElementsT, _InstanceT] | _ParameterElementsT":
        if instance is None:
            return self

        def apply_deepest(
            callback: Callable[[Any], Any],
            obj: Any
        ) -> Any:
            if not isinstance(obj, tuple):
                return callback(obj)
            return tuple(
                apply_deepest(callback, child_obj)
                for child_obj in obj
            )

        def yield_deepest(
            obj: Any
        ) -> Generator[Any, None, None]:
            if not isinstance(obj, tuple):
                yield obj
            else:
                for child_obj in obj:
                    yield from yield_deepest(child_obj)

        parameter = self.instance_to_parameter_dict[instance]
        if (elements := parameter._get()) is None:
            elements = instance
            requires_parameter_binding = True
            for descriptor in self.descriptor_chain:
                if requires_parameter_binding:
                    parameter._bind_parameter_children(*yield_deepest(elements))
                if isinstance(descriptor, LazyCollectionDescriptor):
                    elements = apply_deepest(lambda obj: tuple(descriptor.__get__(obj)._node_children), elements)
                else:
                    elements = apply_deepest(lambda obj: descriptor.__get__(obj), elements)
                    if isinstance(descriptor, LazyPropertyDescriptor):
                        requires_parameter_binding = False
            if self.is_lazy_value:
                elements = apply_deepest(lambda obj: obj.value, elements)
            parameter._set(elements)
        return elements

    def initialize(
        self,
        instance: _InstanceT
    ) -> None:
        self.instance_to_parameter_dict[instance] = LazyParameter()

    def copy_initialize(
        self,
        dst: _InstanceT,
        src: _InstanceT
    ) -> None:
        self.initialize(dst)
        self.instance_to_parameter_dict[dst]._set(self.instance_to_parameter_dict[src]._get())


class LazyPropertyDescriptor(Generic[_LazyEntityT, _InstanceT]):
    __slots__ = (
        "method",
        "parameter_descriptors",
        "instance_to_property_dict",
        "parameters_to_entity_bidict"
    )

    def __init__(
        self,
        method: Callable[..., _LazyEntityT]
    ) -> None:
        self.method: Callable[..., _LazyEntityT] = method
        self.parameter_descriptors: tuple[LazyParameterDescriptor, ...] = NotImplemented
        #self.get_entity_from_parameters: Callable[[tuple], _LazyEntityT] = NotImplemented
        #self.parameters: tuple[str, ...] = parameter_tuple
        self.instance_to_property_dict: dict[_InstanceT, LazyProperty[_LazyEntityT]] = {}
        self.parameters_to_entity_bidict: bidict[tuple, _LazyEntityT] = bidict()
        #self.property_to_parameters_dict: dict[_DAGNodeT, tuple] = {}
        #self.instance_to_property_record_dict: dict[_InstanceT, LazyPropertyRecord[_DAGNodeT]] = {}
        #self.instance_to_variable_tuple_dict: dict[_InstanceT, tuple[_LazyObjectT, ...]] = {}
        #self.variable_tuple_to_instances_dict: dict[tuple[_LazyObjectT, ...], list[_InstanceT]] = {}
        #self.variable_tuple_to_property_dict: dict[tuple[_LazyObjectT, ...], _LazyObjectT] = {}

    @overload
    def __get__(
        self,
        instance: None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyPropertyDescriptor[_LazyEntityT, _InstanceT]": ...

    @overload
    def __get__(
        self,
        instance: _InstanceT,
        owner: type[_InstanceT] | None = None
    ) -> _LazyEntityT: ...

    def __get__(
        self,
        instance: _InstanceT | None,
        owner: type[_InstanceT] | None = None
    ) -> "LazyPropertyDescriptor[_LazyEntityT, _InstanceT] | _LazyEntityT":
        if instance is None:
            return self

        def restock_method(entity: _LazyEntityT) -> None:
            #parameters = self.property_to_parameters_dict.pop(prop)
            self.parameters_to_entity_bidict.inverse.pop(entity)

        prop = self.instance_to_property_dict[instance]
        if (entity := prop._get()) is None:
            parameters = tuple(
                parameter_descriptor.__get__(instance)
                for parameter_descriptor in self.parameter_descriptors
            )
            if (entity := self.parameters_to_entity_bidict.get(parameters)) is None:
                entity = self.handle_new_property(self.method(*parameters))
                self.parameters_to_entity_bidict[parameters] = entity
                entity._at_restock(restock_method)
            #entity = self.get_entity_from_parameters()
            prop._set(entity)
        return entity

        #def flatten_deepest(obj: tuple | LazyProperty[_LazyEntityT]) -> Generator[LazyProperty[_LazyEntityT], None, None]:
        #    if not isinstance(obj, tuple):
        #        yield obj
        #    else:
        #        for child_obj in obj:
        #            yield from flatten_deepest(child_obj)


        #prop = self.instance_to_property_dict[instance]
        #if (entity := prop._get()) is None:
        #    parameters = self.get_parameters_from_instance(instance)
        #    if (entity := self.parameters_to_entity_bidict.get(parameters)) is None:
        #        entity = self.get_entity_from_parameters(parameters)
        #        entity._bind_children(*flatten_deepest(parameters))
        #        self.parameters_to_entity_bidict[parameters] = entity
        #        #self.property_to_parameters_dict[prop] = parameters
        #        entity._at_restock(restock_method)

        #if (prop := self.values_dict.get(instance)) is None:
        #    parameters = self.get_parameters_from_instance(instance)
        #    if (prop := self.parameters_property_bidict.get(parameters)) is None:
        #        prop = self.get_property_from_parameters(parameters)
        #        prop._bind_children(*flatten_deepest(parameters))
        #        self.parameters_property_bidict[parameters] = prop
        #        #self.property_to_parameters_dict[prop] = parameters
        #        prop._at_restock(restock_method)
        #    self.values_dict[instance] = prop

        #return self.values_dict[instance]._get()

    #    record = super().__get__(instance)
    #    #record = self.instance_to_property_record_dict[instance]
    #    if (prop := record._slot) is None:
    #        parameters = self.get_parameters_from_instance(instance)
    #        if (prop := self.parameters_property_bidict.get(parameters)) is None:
    #            record.bind(*flatten_deepest(parameters))
    #            prop = self.get_property_from_parameters(parameters)
    #            self.parameters_property_bidict[parameters] = prop
    #            #self.property_to_parameters_dict[prop] = parameters
    #            prop._at_restock(restock_method)

    #        record._slot = prop
    #        #record._expired = False
    #    #if (prop := self.instance_to_property_record_dict.get(instance)) is None:
    #    #    prop = self.instance_method(instance)
    #    #    self.instance_to_property_dict[instance] = prop
    #    
    #    return prop
    #    #if (variable_tuple := self.instance_to_variable_tuple_dict.get(instance)) is None:
    #    #    variable_tuple = tuple(
    #    #        variable_descr.__get__(instance)
    #    #        for variable_descr in instance.__class__._PROPERTY_DESCR_TO_VARIABLE_DESCRS[self]
    #    #    )
    #    #    self.instance_to_variable_tuple_dict[instance] = variable_tuple
    #    #self.variable_tuple_to_instances_dict.setdefault(variable_tuple, []).append(instance)
    #    #if (result := self.variable_tuple_to_property_dict.get(variable_tuple)) is None:
    #    #    result = self.method(*(
    #    #        param_descr.__get__(instance)
    #    #        for param_descr in instance.__class__._PROPERTY_DESCR_TO_PARAMETER_DESCRS[self]
    #    #    ))
    #    #    self.variable_tuple_to_property_dict[variable_tuple] = result
    #    #return result

    def initialize(
        self,
        instance: _InstanceT
    ) -> None:
        prop = LazyProperty()
        prop._bind_parameter_children(*(
            parameter_descriptor.__get__(instance)
            for parameter_descriptor in self.parameter_descriptors
        ))
        self.instance_to_property_dict[instance] = prop

    def copy_initialize(
        self,
        dst: _InstanceT,
        src: _InstanceT
    ) -> None:
        self.initialize(dst)
        self.instance_to_property_dict[dst]._set(self.instance_to_property_dict[src]._get())

    def handle_new_property(
        self,
        entity: _LazyEntityT
    ) -> _LazyEntityT:
        return entity

    #def missing(
    #    self,
    #    instance: _InstanceT
    #) -> _DAGNodeT:
    #    def flatten_deepest(obj: tuple | DAGNode) -> Generator[DAGNode, None, None]:
    #        if not isinstance(obj, tuple):
    #            yield obj
    #        else:
    #            for child_obj in obj:
    #                yield from flatten_deepest(child_obj)

    #    def restock_method(prop: _DAGNodeT) -> None:
    #        #parameters = self.property_to_parameters_dict.pop(prop)
    #        self.parameters_property_bidict.inverse.pop(prop)

    #    parameters = self.get_parameters_from_instance(instance)
    #    if (prop := self.parameters_property_bidict.get(parameters)) is None:
    #        prop = self.get_property_from_parameters(parameters)
    #        prop._bind_children(*flatten_deepest(parameters))
    #        self.parameters_property_bidict[parameters] = prop
    #        #self.property_to_parameters_dict[prop] = parameters
    #        prop._at_restock(restock_method)
    #    return prop

    #def __set__(
    #    self,
    #    instance: _InstanceT,
    #    value: Never
    #) -> None:
    #    raise RuntimeError("Attempting to set a readonly lazy property")

    #def _setup_callables(self, descrs: dict[str, LazyDescriptor]) -> None:
    #    #parameter_names = list(inspect.signature(self.method).parameters)
    #    parameter_items: list[tuple[tuple[LazyDescriptor, ...], bool]] = [
    #        (tuple(
    #            descrs[name] for name in re.findall(r"_\w+?_(?=_|$)", name)
    #        ), is_lazy_value)
    #        for name, is_lazy_value in (
    #            (name, False) if re.fullmatch(r"_\w+_", name) else (f"_{name}_", True)
    #            for name in inspect.signature(self.method).parameters
    #        )
    #    ]

    #    def apply_deepest(
    #        callback: Callable[[DAGNode], DAGNode],
    #        obj: tuple | DAGNode
    #    ) -> tuple | DAGNode:
    #        if not isinstance(obj, tuple):
    #            return callback(obj)
    #        return tuple(
    #            apply_deepest(callback, child_obj)
    #            for child_obj in obj
    #        )

    #    def construct_obj_from_descr_chain(
    #        descr_chain: tuple[LazyDescriptor, ...],
    #        obj: tuple | DAGNode
    #    ) -> tuple | DAGNode:
    #        for descr in descr_chain:
    #            if isinstance(descr, LazyObjectDescriptor | LazyPropertyDescriptor):
    #                obj = apply_deepest(lambda instance: descr.__get__(instance), obj)
    #            elif isinstance(descr, LazyCollectionDescriptor):
    #                obj = apply_deepest(lambda instance: tuple(descr.__get__(instance)._node_children), obj)
    #            else:
    #                raise TypeError
    #        return obj
    #        #if not descr_chain:
    #        #    return obj
    #        #descr = descr_chain[0]
    #        #rest_chain = descr_chain[1:]
    #        #if isinstance(descr, LazyObjectDescriptor | LazyPropertyDescriptor):
    #        #    return construct_obj_from_descr_chain(
    #        #        rest_chain,
    #        #        apply_deepest(lambda instance: descr.__get__(instance), obj)
    #        #    )
    #        #if isinstance(descr, LazyCollectionDescriptor):
    #        #    return construct_obj_from_descr_chain(
    #        #        rest_chain,
    #        #        apply_deepest(lambda instance: tuple(descr.__get__(instance)._node_children), obj)
    #        #    )
    #        #raise TypeError

    #    def get_parameters_from_instance(instance: _InstanceT) -> tuple:
    #        return tuple(
    #            construct_obj_from_descr_chain(
    #                descr_chain, instance
    #            )
    #            for descr_chain, _ in parameter_items
    #        )

    #    def get_property_from_parameters(parameters: tuple) -> _DAGNodeT:
    #        return self.method(*(
    #            apply_deepest(lambda lazy_value: lazy_value.value, parameter) if is_lazy_value else parameter
    #            for parameter, (_, is_lazy_value) in zip(parameters, parameter_items, strict=True)
    #        ))

    #    self.get_parameters_from_instance = get_parameters_from_instance
    #    self.get_property_from_parameters = get_property_from_parameters


class LazyWrapper(Generic[_T], LazyObject):
    __slots__ = ("__value",)

    def __init__(self, value: _T):
        super().__init__()
        self.__value: _T = value

    @property
    def value(self) -> _T:
        return self.__value


class LazyObjectRawDescriptor(Generic[_T, _InstanceT], LazyObjectDescriptor[LazyWrapper[_T], _InstanceT]):
    __slots__ = ()

    def __init__(
        self,
        method: Callable[[], _T]
    ) -> None:
        @wraps(method)
        def new_method() -> LazyWrapper[_T]:
            return LazyWrapper(method())

        super().__init__(new_method)


class LazyObjectSharedDescriptor(Generic[_T, _InstanceT, _KeyT], LazyObjectRawDescriptor[_T, _InstanceT]):
    __slots__ = (
        "key",
        "key_to_object_bidict"
    )

    def __init__(
        self,
        method: Callable[[], _T],
        key: Callable[[_T], _KeyT]
    ) -> None:
        super().__init__(method)
        self.key: Callable[[_T], _KeyT] = key
        self.key_to_object_bidict: bidict[_KeyT, LazyWrapper[_T]] = bidict()

    def __set__(
        self,
        instance: _InstanceT,
        obj: _T
    ) -> None:

        def restock_method(cached_object: LazyWrapper[_T]) -> None:
            self.key_to_object_bidict.inverse.pop(cached_object)

        key = self.key(obj)
        if (cached_object := self.key_to_object_bidict.get(key)) is None:
            cached_object = LazyWrapper(obj)
            self.key_to_object_bidict[key] = cached_object
            cached_object._at_restock(restock_method)
        super().__set__(instance, cached_object)


class LazyPropertyRawDescriptor(Generic[_T, _InstanceT], LazyPropertyDescriptor[LazyWrapper[_T], _InstanceT]):
    __slots__ = ("restock_methods",)

    def __init__(
        self,
        method: Callable[..., _T]
    ) -> None:
        @wraps(method)
        def new_method(*args) -> LazyWrapper[_T]:
            return LazyWrapper(method(*args))

        super().__init__(new_method)
        self.restock_methods: list[Callable[[_T], None]] = []

    def restocker(self, restock_method: Callable[[_T], None]) -> Callable[[_T], None]:
        self.restock_methods.append(restock_method)
        return restock_method

    def handle_new_property(
        self,
        entity: LazyWrapper[_T]
    ) -> LazyWrapper[_T]:
        for restock_method in self.restock_methods:
            entity._at_restock(lambda obj: restock_method(obj.value))
        return entity


class LazyPropertySharedDescriptor(Generic[_T, _InstanceT, _KeyT], LazyPropertyRawDescriptor[_T, _InstanceT]):
    __slots__ = (
        "key",
        "key_to_object_bidict"
    )

    def __init__(
        self,
        method: Callable[[], _T],
        key: Callable[[_T], _KeyT]
    ) -> None:
        super().__init__(method)
        self.key: Callable[[_T], _KeyT] = key
        self.key_to_object_bidict: bidict[_KeyT, LazyWrapper[_T]] = bidict()

    def handle_new_property(
        self,
        entity: LazyWrapper[_T]
    ) -> LazyWrapper[_T]:

        def restock_method(cached_object: LazyWrapper[_T]) -> None:
            self.key_to_object_bidict.inverse.pop(cached_object)

        super().handle_new_property(entity)
        key = self.key(entity.value)
        if (cached_object := self.key_to_object_bidict.get(key)) is None:
            cached_object = entity
            self.key_to_object_bidict[key] = cached_object
            cached_object._at_restock(restock_method)
        else:
            entity._restock()
        return cached_object


#class DAGNode(ABC):
#    __slots__ = (
#        "_node_children",
#        #"_node_descendants",
#        "_node_parents",
#        #"_node_ancestors",
#        #"_expired"
#        "_restock_callbacks"
#    )

#    _VACANT_INSTANCES: "ClassVar[list[DAGNode]]"
#    _VARIABLE_DESCRS: "ClassVar[list[LazyObjectDescriptor]]"
#    #_VARIABLE_DESCR_TO_PROPERTY_DESCRS: "ClassVar[dict[LazyObjectDescriptor, tuple[LazyPropertyDescriptor, ...]]]"
#    #_PROPERTY_DESCR_TO_VARIABLE_DESCRS: "ClassVar[dict[LazyPropertyDescriptor, tuple[LazyObjectDescriptor, ...]]]"
#    #_PROPERTY_DESCR_TO_PARAMETER_DESCRS: "ClassVar[dict[LazyPropertyDescriptor, tuple[LazyObjectDescriptor | LazyPropertyDescriptor, ...]]]"
#    #_SLOT_DESCRS: ClassVar[tuple[LazySlot, ...]] = ()

#    #def __init_subclass__(cls) -> None:
#    #    descrs: dict[str, LazyObjectDescriptor | LazyPropertyDescriptor] = {
#    #        name: descr
#    #        for parent_cls in cls.__mro__[::-1]
#    #        for name, descr in parent_cls.__dict__.items()
#    #        if isinstance(descr, LazyObjectDescriptor | LazyPropertyDescriptor)
#    #    }
#    #    #slots: dict[str, LazySlot] = {}
#    #    #for parent_cls in cls.__mro__[::-1]:
#    #    #    for name, method in parent_cls.__dict__.items():
#    #    #        if name in descrs:
#    #    #            assert isinstance(method, LazyObjectDescriptor | LazyPropertyDescriptor)
#    #    #            #cls._check_annotation_matching(method.return_annotation, covered_descr.return_annotation)
#    #    #        if isinstance(method, LazyObjectDescriptor | LazyPropertyDescriptor):
#    #    #            descrs[name] = method
#    #    #        #if (covered_slot := slots.get(name)) is not None:
#    #    #        #    assert isinstance(covered_slot, LazySlot)
#    #    #        #if isinstance(method, LazySlot):
#    #    #        #    slots[name] = method

#    #    property_descr_to_parameter_descrs = {
#    #        descr: tuple(descrs[name] for name in descr.parameters)
#    #        for descr in descrs.values()
#    #        if isinstance(descr, LazyPropertyDescriptor)
#    #    }
#    #    #for descr in descrs.values():
#    #    #    if not isinstance(descr, LazyPropertyDescriptor):
#    #    #        continue
#    #    #    param_descrs: list[LazyObjectDescriptor | LazyPropertyDescriptor] = []
#    #    #    for name in descr.parameters:
#    #    #        param_descr = descrs[name]
#    #    #        #cls._check_annotation_matching(param_descr.return_annotation, param_annotation)
#    #    #        param_descrs.append(param_descr)
#    #    #    property_descr_to_parameter_descrs[descr] = tuple(param_descrs)

#    #    def traverse(property_descr: LazyPropertyDescriptor, occurred: set[LazyObjectDescriptor]) -> Generator[LazyObjectDescriptor, None, None]:
#    #        for name in property_descr.parameters:
#    #            param_descr = descrs[name]
#    #            if isinstance(param_descr, LazyObjectDescriptor):
#    #                yield param_descr
#    #                occurred.add(param_descr)
#    #            else:
#    #                yield from traverse(param_descr, occurred)

#    #    property_descr_to_variable_descrs = {
#    #        property_descr: tuple(traverse(property_descr, set()))
#    #        for property_descr in descrs.values()
#    #        if isinstance(property_descr, LazyPropertyDescriptor)
#    #    }
#    #    variable_descr_to_property_descrs = {
#    #        variable_descr: tuple(
#    #            property_descr
#    #            for property_descr, variable_descrs in property_descr_to_variable_descrs.items()
#    #            if variable_descr in variable_descrs
#    #        )
#    #        for variable_descr in descrs.values()
#    #        if isinstance(variable_descr, LazyObjectDescriptor)
#    #    }

#    #    cls._VACANT_INSTANCES = []
#    #    cls._VARIABLE_DESCR_TO_PROPERTY_DESCRS = variable_descr_to_property_descrs
#    #    cls._PROPERTY_DESCR_TO_VARIABLE_DESCRS = property_descr_to_variable_descrs
#    #    cls._PROPERTY_DESCR_TO_PARAMETER_DESCRS = property_descr_to_parameter_descrs
#    #    #cls._SLOT_DESCRS = tuple(slots.values())
#    #    return super().__init_subclass__()

#    def __new__(cls: type[Self], *args, **kwargs):
#        if (instances := cls._VACANT_INSTANCES):
#            instance = instances.pop()
#            assert isinstance(instance, cls)
#        else:
#            instance = super().__new__(cls)
#        return instance

#    def __init__(self) -> None:
#        super().__init__()
#        #self._nodes: list[LazyObjectNode] = []
#        self._node_children: list[DAGNode] = []
#        #self._node_descendants: list[LazyObject] = [self]
#        self._node_parents: list[DAGNode] = []
#        #self._node_ancestors: list[LazyObject] = [self]
#        self._restock_callbacks: list[Callable[[Self], None]] | None = []

#        #self._expired: bool = False

#    #def __delete__(self) -> None:
#    #    self._restock()

#    def _iter_descendants(self) -> "Generator[DAGNode, None, None]":
#        occurred: set[DAGNode] = set()

#        def iter_descendants(node: DAGNode) -> Generator[DAGNode, None, None]:
#            if node in occurred:
#                return
#            occurred.add(node)
#            yield node
#            for child in node._node_children:
#                yield from iter_descendants(child)

#        yield from iter_descendants(self)
#        #stack: list[LazyObject] = [self]
#        #while stack:
#        #    node = stack.pop()
#        #    if node in occurred:
#        #        continue
#        #    yield node
#        #    occurred.add(node)
#        #    stack.extend(reversed(node._node_children))

#    def _iter_ancestors(self) -> "Generator[DAGNode, None, None]":
#        occurred: set[DAGNode] = set()

#        def iter_ancestors(node: DAGNode) -> Generator[DAGNode, None, None]:
#            if node in occurred:
#                return
#            occurred.add(node)
#            yield node
#            for child in node._node_parents:
#                yield from iter_ancestors(child)

#        yield from iter_ancestors(self)
#        #stack: list[LazyObject] = [self]
#        #occurred: set[LazyObject] = set()
#        #while stack:
#        #    node = stack.pop()
#        #    if node in occurred:
#        #        continue
#        #    yield node
#        #    occurred.add(node)
#        #    stack.extend(reversed(node._node_parents))


#    #@classmethod
#    #def _check_annotation_matching(cls, child_annotation: _Annotation, parent_annotation: _Annotation) -> None:
#    #    error_message = f"Type annotation mismatched: `{child_annotation}` is not compatible with `{parent_annotation}`"
#    #    if isinstance(child_annotation, TypeVar) or isinstance(parent_annotation, TypeVar):
#    #        if isinstance(child_annotation, TypeVar) and isinstance(parent_annotation, TypeVar):
#    #            assert child_annotation == parent_annotation, error_message
#    #        return

#    #    def to_classes(annotation: _Annotation) -> tuple[type, ...]:
#    #        return tuple(
#    #            child.__origin__ if isinstance(child, GenericAlias) else
#    #            Callable if isinstance(child, Callable) else child
#    #            for child in (
#    #                annotation.__args__ if isinstance(annotation, UnionType) else (annotation,)
#    #            )
#    #        )

#    #    assert all(
#    #        any(
#    #            issubclass(child_cls, parent_cls)
#    #            for parent_cls in to_classes(parent_annotation)
#    #        )
#    #        for child_cls in to_classes(child_annotation)
#    #    ), error_message

#    def _bind_children(self, *nodes: "DAGNode"):
#        if (invalid_nodes := [
#            node for node in self._iter_ancestors()
#            if node in nodes
#        ]):
#            raise ValueError(f"Nodes `{invalid_nodes}` have already included `{self}`")
#        self._node_children.extend(nodes)
#        #for ancestor in self._node_ancestors:
#        #    ancestor._node_descendants.update(nodes)
#        for node in nodes:
#            node._node_parents.append(self)
#            #for descendant in self._node_descendants:
#            #    descendant._node_ancestors.append(self)
#        return self

#    def _unbind_children(self, *nodes: "DAGNode"):
#        if (invalid_nodes := [
#            node for node in nodes
#            if node not in self._node_children
#        ]):
#            raise ValueError(f"Nodes `{invalid_nodes}` are not children of `{self}`")
#        #self._node_children.difference_update(nodes)
#        #for ancestor in self._node_ancestors:
#        #    ancestor._node_descendants.difference_update(nodes)
#        for node in nodes:
#            self._node_children.remove(node)
#            node._node_parents.remove(self)
#            if not node._node_parents:
#                node._restock()
#            #for descendant in self._node_descendants:
#            #    descendant._node_ancestors.remove(self)
#        return self

#    #def _copy(self):
#    #    cls = self.__class__
#    #    result = cls.__new__(cls)
#    #    for variable_descr in self._VARIABLE_DESCR_TO_PROPERTY_DESCRS:
#    #        variable = variable_descr.instance_to_object_dict.get(self)
#    #        variable_descr.__set__(result, variable)
#    #    for slot in cls.__slots__:
#    #        result.__setattr__(slot, self.__getattribute__(slot))
#    #    #for slot_descr in self._SLOT_DESCRS:
#    #    #    slot_descr._copy_value(self, result)
#    #    return result

#    def _restock(self) -> None:
#        #for variable_descr in self._VARIABLE_DESCR_TO_PROPERTY_DESCRS:
#        #    variable_descr.__set__(self, None)
#        #for slot_descr in self._SLOT_DESCRS:
#        #    slot_descr.instance_to_value_dict.pop(self, None)
#        for node in self._iter_descendants():
#            if (callbacks := node._restock_callbacks) is None:
#                continue
#            for callback in callbacks:
#                callback(node)
#            callbacks.clear()
#            node.__class__._VACANT_INSTANCES.append(node)

#    def _at_restock(self, callback: Callable[[Self], None]) -> None:
#        if (callbacks := self._restock_callbacks) is not None:
#            callbacks.append(callback)


#class LazyObject(DAGNode):
#    _LAZY_DESCRIPTORS: "ClassVar[list[LazyDescriptor[DAGNode, LazyObject]]]"
#    #_LAZY_COLLECTION_DESCRIPTORS: "ClassVar[list[LazyCollectionDescriptor]]"
#    #_LAZY_PROPERTY_DESCRIPTORS: "ClassVar[list[LazyPropertyDescriptor]]"
#    #_LAZY_DATACLASS: ClassVar[type]

#    def __init_subclass__(cls) -> None:
#        attrs: dict[str, Any] = {
#            name: attr
#            for parent_cls in reversed(cls.__mro__)
#            for name, attr in parent_cls.__dict__.items()
#        }
#        descrs: dict[str, LazyDescriptor] = {
#            name: attr
#            for name, attr in attrs.items()
#            if isinstance(attr, LazyDescriptor)
#        }
#        cls._LAZY_DESCRIPTORS = list(descrs.values())

#        for descr in descrs.values():
#            if not isinstance(descr, LazyPropertyDescriptor):
#                continue
#            descr._setup_callables(descrs)

#        #cls._LAZY_OBJECT_DESCRIPTORS = [
#        #    descr for descr in descrs.values()
#        #    if isinstance(descr, LazyObjectDescriptor)
#        #]
#        #cls._LAZY_COLLECTION_DESCRIPTORS = [
#        #    descr for descr in descrs.values()
#        #    if isinstance(descr, LazyCollectionDescriptor)
#        #]
#        #cls._LAZY_PROPERTY_DESCRIPTORS = [
#        #    descr for descr in descrs.values()
#        #    if isinstance(descr, LazyPropertyDescriptor)
#        #]
#        #for name, descr in descrs.items():
#        #    descr.name = name
#        #cls._LAZY_DATACLASS = make_dataclass(
#        #    f"_{cls.__name__}__dataclass",
#        #    [
#        #        (name, Any, descr.get_field())
#        #        for name, descr in descrs.items()
#        #    ],
#        #    order=True,
#        #    kw_only=True,
#        #    slots=True
#        #)

#    def __init__(self) -> None:
#        super().__init__()
#        #self._lazy_data: Any = self._LAZY_DATACLASS()

#        children: list[DAGNode] = []
#        for descr in self.__class__._LAZY_DESCRIPTORS:
#            if isinstance(descr, LazyObjectDescriptor):
#                if (default_object := descr._default_object) is None:
#                    default_object = descr.method()
#                    default_object._restock_callbacks = None  # Never restock
#                    descr._default_object = default_object
#                descr.initialize(self, default_object)
#                children.append(default_object)
#            elif isinstance(descr, LazyCollectionDescriptor):
#                default_collection = descr.method()
#                descr.initialize(self, default_collection)
#                children.append(default_collection)

#        self._bind_children(*children)

    #@overload
    #def _descr_get(
    #    self,
    #    descr: "LazyObjectDescriptor[_LazyObjectT, _InstanceT]"
    #) -> _LazyObjectT: ...

    #@overload
    #def _descr_get(
    #    self,
    #    descr: "LazyCollectionDescriptor[_DAGNodeT, _InstanceT]"
    #) -> "LazyCollection[_DAGNodeT]": ...

    #@overload
    #def _descr_get(
    #    self,
    #    descr: "LazyPropertyDescriptor[_DAGNodeT, _InstanceT]"
    #) -> "LazyPropertyRecord[_DAGNodeT]": ...

    #def _descr_get(
    #    self,
    #    descr: """Union[
    #        LazyObjectDescriptor[_LazyObjectT, _InstanceT],
    #        LazyCollectionDescriptor[_DAGNodeT, _InstanceT],
    #        LazyPropertyDescriptor[_DAGNodeT, _InstanceT]
    #    ]"""
    #) -> """Union[
    #    _LazyObjectT,
    #    LazyCollection[_DAGNodeT],
    #    LazyPropertyRecord[_DAGNodeT]
    #]""":
    #    return self._lazy_data.__getattribute__(descr.name)

    ##@overload
    #def set_object(
    #    self,
    #    descr: "LazyObjectDescriptor[_LazyObjectT, _InstanceT]",
    #    value: _LazyObjectT
    #) -> None:
    #    self._lazy_data.__setattr__(descr.name, value)

    #@overload
    #def set_object(
    #    self,
    #    descr: "LazyCollectionDescriptor[_DAGNodeT, _InstanceT]",
    #    value: "LazyCollection[_DAGNodeT]"
    #) -> None: ...

    #@overload
    #def set_object(
    #    self,
    #    descr: "LazyPropertyDescriptor[_DAGNodeT, _InstanceT]",
    #    value: "LazyPropertyRecord[_DAGNodeT]"
    #) -> None: ...

    #def set_object(
    #    self,
    #    descr: """Union[
    #        LazyObjectDescriptor[_LazyObjectT, _InstanceT],
    #        LazyPropertyDescriptor[_DAGNodeT, _InstanceT]
    #    ]""",
    #    value: """Union[
    #        _LazyObjectT,
    #        LazyPropertyRecord[_DAGNodeT]
    #    ]"""
    #) -> None:
    #    return self._lazy_data.__setattr__(descr.name, value)


#class LazyCollection(Generic[_DAGNodeT], DAGNode):
#    __slots__ = ()
#
#    def __len__(self) -> int:
#        return self._node_children.__len__()
#
#    @overload
#    def __getitem__(self, index: slice) -> list[_DAGNodeT]:
#        ...
#
#    @overload
#    def __getitem__(self, index: int) -> _DAGNodeT:
#        ...
#
#    def __getitem__(self, index: slice | int) -> list[_DAGNodeT] | _DAGNodeT:
#        return self._node_children.__getitem__(index)
#
#    def add(self, *nodes: _DAGNodeT):
#        self._bind_children(*nodes)
#        return self
#
#    def remove(self, *nodes: _DAGNodeT):
#        self._unbind_children(*nodes)
#        return self


#class LazyPropertyRecord(Generic[_DAGNodeT]):
#    #__slots__ = ()
#    __slots__ = ("_slot",)
#
#    def __init__(self) -> None:
#        self._slot: _DAGNodeT | None = None

    #def get(self) -> _DAGNodeT | None:
    #    if not self._node_children:
    #        return None
    #    return self._node_children[0]

    #def set(self, node: _DAGNodeT) -> None:
    #    if self.get() is node:
    #        return
    #    if self._node_children:
    #        self._unbind_children(self._node_children[0])
    #    self._bind_children(node)

    #def bind(self, *nodes: DAGNode) -> None:
    #    self._bind_children(*nodes)

    #def expire(self) -> None:
    #    self._unbind_children(*self._node_children)

    #def __init__(self) -> None:
    #    self._node: _DAGNodeT | None = None
    #    #self._expired: bool = True

#    __slots__ = ("__storage",)

#    def __init__(self, storage: list[_LazyObjectT] | None = None):
#        if storage is None:
#            storage = []
#        self.__storage: list[_LazyObjectT] = storage

#    def __iter__(self) -> "Iterator[_LazyObjectT]":
#        return iter(self.__storage)

#    @overload
#    def __getitem__(self, index: int) -> "_LazyObjectT": ...

#    @overload
#    def __getitem__(self, index: slice) -> "list[_LazyObjectT]": ...

#    def __getitem__(self, index: int | slice) -> "_LazyObjectT | list[_LazyObjectT]":
#        return self.__storage.__getitem__(index)

#    def add(self, *lazy_objects: _LazyObjectT) -> "LazyCollection[_LazyObjectT]":
#        storage = self.__storage[:]
#        storage.extend(lazy_objects)
#        return LazyCollection(storage)

#    def remove(self, *lazy_objects: _LazyObjectT) -> "LazyCollection[_LazyObjectT]":
#        storage = self.__storage[:]
#        for lazy_object in lazy_objects:
#            storage.remove(lazy_object)
#        return LazyCollection(storage)


#class LazyDescriptor(Generic[_LazyObjectT]):
#    def __init__(self, method: Callable[..., _LazyObjectT]):
#        #self.name: str = method.__name__
#        self.method: Callable[..., _LazyObjectT] = method
#        #self.signature: inspect.Signature = inspect.signature(method)
#        #self.restock_method: Callable[[_T], None] | None = None

    #@property
    #def parameters(self) -> dict[str, _Annotation]:
    #    return {
    #        f"_{parameter.name}_": parameter.annotation
    #        for parameter in list(self.signature.parameters.values())
    #    }

    #@property
    #def return_annotation(self) -> _Annotation:
    #    return self.signature.return_annotation

    #def _restock(self, data: _T) -> None:
    #    if self.restock_method is not None:
    #        self.restock_method(data)
    #    elif isinstance(data, LazyBase):
    #        data._restock()

    #def restocker(self, restock_method: Callable[[_T], None]) -> Callable[[_T], None]:
    #    self.restock_method = restock_method
    #    return restock_method


#class LazyDescriptor(Generic[_DAGNodeT, _InstanceT]):
#    def __init__(self, name: str) -> None:
#        self.name: str = name
#        #self.default_factory: Callable[..., _DAGNodeT] = default_factory
#        #self.name: str = init_method.__name__
#        self.instance_to_node_dict: dict[_InstanceT, _DAGNodeT] = {}

#    @overload
#    def __get__(
#        self,
#        instance: None,
#        owner: type[_InstanceT] | None = None
#    ): ...  # TODO: typing

#    @overload
#    def __get__(
#        self,
#        instance: _InstanceT,
#        owner: type[_InstanceT] | None = None
#    ) -> _DAGNodeT: ...

#    def __get__(
#        self,
#        instance: _InstanceT | None,
#        owner: type[_InstanceT] | None = None
#    )  | _DAGNodeT:
#        if instance is None:
#            return self
#        if (node := self.get(instance)) is None:
#            node = self.missing(instance)
#            self.instance_to_node_dict[instance] = node
#        return node

#    def __set__(
#        self,
#        instance: _InstanceT,
#        value: _DAGNodeT
#    ) -> None:
#        self.instance_to_node_dict[instance] = value

#    def initialize(
#        self,
#        instance: _InstanceT,
#        value: _DAGNodeT
#    ) -> None:
#        assert instance not in self.instance_to_node_dict
#        self.instance_to_node_dict[instance] = value

#    def pop(
#        self,
#        instance: _InstanceT
#    ) -> _DAGNodeT:
#        return self.instance_to_node_dict.pop(instance)

#    def get(
#        self,
#        instance: _InstanceT
#    ) -> _DAGNodeT | None:
#        return self.instance_to_node_dict.get(instance)

#    def missing(
#        self,
#        instance: _InstanceT
#    ) -> _DAGNodeT:
#        raise KeyError

#    #def get_field(self) -> Any:
#    #    pass


#class LazyObjectDescriptor(LazyDescriptor[_LazyObjectT, _InstanceT]):
#    def __init__(
#        self,
#        method: Callable[[], _LazyObjectT]
#    ) -> None:
#        super().__init__(method.__name__)
#        self.method: Callable[[], _LazyObjectT] = method
#        self._default_object: _LazyObjectT | None = None

        #def default_factory() -> _LazyObjectT:
        #    if (default_object := self._default_object) is None:
        #        default_object = method()
        #        default_object._restock_callbacks = None  # Never restock
        #    self._default_object = default_object
        #    return default_object

        #super().__init__(method)
        #assert not self.parameters
        #self.method: Callable[[], _LazyObjectT] = method
        #self.object_type: type[_LazyObjectT] = _get_type_from_annotation(
        #    inspect.signature(method).return_annotation
        #)
        #self.name: str = method.__name__
        #self.instance_to_object_dict: dict[_InstanceT, _LazyObjectT] = {}
        #self.variable_to_instances_dict: dict[_LazyObjectT, list[_InstanceT]] = {}

    #@overload
    #def __get__(
    #    self,
    #    instance: None,
    #    owner: type[_InstanceT] | None = None
    #): ...  # TODO: typing

    #@overload
    #def __get__(
    #    self,
    #    instance: _InstanceT,
    #    owner: type[_InstanceT] | None = None
    #) -> _LazyObjectT: ...

    #def __get__(
    #    self,
    #    instance: _InstanceT | None,
    #    owner: type[_InstanceT] | None = None
    #)  | _LazyObjectT:
    #    if instance is None:
    #        return self
    #    return instance._descr_get(self)
    #    #if (variable := self.instance_to_object_dict.get(instance)) is None:
    #    #    variable = self._get_initial_value()
    #    #    self.instance_to_object_dict[instance] = variable
    #    #return variable
    #    #return self.instance_to_object_dict.get(instance, self.default_variable)

    #def __set__(
    #    self,
    #    instance: _InstanceT,
    #    lazy_object: _LazyObjectT
    #) -> None:
    #    #assert isinstance(variable, LazyWrapper)
    #    #self._set_data(instance, variable)
    #    old_object = self.__get__(instance)
    #    instance._unbind_children(old_object)
    #    for descr in instance.__class__._LAZY_DESCRIPTORS:
    #        if not isinstance(descr, LazyPropertyDescriptor):
    #            continue
    #        if (expired_node := descr.get(instance)) is None:
    #            continue
    #        #record: LazyPropertyRecord = descr.__get__(instance)
    #        expired_node._unbind_children(*expired_node._node_children)
    #    #instance.set_object(self, lazy_object)
    #    super().__set__(instance, lazy_object)
    #    #self.instance_to_node_dict[instance] = lazy_object
    #    instance._bind_children(lazy_object)

        #if self.instance_to_object_dict.get(instance) is variable:
        #    return
        #self._clear_instance_variable(instance)
        #for property_descr in instance.__class__._VARIABLE_DESCR_TO_PROPERTY_DESCRS[self]:
        #    property_descr._clear_instance_variable_tuple(instance)
        #if variable is None:
        #    return
        #self.instance_to_object_dict[instance] = variable
        #self.variable_to_instances_dict.setdefault(variable, []).append(instance)

    #def get_field(self) -> Any:
    #    def factory() -> _LazyObjectT:
    #        if (default_object := self._default_object) is None:
    #            default_object = self.method()
    #            default_object._restock_callbacks = None  # Never restock
    #        self._default_object = default_object
    #        return default_object
    #    return field(default_factory=factory)

    #def _get_default_object(self) -> _LazyObjectT:
    #    if (default_object := self._default_object) is None:
    #        default_object = self.method()
    #        self._default_object = default_object
    #    return default_object

    #@property
    #def default_variable(self) -> _LazyObjectT:
    #    if self._default_object is None:
    #        self._default_object = self.method()
    #    return self._default_object

    #def _get_data(self, instance: _InstanceT) -> LazyWrapper[_T]:
    #    return self.instance_to_object_dict.get(instance, self.default_variable)

    #def _set_data(self, instance: _InstanceT, variable: LazyWrapper[_T] | None) -> None:
    #    if self.instance_to_object_dict.get(instance) is variable:
    #        return
    #    self._clear_instance_variable(instance)
    #    for property_descr in instance.__class__._VARIABLE_DESCR_TO_PROPERTY_DESCRS[self]:
    #        property_descr._clear_instance_variable_tuple(instance)
    #    if variable is None:
    #        return
    #    self.instance_to_object_dict[instance] = variable
    #    self.variable_to_instances_dict.setdefault(variable, []).append(instance)

    #def _clear_instance_variable(self, instance: _InstanceT) -> None:
    #    if (variable := self.instance_to_object_dict.pop(instance, None)) is None:
    #        return
    #    self.variable_to_instances_dict[variable].remove(instance)
    #    if self.variable_to_instances_dict[variable]:
    #        return
    #    self.variable_to_instances_dict.pop(variable)
    #    variable._restock()  # TODO
    #    #self._restock(variable.data)  # TODO


#class LazyCollectionDescriptor(Generic[_DAGNodeT, _InstanceT], LazyDescriptor[LazyCollection[_DAGNodeT], _InstanceT]):
#    def __init__(
#        self,
#        method: Callable[[], LazyCollection[_DAGNodeT]]
#    ) -> None:
#        super().__init__(method.__name__)
#        self.method: Callable[[], LazyCollection[_DAGNodeT]] = method
        #self.object_type: type[_DAGNodeT] = _get_type_from_annotation(
        #    inspect.signature(method).return_annotation.__args__[0]
        #)
        #self.instance_to_collection_dict: dict[_InstanceT, LazyCollection[_DAGNodeT]] = {}

    #@overload
    #def __get__(
    #    self,
    #    instance: None,
    #    owner: type[_InstanceT] | None = None
    #): ...  # TODO: typing

    #@overload
    #def __get__(
    #    self,
    #    instance: _InstanceT,
    #    owner: type[_InstanceT] | None = None
    #) -> LazyCollection[_DAGNodeT]: ...

    #def __get__(
    #    self,
    #    instance: _InstanceT | None,
    #    owner: type[_InstanceT] | None = None
    #)  | LazyCollection[_DAGNodeT]:
    #    if instance is None:
    #        return self
    #    return instance._descr_get(self)

    #def __set__(
    #    self,
    #    instance: _InstanceT,
    #    value: Never
    #) -> None:
    #    raise RuntimeError("Attempting to set a collection object directly")

    #def get_field(self) -> Any:
    #    def factory() -> LazyCollection[_DAGNodeT]:
    #        return self.method()
    #    return field(default_factory=factory)


#class LazyPropertyDescriptor(LazyDescriptor[_DAGNodeT, _InstanceT]):
    #def __init__(
    #    self,
    #    method: Callable[..., _DAGNodeT]
    #) -> None:
    #    #def default_factory() -> LazyPropertyRecord[_DAGNodeT]:
    #    #    return LazyPropertyRecord()

    #    super().__init__(method.__name__)
    #    #super().__init__(method)
    #    #assert self.parameters

    #    #parameter_items = [
    #    #    (name, False) if re.fullmatch(r"_\w+_", name := parameter.name) else (f"_{name}_", True)
    #    #    for parameter in inspect.signature(method).parameters.values()
    #    #]
    #    #parameter_tuple = tuple(parameter for parameter, _ in parameter_items)
    #    #is_lazy_value_tuple = tuple(is_lazy_value for _, is_lazy_value in parameter_items)

    #    #def new_method(*args) -> _DAGNodeT:
    #    #    return method(*(
    #    #        arg.value if is_lazy_value else arg
    #    #        for arg, is_lazy_value in zip(args, is_lazy_value_tuple, strict=True)
    #    #    ))

    #    #self.method: Callable[..., _DAGNodeT] = method
    #    #self.object_type: type[_DAGNodeT] = _get_type_from_annotation(
    #    #    inspect.signature(method).return_annotation
    #    #)
    #    self.method: Callable[..., _DAGNodeT] = method
    #    self.get_parameters_from_instance: Callable[[_InstanceT], tuple] = NotImplemented
    #    self.get_property_from_parameters: Callable[[tuple], _DAGNodeT] = NotImplemented
    #    #self.parameters: tuple[str, ...] = parameter_tuple
    #    self.parameters_property_bidict: bidict[tuple, _DAGNodeT] = bidict()
    #    #self.property_to_parameters_dict: dict[_DAGNodeT, tuple] = {}
    #    #self.instance_to_property_record_dict: dict[_InstanceT, LazyPropertyRecord[_DAGNodeT]] = {}
    #    #self.instance_to_variable_tuple_dict: dict[_InstanceT, tuple[_LazyObjectT, ...]] = {}
    #    #self.variable_tuple_to_instances_dict: dict[tuple[_LazyObjectT, ...], list[_InstanceT]] = {}
    #    #self.variable_tuple_to_property_dict: dict[tuple[_LazyObjectT, ...], _LazyObjectT] = {}

    #@overload
    #def __get__(
    #    self,
    #    instance: None,
    #    owner: type[_InstanceT] | None = None
    #): ...

    #@overload
    #def __get__(
    #    self,
    #    instance: _InstanceT,
    #    owner: type[_InstanceT] | None = None
    #) -> _DAGNodeT: ...

    #def __get__(
    #    self,
    #    instance: _InstanceT | None,
    #    owner: type[_InstanceT] | None = None
    #)  | _DAGNodeT:
    #    if instance is None:
    #        return self

    #    def flatten_deepest(obj: tuple | DAGNode) -> Generator[DAGNode, None, None]:
    #        if not isinstance(obj, tuple):
    #            yield obj
    #        else:
    #            for child_obj in obj:
    #                yield from flatten_deepest(child_obj)

    #    def restock_method(prop: _DAGNodeT) -> None:
    #        #parameters = self.property_to_parameters_dict.pop(prop)
    #        self.parameters_property_bidict.inverse.pop(prop)

    #    record = super().__get__(instance)
    #    #record = self.instance_to_property_record_dict[instance]
    #    if (prop := record._slot) is None:
    #        parameters = self.get_parameters_from_instance(instance)
    #        if (prop := self.parameters_property_bidict.get(parameters)) is None:
    #            record.bind(*flatten_deepest(parameters))
    #            prop = self.get_property_from_parameters(parameters)
    #            self.parameters_property_bidict[parameters] = prop
    #            #self.property_to_parameters_dict[prop] = parameters
    #            prop._at_restock(restock_method)

    #        record._slot = prop
    #        #record._expired = False
    #    #if (prop := self.instance_to_property_record_dict.get(instance)) is None:
    #    #    prop = self.instance_method(instance)
    #    #    self.instance_to_property_dict[instance] = prop
    #    
    #    return prop
    #    #if (variable_tuple := self.instance_to_variable_tuple_dict.get(instance)) is None:
    #    #    variable_tuple = tuple(
    #    #        variable_descr.__get__(instance)
    #    #        for variable_descr in instance.__class__._PROPERTY_DESCR_TO_VARIABLE_DESCRS[self]
    #    #    )
    #    #    self.instance_to_variable_tuple_dict[instance] = variable_tuple
    #    #self.variable_tuple_to_instances_dict.setdefault(variable_tuple, []).append(instance)
    #    #if (result := self.variable_tuple_to_property_dict.get(variable_tuple)) is None:
    #    #    result = self.method(*(
    #    #        param_descr.__get__(instance)
    #    #        for param_descr in instance.__class__._PROPERTY_DESCR_TO_PARAMETER_DESCRS[self]
    #    #    ))
    #    #    self.variable_tuple_to_property_dict[variable_tuple] = result
    #    #return result

    #def missing(
    #    self,
    #    instance: _InstanceT
    #) -> _DAGNodeT:
    #    def flatten_deepest(obj: tuple | DAGNode) -> Generator[DAGNode, None, None]:
    #        if not isinstance(obj, tuple):
    #            yield obj
    #        else:
    #            for child_obj in obj:
    #                yield from flatten_deepest(child_obj)

    #    def restock_method(prop: _DAGNodeT) -> None:
    #        #parameters = self.property_to_parameters_dict.pop(prop)
    #        self.parameters_property_bidict.inverse.pop(prop)

    #    parameters = self.get_parameters_from_instance(instance)
    #    if (prop := self.parameters_property_bidict.get(parameters)) is None:
    #        prop = self.get_property_from_parameters(parameters)
    #        prop._bind_children(*flatten_deepest(parameters))
    #        self.parameters_property_bidict[parameters] = prop
    #        #self.property_to_parameters_dict[prop] = parameters
    #        prop._at_restock(restock_method)
    #    return prop

    #def __set__(
    #    self,
    #    instance: _InstanceT,
    #    value: Never
    #) -> None:
    #    raise RuntimeError("Attempting to set a readonly lazy property")

    #def _setup_callables(self, descrs: dict[str, LazyDescriptor]) -> None:
    #    #parameter_names = list(inspect.signature(self.method).parameters)
    #    parameter_items: list[tuple[tuple[LazyDescriptor, ...], bool]] = [
    #        (tuple(
    #            descrs[name] for name in re.findall(r"_\w+?_(?=_|$)", name)
    #        ), is_lazy_value)
    #        for name, is_lazy_value in (
    #            (name, False) if re.fullmatch(r"_\w+_", name) else (f"_{name}_", True)
    #            for name in inspect.signature(self.method).parameters
    #        )
    #    ]

    #    def apply_deepest(
    #        callback: Callable[[DAGNode], DAGNode],
    #        obj: tuple | DAGNode
    #    ) -> tuple | DAGNode:
    #        if not isinstance(obj, tuple):
    #            return callback(obj)
    #        return tuple(
    #            apply_deepest(callback, child_obj)
    #            for child_obj in obj
    #        )

    #    def construct_obj_from_descr_chain(
    #        descr_chain: tuple[LazyDescriptor, ...],
    #        obj: tuple | DAGNode
    #    ) -> tuple | DAGNode:
    #        for descr in descr_chain:
    #            if isinstance(descr, LazyObjectDescriptor | LazyPropertyDescriptor):
    #                obj = apply_deepest(lambda instance: descr.__get__(instance), obj)
    #            elif isinstance(descr, LazyCollectionDescriptor):
    #                obj = apply_deepest(lambda instance: tuple(descr.__get__(instance)._node_children), obj)
    #            else:
    #                raise TypeError
    #        return obj
    #        #if not descr_chain:
    #        #    return obj
    #        #descr = descr_chain[0]
    #        #rest_chain = descr_chain[1:]
    #        #if isinstance(descr, LazyObjectDescriptor | LazyPropertyDescriptor):
    #        #    return construct_obj_from_descr_chain(
    #        #        rest_chain,
    #        #        apply_deepest(lambda instance: descr.__get__(instance), obj)
    #        #    )
    #        #if isinstance(descr, LazyCollectionDescriptor):
    #        #    return construct_obj_from_descr_chain(
    #        #        rest_chain,
    #        #        apply_deepest(lambda instance: tuple(descr.__get__(instance)._node_children), obj)
    #        #    )
    #        #raise TypeError

    #    def get_parameters_from_instance(instance: _InstanceT) -> tuple:
    #        return tuple(
    #            construct_obj_from_descr_chain(
    #                descr_chain, instance
    #            )
    #            for descr_chain, _ in parameter_items
    #        )

    #    def get_property_from_parameters(parameters: tuple) -> _DAGNodeT:
    #        return self.method(*(
    #            apply_deepest(lambda lazy_value: lazy_value.value, parameter) if is_lazy_value else parameter
    #            for parameter, (_, is_lazy_value) in zip(parameters, parameter_items, strict=True)
    #        ))

    #    self.get_parameters_from_instance = get_parameters_from_instance
    #    self.get_property_from_parameters = get_property_from_parameters


    #def _clear_instance_variable_tuple(self, instance: _InstanceT) -> None:
    #    if (variable_tuple := self.instance_to_variable_tuple_dict.pop(instance, None)) is None:
    #        return
    #    self.variable_tuple_to_instances_dict[variable_tuple].remove(instance)
    #    if self.variable_tuple_to_instances_dict[variable_tuple]:
    #        return
    #    self.variable_tuple_to_instances_dict.pop(variable_tuple)
    #    if (property_ := self.variable_tuple_to_property_dict.pop(variable_tuple, None)) is None:
    #        return
    #    property_._restock()
    #    #self._restock(property_)

    #def get_field(self) -> Any:
    #    def factory() -> LazyPropertyRecord[_DAGNodeT]:
    #        return LazyPropertyRecord()
    #    return field(default_factory=factory)


class lazy_object(Generic[_LazyObjectT, _InstanceT]):
    __slots__ = ()

    def __new__(cls, method: Callable[[], _LazyObjectT]) -> LazyObjectDescriptor[_LazyObjectT, _InstanceT]:
        return LazyObjectDescriptor(method)


class lazy_collection(Generic[_LazyEntityT, _InstanceT]):
    __slots__ = ()

    def __new__(cls, method: Callable[[], LazyCollection[_LazyEntityT]]) -> LazyCollectionDescriptor[_LazyEntityT, _InstanceT]:
        return LazyCollectionDescriptor(method)


class lazy_property(Generic[_LazyEntityT, _InstanceT]):
    __slots__ = ()

    def __new__(cls, method: Callable[..., _LazyEntityT]) -> LazyPropertyDescriptor[_LazyEntityT, _InstanceT]:
        return LazyPropertyDescriptor(method)


class lazy_object_raw(Generic[_T, _InstanceT]):
    __slots__ = ()

    def __new__(cls, method: Callable[[], _T]) -> LazyObjectRawDescriptor[_T, _InstanceT]:
        return LazyObjectRawDescriptor(method)


class lazy_object_shared(Generic[_T, _InstanceT, _KeyT]):
    __slots__ = ("key",)

    def __init__(self, key: Callable[[_T], _KeyT]):
        self.key: Callable[[_T], _KeyT] = key

    def __call__(self, method: Callable[[], _T]) -> LazyObjectSharedDescriptor[_T, _InstanceT, _KeyT]:
        return LazyObjectSharedDescriptor(method, self.key)


class lazy_property_raw(Generic[_T, _InstanceT]):
    __slots__ = ()

    def __new__(cls, method: Callable[..., _T]) -> LazyPropertyRawDescriptor[_T, _InstanceT]:
        return LazyPropertyRawDescriptor(method)


class lazy_property_shared(Generic[_T, _InstanceT, _KeyT]):
    __slots__ = ("key",)

    def __init__(self, key: Callable[[_T], _KeyT]):
        self.key: Callable[[_T], _KeyT] = key

    def __call__(self, method: Callable[..., _T]) -> LazyPropertySharedDescriptor[_T, _InstanceT, _KeyT]:
        return LazyPropertySharedDescriptor(method, self.key)
