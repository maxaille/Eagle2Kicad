""" Converts all attribute values to a string """
from builtins import str

import unicodedata

def stringify_attributes(attributes):
    """ Converts all attribute values to a string """
    attrs = {}
    for name, value in attributes.items():
        try:
            attrs[name] = str(value)
        except UnicodeEncodeError:
            attrs[name] = unicodedata.normalize('NFKD', value)
    return attrs