""" wc_env_manager command line interface

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import cement
import wc_env_manager
import wc_env_manager.core


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "wc_env_manager"

    @cement.ex(help='command_1 description')
    def command_1(self):
        """ command_1 description """
        pass

    @cement.ex(help='command_2 description')
    def command_2(self):
        """ command_2 description """
        pass

    @cement.ex(help='Get version')
    def get_version(self):
        """ Get version """
        print(wc_env_manager.__version__)


class Command3WithArgumentsController(cement.Controller):
    """ Command3 description """

    class Meta:
        label = 'command-3'
        description = 'Command3 description'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['arg_1'], dict(
                type=str, help='Description of arg_1')),
            (['arg_2'], dict(
                type=str, help='Description of arg_2')),
            (['--opt-arg-3'], dict(
                type=str, default='default value of opt-arg-1', help='Description of opt-arg-3')),
            (['--opt-arg-4'], dict(
                type=float, default=float('nan'), help='Description of opt-arg-4')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        args.arg_1
        args.arg_2
        args.opt_arg_3
        args.opt_arg_4


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'wc_env_manager'
        base_controller = 'base'
        handlers = [
            BaseController,
            Command3WithArgumentsController,
        ]


def main():
    with App() as app:
        app.run()
