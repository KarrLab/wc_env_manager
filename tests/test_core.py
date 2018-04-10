""" Test wc_env.core

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import unittest
import tempfile
import shutil
import os
import stat
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
        self.relative_temp_path = os.path.join('tests', 'tmp')
        self.moving_text = 'I Have a Dream'
        with open(self.absolute_path_file, 'w') as f:
            f.write(self.moving_text)
        self.sample_repo = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_repo')
        self.docker_client = docker.from_env()
        self.tmp_containers = []

    def tearDown(self):
        # remove containers created by these tests
        for container in self.tmp_containers:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
        # remove relative temp files
        shutil.rmtree(self.relative_temp_path, ignore_errors=True)

    '''
    @classmethod
    def tearDownClass(cls):
        DockerUtils.list_all()
    '''

    def make_test_repo(self, relative_path):
        # copy contents of self.sample_repo to a test repo at `relative_path`
        test_repo = os.path.abspath(os.path.expanduser(relative_path))
        shutil.copytree(self.sample_repo, test_repo)

    def test_constructor(self):
        test_wc_repos = [
            # test path in home dir
            os.path.join(self.test_dir_in_home, 'repo_a'),
            # test full pathname
            os.path.join(self.test_dir, 'repo_b'),
            # test relative pathname
            os.path.join(self.relative_temp_path, 'repo_c')
        ]
        for test_wc_repo in test_wc_repos:
            self.make_test_repo(test_wc_repo)
        manage_container = wc_env.ManageContainer(test_wc_repos, '0.1')
        expected_paths = [
            os.path.join(self.temp_dir_in_home.name, 'repo_a'),
            os.path.join(self.test_dir, 'repo_b'),
            os.path.join(os.getcwd(), self.relative_temp_path, 'repo_c')
        ]
        for computed_path,expected_path in zip(manage_container.local_wc_repos, expected_paths):
            self.assertEqual(computed_path, expected_path)
        with self.assertRaises(wc_env.EnvError):
            wc_env.ManageContainer([self.absolute_path_file], '0.1')
        repo_a = os.path.join(self.temp_dir_in_home.name, 'repo_a')
        os.chmod(repo_a, 0)
        with self.assertRaises(wc_env.EnvError):
            wc_env.ManageContainer([repo_a], '0.1')
        os.chmod(repo_a, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

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
        # test volume sharing
        '''
        manage_container = wc_env.ManageContainer([], '0.0.1',
            ssh_key=test_ssh_key,
            git_config_file=test_git_config_file)
        manage_container.create()
        self.tmp_containers.append(manage_container.container)

        self.assertEqual(manage_container.container.status, 'created')
        '''

        # test file copying
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
