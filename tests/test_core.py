""" Test wc_env.core

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import unittest
import tempfile
import os

import wc_env.core


# todo: port to Windows
class TestManageContainer(unittest.TestCase):

    def setUp(self):
        self.temp_dir  = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        self.temp_dir_in_home  = tempfile.TemporaryDirectory(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home.name))
        self.fixture_repo = os.path.join('tests', 'fixtures', 'fixture_repo')

    def test_constructor(self):
        wc_repos = [
            # test path in home dir
            os.path.join(self.test_dir_in_home, 'repo_dir'),
            # test full pathname
            self.test_dir,
            # test relative pathname
            self.fixture_repo
        ]
        manage_container = wc_env.ManageContainer(wc_repos, '0.1')
        expected_paths = [
            os.path.join(self.temp_dir_in_home.name, 'repo_dir'),
            self.test_dir,
            os.path.join(os.getcwd(), self.fixture_repo)
        ]
        for computed_path,expected_path in zip(manage_container.local_wc_repos, expected_paths):
            self.assertEqual(computed_path, expected_path)

    def do_check_credentials(self, test_configs_repo_pwd_file, expected):
        # check ManageContainer.check_credentials()
        manage_container = wc_env.ManageContainer([], '0.1',
            configs_repo_pwd_file=test_configs_repo_pwd_file)
        manage_container.check_credentials()
        self.assertEqual(manage_container.configs_repo_pwd_file, expected)

    def test_check_credentials(self):
        # readable file
        test_configs_repo_pwd_file = os.path.join(self.test_dir, 'configs_repo_pwd_file')
        with open(test_configs_repo_pwd_file, 'w') as f:
            f.write('test')
            f.close()
        self.do_check_credentials(test_configs_repo_pwd_file, test_configs_repo_pwd_file)

        # file that cannot be read
        os.chmod(test_configs_repo_pwd_file, 0)
        self.do_check_credentials(test_configs_repo_pwd_file, None)

        # non-existant file
        test_no_such_file = os.path.join(self.test_dir, 'no_such_file')
        self.do_check_credentials(test_no_such_file, None)

        # no credentials
        manage_container = wc_env.ManageContainer([], '0.1',
            configs_repo_pwd_file=test_no_such_file, ssh_key=test_no_such_file)
        with self.assertRaises(wc_env.EnvError) as context:
            manage_container.check_credentials()

    def test_build(self):
        manage_container = wc_env.ManageContainer([], '0.1')
        manage_container.build()
