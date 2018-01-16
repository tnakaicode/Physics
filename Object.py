import pyparsing as p
import sys, time, os
from collections import OrderedDict

#sys.setrecursionlimit(10000)

from .base import Grammar

class ObjectRepository(OrderedDict):
    """
    This class represents a TICRA Object Repository (.tor) file.
    """

    def load(self, filename):
        with open(filename, 'r') as f:
            self.update([(physical.display_name, physical)
                         for physical in Grammar.object_repository.parseFile(f)])

    def save(self, filename):
        """
        Write all the class descriptions to a file, which should have
        the .tor extension.
        """
        with open(filename, 'w') as f:
            f.write(str(self))

    def __str__(self):
        return '\n \n'.join([str(physical) for physical in self.values()]) + '\n'

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               super(OrderedDict, self).__repr__())

    def extract(self, name, source, careful=False):
        obj = source[name]
        if name in self and careful:
            pass
        else:
            self[obj.display_name] = obj
            obj.traverse(lambda name, thing: isinstance(thing, Ref),
                         lambda name, thing: self.extract(thing.name, source, careful))
