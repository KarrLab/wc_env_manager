""" Tests of the configuration

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-08-20
:Copyright: 2018, Karr Lab
:License: MIT
"""

import os
import pathlib
import pkg_resources
import unittest
import wc_env_manager.config.core


class Test(unittest.TestCase):

    def test_get_config(self):
        config = wc_env_manager.config.core.get_config()
        self.assertIn('base_image', config['wc_env_manager'])
        self.assertIsInstance(config['wc_env_manager']['base_image']['repo'], str)

    def test_get_config_extra(self):
        extra = {
            'wc_env_manager': {
                'base_image': {
                    'build_args': {
                        'timezone': 'America/Los_Angeles',
                    },
                },
            },
        }
        config = wc_env_manager.config.core.get_config(extra=extra)
        self.assertEqual(config['wc_env_manager']['base_image']['build_args']['timezone'], 'America/Los_Angeles')

    def test_get_config_context(self):
        extra = {
            'wc_env_manager': {
                'base_image': {
                    'dockerfile_path': '${HOME}/Dockerfile',
                },
            },
        }
        config = wc_env_manager.config.core.get_config(extra=extra)
        self.assertEqual(config['wc_env_manager']['base_image']['dockerfile_path'],
                         '{}/Dockerfile'.format(pathlib.Path.home()))
