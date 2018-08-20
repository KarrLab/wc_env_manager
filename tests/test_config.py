""" Tests of the configuration

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-08-20
:Copyright: 2018, Karr Lab
:License: MIT
"""

import wc_env_manager.config.core
import os
import pkg_resources
import unittest


class Test(unittest.TestCase):

    def test_get_config(self):
        config = wc_env_manager.config.core.get_config()
        self.assertIn('ssh_key_path', config['wc_env_manager'])
        self.assertIsInstance(config['wc_env_manager']['ssh_key_path'], str)
