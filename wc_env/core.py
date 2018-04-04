""" wc_env

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""


class ExampleClass(object):
    """ Descipton of ExampleClass

    Attributes:
        attr_1 (:obj:`type of attr_1`): description of attr_1
        attr_2 (:obj:`type of attr_2`): description of attr_2
        ...
    """

    def __init__(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """
        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            arg_2 (:obj:`type of arg_2`): description of arg_2
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            kwarg_2 (:obj:`type of kwarg_2`, optional): description of kwarg_2
            ...
        """
        self.attr_1 = arg_1
        self.attr_2 = arg_2

    def method_1(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Description of method_1

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            arg_2 (:obj:`type of arg_2`): description of arg_2
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            kwarg_2 (:obj:`type of kwarg_2`, optional): description of kwarg_2
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        pass