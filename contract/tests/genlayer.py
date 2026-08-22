"""Minimal stand-in for the GenLayer SDK so the contract logic can be
unit-tested off-chain. Only the surface used by political_warfare.py."""


class Address:
    def __init__(self, value):
        if isinstance(value, Address):
            value = value.as_hex
        self.as_hex = str(value)

    def __eq__(self, other):
        return isinstance(other, Address) and other.as_hex == self.as_hex

    def __hash__(self):
        return hash(self.as_hex)

    def __repr__(self):
        return f"Address({self.as_hex})"


class TreeMap(dict):
    """dict-like; class-getitem so TreeMap[K, V] annotations work."""

    def __class_getitem__(cls, item):
        return cls


class DynArray(list):
    def __class_getitem__(cls, item):
        return cls


bigint = int


def _identity(fn):
    return fn


class _Public:
    view = staticmethod(_identity)
    write = staticmethod(_identity)


class _Message:
    sender_address = Address("0x" + "0" * 40)


class _Nondet:
    # Tests override `responses` (a list used as a FIFO queue).
    responses = []

    def exec_prompt(self, task):
        if not self.responses:
            return ""
        return self.responses.pop(0)


class _EqPrinciple:
    @staticmethod
    def prompt_comparative(fn, principle):
        return fn()


class _GL:
    Contract = object
    public = _Public()
    message = _Message()
    nondet = _Nondet()
    eq_principle = _EqPrinciple()


gl = _GL()
