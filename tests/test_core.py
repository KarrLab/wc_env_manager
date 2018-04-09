""" Test wc_env.core

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import unittest
import tempfile
import os
import subprocess
import docker

import wc_env.core


class ContainerUtils(object):

    FIELDS = 'name status image short_id'.split()

    @staticmethod
    def header():
        return ContainerUtils.FIELDS

    @staticmethod
    def format(container):
        rv = []
        for f in ContainerUtils.FIELDS:
            rv.append(str(getattr(container, f)))
        return rv

    @staticmethod
    def list_all():
        print('\t\t'.join(ContainerUtils.header()))
        for c in docker.from_env().containers.list(all=True):
            print('\t\t'.join(ContainerUtils.format(c)))

# todo: port to and test on Windows
class TestManageContainer(unittest.TestCase):

    def setUp(self):
        self.temp_dir  = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        self.temp_dir_in_home  = tempfile.TemporaryDirectory(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home.name))
        self.relative_path_file = os.path.join('tests', 'fixtures', 'relative_path_file.txt')
        self.absolute_path_file = os.path.join(os.getcwd(), self.relative_path_file)
        self.MLK_speech = 'I Have a Dream'
        with open(self.absolute_path_file, 'w') as f:
            f.write(self.MLK_speech)
        self.docker_client = docker.from_env()
        self.tmp_containers = []

    def tearDown(self):
        # remove containers created by these tests
        for container in self.tmp_containers:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass

    @classmethod
    def tearDownClass(cls):
        ContainerUtils.list_all()

    def test_constructor(self):
        wc_repos = [
            # test path in home dir
            os.path.join(self.test_dir_in_home, 'repo_dir'),
            # test full pathname
            self.test_dir,
            # test relative pathname
            self.relative_path_file
        ]
        manage_container = wc_env.ManageContainer(wc_repos, '0.1')
        expected_paths = [
            os.path.join(self.temp_dir_in_home.name, 'repo_dir'),
            self.test_dir,
            self.absolute_path_file
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

    def create_test_container(self):
        manage_container = wc_env.ManageContainer([], '0.0.1')
        manage_container.create()
        self.tmp_containers.append(manage_container.container)
        return manage_container

    def test_create(self):
        manage_container = self.create_test_container()
        self.assertEqual(manage_container.container.status, 'created')

    def test_cp(self):
        manage_container = wc_env.ManageContainer([], '0.0.1')
        with self.assertRaises(wc_env.EnvError):
            manage_container.cp(self.absolute_path_file, '')
        with self.assertRaises(wc_env.EnvError):
            manage_container.cp('no such file', '')
        manage_container = self.create_test_container()
        with self.assertRaises(subprocess.CalledProcessError):
            # it is an error if DEST_PATH does not exist and ends with /
            manage_container.cp(self.absolute_path_file, '/root/tmp/no such dir/')
        manage_container.cp(self.absolute_path_file,
            os.path.join('/tmp/', os.path.basename(self.absolute_path_file)))
        # a hand check shows that cp works
        # todo: check that self.absolute_path_file is in '/root/tmp'; can try techniques in https://github.com/docker/docker-py/blob/master/tests/integration/api_container_test.py
