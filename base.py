import pyparsing as p
from collections import OrderedDict

class Quantity(object):
    """
    This class represents a physical quantity that may or may not
    carry units.
    """

    def __init__(self, number, units=None):
        if isinstance(number, str):
            try:
                self.number = int(number)
            except ValueError:
                self.number = float(number)
        # This should possibly be expanded for numpy number types.
        elif isinstance(number, int) or isinstance(number, float):
            self.number = number
        else:
            raise ValueError("Invalid number: {!r}".format(number))
        # Add logic for allowed units.
        self.units = units

    def __str__(self):
        # This uses a lowercase e for exponential notation; GRASP
        # writes an uppercase E, but can read either. Using repr
        # instead of str for numbers seems to ensure that no rounding
        # occurs.
        if self.units is None:
            return '{!r}'.format(self.number)
        else:
            return '{!r} {}'.format(self.number, self.units)

    def __repr__(self):
        if self.units is None:
            return '{}({!r})'.format(self.__class__.__name__, self.number)
        else:
            return '{}({!r}, {!r})'.format(self.__class__.__name__, self.number, self.units)

class Ref(object):
    """
    This class is a wrapper for Physical objects. It stops the
    recursion of __str__ to avoid infinite loops.

    To do: if pointers to actual objects become useful, implement
    __repr__() to stop infinite loops.
    """

    def __init__(self, ref):
        self.set(ref)

    def set(self, ref):
        """
        This allows self.ref to be changed in a lambda statement.
        """
        if isinstance(ref, str):
            self.name = ref
        elif isinstance(ref, Physical):
            self.name = ref.display_name
        else:
            raise ValueError("Invalid Ref: {!r}".format(ref))
        self.ref = ref

    def __str__(self):
        return 'ref({})'.format(self.name)

    # This will not work for referenced objects, only strings.
    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.ref)


class Sequence(list):

    def __str__(self):
        return 'sequence({})'.format(', '.join(str(j) for j in (s for s in self)))

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super(Sequence, self).__repr__())

class Struct(OrderedDict):
    
    def __str__(self):
        return 'struct({})'.format(', '.join('{}: {}'.format(k, v) for k, v in self.items()))

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, super(OrderedDict, self).__repr__()) 

class Physical(OrderedDict):
    """
    This class is a lightweight container for GRASP physical objects.

    It inherits from OrderedDict so that it remembers the ordering of its properties.
    """

    def __init__(self, display_name, class_name, other={}):
        super(Physical, self).__init__(other)
        self.display_name = str(display_name)
        self.class_name = str(class_name)

    def __str__(self):
        lines = ['{}  {}  '.format(self.display_name, self.class_name)]
        lines.append('(')
        for k, v in self.items():
            lines.append('  {:16s} : {},'.format(k, v))
        lines[-1] = lines[-1].rstrip(',')
        lines.append(')')
        return '\n'.join(lines)
    
    def __repr__(self):
        return '{}({!r}, {!r}, {{{}}})'.format(self.__class__.__name__, 
                                               self.display_name,
                                               self.class_name,
                                               ', '.join(['{!r}: {!r}'.format(k, v) for k, v in self.items()]))

class Grammar (object):
    ident = p.Word(p.alphas + '_', p.alphanums + '_.')
    value = p.Forward()
    s_int = p.Word(p.nums    )
    s_flt = p.Word(p.nums+'.')

    number = p.Combine(
        p.Optional(p.Literal('+') ^ p.Literal('-')) +
        p.Word(p.nums) +
        p.Optional('.' + p.Word(p.nums)) +
        p.Optional(p.CaselessLiteral('E') +
        p.Word(p.nums + '+-', p.nums))
    )
    quantity = (
        number + 
        p.Optional(p.Word(p.alphas, p.alphanums + '-^/' + ' '), default=None)
    )
    quantity.setParseAction(lambda tokens: Quantity(*tokens))
    
    s_ref = (
        "ref" + 
        p.Suppress("(") + 
        value + 
        p.Suppress(")")
    )
    s_ref.setParseAction (lambda tokens: [Ref(tokens[1])])

    s_seq_e = value + p.Optional(ident)
    s_seq = (
        "sequence" + 
        p.Suppress("(") + 
        p.delimitedList(s_seq_e) + 
        p.Suppress(")")
    )
    s_seq.setParseAction (lambda tokens: [Sequence(tokens[1:])])

    s_sct_e = (
        p.Group(ident + p.Suppress(":") + p.QuotedString('"') + ident) |
        p.Group(ident + p.Suppress(":") + value + ident) |
        p.Group(ident + p.Suppress(":") + value)
    )
    s_sct = (
        "struct" + 
        p.Suppress("(") + 
        p.delimitedList(s_sct_e) + 
        p.Suppress(")")
    )
    s_sct.setParseAction (
        lambda tokens: [Struct((dat[0], dat[1]) for dat in tokens[1:])]
    )
    s_quo = p.QuotedString('"')

    comment = p.QuotedString('"', unquoteResults=False)
    other = p.Word(p.alphanums + '\/._-')
    value << (quantity | s_ref | s_seq | s_sct | other | comment)

    member   = p.Group(ident + p.Suppress(":") + value)
    physical = (
        ident + ident +
        p.Suppress('(') +
        p.Optional(p.delimitedList(member)) +
        p.Suppress(')')
    )
    physical.ignore(p.cppStyleComment) # '// comment'
    physical.ignore(p.pythonStyleComment) # '# comment'
    physical.setParseAction(
        lambda tokens: [Physical (tokens[0], tokens[1], tokens[2:])]
    )

    object_repository = p.ZeroOrMore(physical) + p.StringEnd()
    object_repository.ignore(p.cppStyleComment)
    object_repository.ignore(p.pythonStyleComment)
