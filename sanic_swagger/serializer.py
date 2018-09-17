import sys
from datetime import date, datetime
from enum import EnumMeta
from functools import singledispatch
from pprint import pprint
from typing import (
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    Sequence,
    Set,
    Union,
)

import attr

from .doc import ModelMeta
from .options import metadata_aliases

# Check if we are running on Python 3.7
if sys.version_info[:3] >= (3, 7, 0):
    GenericMeta = type
else:
    from typing import GenericMeta  # noqa

required_fields = {}
object_definitions = {}


def serialize(field, model=None):
    if hasattr(field, 'type'):
        return _merge_metadata(
            _serialize_type(field.type, model), field, model
        )
    else:
        return _serialize_type(field, model)


def _create_definition(func):
    def wrapper(type_, model):
        # if model is None:
        #     return func(type_, model)
        output = func(type_, model)
        object_definitions[type_] = output
        return {
            'type': output.get('type'),
            'format': output.get('format', None),
            '$ref': '#/definitions/{}'.format(type_.__name__),
        }

    return wrapper


def _camel_case(snake_str):
    # from https://stackoverflow.com/a/42450252
    first, *others = snake_str.split('_')
    return ''.join([first.lower(), *map(str.title, others)])


def _raise_other_encouraged_type_exception(simple_type, *encouraged_type):
    if len(encouraged_type) > 1:
        encouraged = ', '.join([str(t._name) for t in encouraged_type])
    else:
        encouraged = str(encouraged_type[0])
    raise TypeError(
        'It is encouraged to use \'{}\' instead of \'{}\''.format(
            encouraged, simple_type.__name__
        )
    )


def _merge_metadata(data, field, model):
    if data.get('type', None) is None:
        return data

    for key in metadata_aliases['all']:
        if key in field.metadata:
            data[_camel_case(key)] = field.metadata.get(key)

    if data['type'] in metadata_aliases:
        for key in metadata_aliases[data['type']]:
            if key in field.metadata:
                data[_camel_case(key)] = field.metadata.get(key)

    if data.get('required', False):
        del data['required']
        if model is not None:
            if model in required_fields:
                required_fields[model].append(field.name)
            else:
                required_fields[model] = [field.name]
    return data


@singledispatch
def _serialize_type(type_, model):
    print("_serialize_type(type_, model)")
    print("type_ = {}".format(type_))
    pprint(vars(type_))
    print("model = {}".format(model))
    
    if type_._name == 'Any':
        return {'type': 'object'}  # TODO is this the best way to deal with?
    elif type_.__origin__ == Union:
        if len(type_.__args__) == 2 and type(None) == type_.__args__[1]:
            output = _serialize_type(type_.__args__[0], model)
            output.update({'nullable': True})
            return output
        else:
            return {
                'oneOf': [
                    _serialize_type(arg, model) for arg in type_.__args__
                ]
            }
    else:
        raise TypeError('{} is not supported'.format(type_))


@_serialize_type.register(EnumMeta)  # for enums
@_create_definition
def _serialize_enum_meta(type_, model):
    """
    Note: Remember that this function is decorated with _create_definition.
          So its outputs when calling this function are those of the wrapped
          output.
    """
    print("_serialize_enum_meta(type_, model)")
    print("type_ = {}".format(type_))
    pprint(vars(type_))
    print("model = {}".format(model))
    choices = [e.value for e in type_]
    output = _serialize_type(type(choices[0]), model)
    output.update({'enum': choices})
    return output


@_serialize_type.register(GenericMeta)  # for typing generics
def _serialize_generic_meta(type_, model):
    print("_serialize_generic_meta(type_, model)")
    print("type_ = {}".format(type_))
    pprint(vars(type_))
    print("model = {}".format(model))
    if type_._name in ('List', 'Set', 'Sequence', 'Collection', 'Iterable'):
        print("type_ is an array (or more accurately its _name is)")
        output = {'type': 'array'}
        if len(type_.__args__):
            output.update(
                {'items': {**_serialize_type(type_.__args__[0], model)}}
            )
        return output
    elif type_._name in ('Dict', 'Mapping'):
        print("type_ is an object (or more accurately its _name is)")
        output = {'type': 'object'}
        if type_.__args__:
            output.update(
                {
                    'properties': {
                        'key': _serialize_type(type_.__args__[0], model),
                        'value': _serialize_type(type_.__args__[1], model),
                    }
                }
            )
        return output
    else:
        raise TypeError('{} is not supported'.format(type_))


@_serialize_type.register(ModelMeta)  # for recursive types
@_create_definition
def _serialize_custom_objects(type_, model):
    """
    Note: Remember that this function is decorated with _create_definition.
          So its outputs when calling this function are those of the wrapped
          output.
    """
    print("_serialize_custom_objects(type_, model)")
    print("type_ = {}".format(type_))
    pprint(vars(type_))
    print("model = {}".format(model))
    output = {
        'type': 'object',
        'properties': {
            str(field.name): serialize(field, type_)
            for field in attr.fields(type_)
        },
    }
    if model is None and type_ in required_fields:
        output.update({'required': required_fields[type_]})
    return output


@_serialize_type.register(type)
def _serialize_raw_type_information(type_, model):
    if type_ == int:
        return {'type': 'integer', 'format': 'int64'}
    elif type_ == float:
        return {'type': 'number', 'format': 'double'}
    elif type_ == str:
        return {'type': 'string'}
    elif type_ == bool:
        return {'type': 'boolean'}
    elif type_ == date:
        return {'type': 'string', 'format': 'date'}
    elif type_ == datetime:
        return {'type': 'string', 'format': 'date-time'}
    elif type_ == bytes:
        return {'type': 'string', 'format': 'byte'}
    elif type_ in (list, set, tuple):
        _raise_other_encouraged_type_exception(type_, Collection, Iterable,
                                               List, Sequence, Set)
    elif type_ == dict:
        _raise_other_encouraged_type_exception(type_, Dict, Mapping)
    else:
        if attr.has(type_):  # for recursive types, just like ModelMeta
            return _create_definition(_serialize_custom_objects)(type_, model)
        raise TypeError('{} is not supported'.format(type_))
