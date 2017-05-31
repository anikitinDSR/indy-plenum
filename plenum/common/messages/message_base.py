from operator import itemgetter

import itertools
from typing import Mapping
from collections import OrderedDict
from plenum.common.constants import OP_FIELD_NAME
from plenum.common.messages.fields import FieldValidator

class MessageValidator(FieldValidator):

    # the schema has to be an ordered iterable because the message class
    # can be create with positional arguments __init__(*args)
    schema = ()
    optional = False

    def validate(self, dct):
        self._validate_fields_with_schema(dct, self.schema)
        self._validate_message(dct)

    def _validate_fields_with_schema(self, dct, schema):
        if not isinstance(dct, dict):
            self._raise_invalid_type(dct)
        schema_dct = dict(schema)
        required_fields = filter(lambda x: not x[1].optional, schema)
        required_field_names = map(lambda x: x[0], required_fields)
        missed_required_fields = set(required_field_names) - set(dct)
        if missed_required_fields:
            self._raise_missed_fields(*missed_required_fields)
        for k, v in dct.items():
            if k not in schema_dct:
                self._raise_unknown_fields(k, v)
            validation_error = schema_dct[k].validate(v)
            if validation_error:
                self._raise_invalid_fields(k, v, validation_error)


    def _raise_invalid_type(self, dct):
        raise TypeError("validation error: invalid type {}, dict expected"
                        .format(type(dct)))

    def _validate_message(self, dct):
        return None

    def _raise_missed_fields(self, *fields):
        raise TypeError("validation error: missed fields "
                        "{}".format(', '.join(map(str, fields))))

    def _raise_unknown_fields(self, field, value):
        raise TypeError("validation error: unknown field "
                        "({}={})".format(field, value))

    def _raise_invalid_fields(self, field, value, reason):
        raise TypeError("validation error: {} "
                        "({}={})".format(reason, field, value))

    def _raise_invalid_message(self, reason):
        raise TypeError("validation error: {}".format(reason))


class MessageBase(Mapping, MessageValidator):
    typename = None

    def __init__(self, *args, **kwargs):
        assert not (args and kwargs), \
            '*args, **kwargs cannot be used together'

        if kwargs:
            # op field is not required since there is self.typename
            kwargs.pop(OP_FIELD_NAME, None)

        argsLen = len(args or kwargs)
        assert argsLen == len(self.schema), \
            "number of parameters should be the " \
            "same as a number of fields in schema, but it was {}" \
                .format(argsLen)

        input_as_dict = kwargs if kwargs else self._join_with_schema(args)

        self.validate(input_as_dict)

        self._fields = OrderedDict((name, input_as_dict[name]) for name, _ in self.schema)

    def _join_with_schema(self, args):
        return dict(zip(map(itemgetter(0), self.schema), args))

    def __getattr__(self, item):
        return self._fields[item]

    def __getitem__(self, key):
        values = list(self._fields.values())
        if isinstance(key, slice):
            return values[key]
        if isinstance(key, int):
            return values[key]
        raise TypeError("Invalid argument type.")

    def _asdict(self):
        """
        Legacy form TaggedTuple
        """
        return self.__dict__

    @property
    def __dict__(self):
        """
        Return a dictionary form.
        """
        m = self._fields.copy()
        m[OP_FIELD_NAME] = self.typename
        m.move_to_end(OP_FIELD_NAME, False)
        return m

    @property
    def __name__(self):
        return self.typename

    def __iter__(self):
        return self._fields.values().__iter__()

    def __len__(self):
        return len(self._fields)

    def items(self):
        return self._fields.items()

    def keys(self):
        return self._fields.keys()

    def values(self):
        return self._fields.values()

    def __str__(self):
        return "{}{}".format(self.typename, dict(self.items()))