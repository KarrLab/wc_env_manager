""" Tests of wc_env_manager command line interface

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-08-29
:Copyright: 2018, Karr Lab
:License: MIT
"""

from wc_env_manager import __main__
import capturer
import mock
import unittest
import whichcraft


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class MainTestCase(unittest.TestCase):

    def test_cli(self):
        with mock.patch('sys.argv', ['wc_env_manager', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: wc_env_manager')

    def test_help(self):
        with __main__.App(argv=['--help']) as app:
            with self.assertRaises(SystemExit):
                app.run()

    def test_base_image(self):
        with __main__.App(argv=['base-image', '--help']) as app:
            with self.assertRaises(SystemExit):
                app.run()

        with __main__.App(argv=['base-image', 'pull']) as app:
            app.run()

        with __main__.App(argv=['base-image', 'build']) as app:
            app.run()

        with __main__.App(argv=['base-image', 'push']) as app:
            app.run()

        with __main__.App(argv=['base-image', 'version']) as app:
            app.run()

        with __main__.App(argv=['base-image', 'remove']) as app:
            app.run()

        with __main__.App(argv=['base-image', 'pull']) as app:
            app.run()

    def test_image(self):
        with __main__.App(argv=['image', '--help']) as app:
            with self.assertRaises(SystemExit):
                app.run()

        with __main__.App(argv=['image', 'pull']) as app:
            app.run()

        with __main__.App(argv=['image', 'build']) as app:
            app.run()

        with __main__.App(argv=['image', 'push']) as app:
            app.run()

        with __main__.App(argv=['image', 'version']) as app:
            app.run()

        with __main__.App(argv=['image', 'remove']) as app:
            app.run()

        with __main__.App(argv=['image', 'pull']) as app:
            app.run()

    def test_network(self):
        with __main__.App(argv=['network', '--help']) as app:
            with self.assertRaises(SystemExit):
                app.run()

        with __main__.App(argv=['network', 'build']) as app:
            app.run()

        with __main__.App(argv=['network', 'remove']) as app:
            app.run()

    def test_container(self):
        with __main__.App(argv=['container', '--help']) as app:
            with self.assertRaises(SystemExit):
                app.run()

        with __main__.App(argv=['image', 'pull']) as app:
            app.run()

        with __main__.App(argv=['container', 'build']) as app:
            app.run()

        with __main__.App(argv=['container', 'remove']) as app:
            app.run()

    def test_all(self):
        with __main__.App(argv=['pull']) as app:
            app.run()

        with __main__.App(argv=['build']) as app:
            app.run()

        with __main__.App(argv=['push']) as app:
            app.run()

        with __main__.App(argv=['remove']) as app:
            app.run()

        with __main__.App(argv=['pull']) as app:
            app.run()
