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


class DockerUtils(object):

    FIELDS = 'name status image short_id'.split()

    @staticmethod
    def header():
        return DockerUtils.FIELDS

    @staticmethod
    def format(container):
        rv = []
        for f in DockerUtils.FIELDS:
            rv.append(str(getattr(container, f)))
        return rv

    @staticmethod
    def list_all():
        print('\t\t'.join(DockerUtils.header()))
        for c in docker.from_env().containers.list(all=True):
            print('\t\t'.join(DockerUtils.format(c)))

    @staticmethod
    def get_file(container, file):
        """ get contents of a file in a container

        Args:
            container (:obj:`type of arg_1`): a Docker container
            file (:obj:`str`): path to a file in `container`

        Returns:
            :obj:`str`: the contents of `file` in `container`

        Raises:
            :obj:`docker.errors.APIError`: if `container.exec_run` raises an error
        """
        exit_code, output = container.exec_run(['cat', file])
        if exit_code==0:
            return output.decode('utf-8')
        else:
            raise wc_env.EnvError("cat {} fails".format(file))


# todo: port to and test on Windows
class TestManageContainer(unittest.TestCase):

    def setUp(self):
        self.temp_dir  = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        self.temp_dir_in_home  = \
            tempfile.TemporaryDirectory(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home.name))
        self.relative_path_file = os.path.join('tests', 'fixtures', 'relative_path_file.txt')
        self.absolute_path_file = os.path.join(os.getcwd(), self.relative_path_file)
        self.moving_text = 'I Have a Dream'
        with open(self.absolute_path_file, 'w') as f:
            f.write(self.moving_text)
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
        DockerUtils.list_all()

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
        with self.assertRaises(wc_env.EnvError):
            manage_container = wc_env.ManageContainer([], '0.1',
                configs_repo_pwd_file=test_no_such_file, ssh_key=test_no_such_file)

    def test_create(self):
        test_ssh_key = os.path.join(self.test_dir_in_home, 'test_ssh_key')
        test_ssh_key_content = 'Four score ...\nago our ...'
        with open(os.path.expanduser(test_ssh_key), 'w') as f:
            f.write(test_ssh_key_content)
        with open(os.path.expanduser(test_ssh_key+'.pub'), 'w') as f:
            f.write(test_ssh_key_content+'.pub')

        test_git_config_file = os.path.join('tests', 'fixtures', '.gitconfig')

        manage_container = wc_env.ManageContainer([], '0.0.1',
            ssh_key=test_ssh_key,
            git_config_file=test_git_config_file)
        manage_container.create()
        self.tmp_containers.append(manage_container.container)

        self.assertEqual(manage_container.container.status, 'created')
        self.assertEqual(DockerUtils.get_file(manage_container.container, '/root/.ssh/id_rsa'),
            test_ssh_key_content)
        self.assertEqual(DockerUtils.get_file(manage_container.container, '/root/.ssh/id_rsa.pub'),
            test_ssh_key_content+'.pub')
        self.assertEqual(DockerUtils.get_file(manage_container.container, '/root/.gitconfig'),
            ''.join(open(test_git_config_file, 'r').readlines()))

    def create_test_container(self):
        manage_container = wc_env.ManageContainer([], '0.0.1')
        manage_container.create()
        self.tmp_containers.append(manage_container.container)
        return manage_container

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
        path_in_container = os.path.join('/tmp/', os.path.basename(self.absolute_path_file))
        manage_container.cp(self.absolute_path_file, path_in_container)
        self.assertEqual(DockerUtils.get_file(manage_container.container, path_in_container),
            self.moving_text)
