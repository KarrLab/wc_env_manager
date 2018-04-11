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
            container (:obj:`docker.models.containers.container`): a Docker container
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

    @staticmethod
    def cmp_files(testcase, container, container_filename, host_file_content=None, host_filename=None):
        """ Make testcase comparison of content of file on host with file in container

        At least one of `host_file_content` or `host_filename` must be provided.
        Will not scale to huge files.

        Args:
            testcase (:obj:`testcase.TestCase`): testcase being run
            container (:obj:`docker.models.containers.container`): Docker container storing `container_filename`
            container_filename (:obj:`str`): pathname of file in `container`
            host_file_content (:obj:`str`, optional): content of host file being compared
            host_filename (:obj:`str`, optional): pathname of host file being compared

        Raises:
            :obj:`ValueError`: if both `host_file_content` and `host_filename` are `None`
        """
        if host_file_content is None and host_filename is None:
            raise ValueError('either host_file_content or host_filename must be provided')
        if host_file_content is None:
            host_filename = os.path.abspath(os.path.expanduser(host_filename))
            with open(host_filename, 'r') as f:
                host_file_content = ''.join(f.readlines())
        testcase.assertEqual(DockerUtils.get_file(container, container_filename), host_file_content)


# todo: port to and test on Windows
class TestManageContainer(unittest.TestCase):

    def setUp(self):
        # put in temp dir in /private/tmp which can contain a Docker volume by default
        # todo: make this OS portable
        # use mkdtemp() instead of TemporaryDirectory() so files can survive testing for debugging container
        self.test_dir = tempfile.mkdtemp(dir='/private/tmp')
        self.temp_dir_in_home  = \
            tempfile.mkdtemp(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home))
        self.relative_path_file = os.path.join('tests', 'fixtures', 'relative_path_file.txt')
        self.absolute_path_file = os.path.join(os.getcwd(), self.relative_path_file)
        self.relative_temp_path = os.path.join('tests', 'tmp')
        self.moving_text = 'I Have a Dream'
        with open(self.absolute_path_file, 'w') as f:
            f.write(self.moving_text)

        self.sample_repo = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_repo')
        self.test_wc_repos = [
            # test path in home dir
            os.path.join(self.test_dir_in_home, 'repo_a'),
            # test full pathname
            os.path.join(self.test_dir, 'repo_b'),
            # test relative pathname
            os.path.join(self.relative_temp_path, 'repo_c')
        ]
        for test_wc_repo in self.test_wc_repos:
            self.make_test_repo(test_wc_repo)

        self.docker_client = docker.from_env()
        self.tmp_containers = []

    def tearDown(self):
        # remove containers created by these tests
        for container in self.tmp_containers:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
        # remove temp files
        remove_temp_files = True
        if remove_temp_files:
            shutil.rmtree(self.relative_temp_path, ignore_errors=True)
            shutil.rmtree(self.test_dir)
            shutil.rmtree(self.temp_dir_in_home)

    @classmethod
    def tearDownClass(cls):
        # DockerUtils.list_all()
        pass

    def make_test_repo(self, relative_path):
        # copy contents of self.sample_repo to a test repo at `relative_path`
        test_repo = os.path.abspath(os.path.expanduser(relative_path))
        shutil.copytree(self.sample_repo, test_repo)
        # create a unique repo name file
        with open(os.path.join(test_repo, 'REPO_NAME'), 'w') as f:
            f.write(os.path.basename(test_repo))

    def test_constructor(self):
        manage_container = wc_env.ManageContainer(self.test_wc_repos, '0.1')
        expected_repo_paths = [
            os.path.join(self.temp_dir_in_home, 'repo_a'),
            os.path.join(self.test_dir, 'repo_b'),
            os.path.join(os.getcwd(), self.relative_temp_path, 'repo_c')
        ]
        for computed_path,expected_path in zip(manage_container.local_wc_repos, expected_repo_paths):
            self.assertEqual(computed_path, expected_path)
        with self.assertRaises(wc_env.EnvError):
            wc_env.ManageContainer([self.absolute_path_file], '0.1')
        repo_a = os.path.join(self.temp_dir_in_home, 'repo_a')
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

    def test_create_volume_sharing(self):
        # test volume sharing
        manage_container = wc_env.ManageContainer(self.test_wc_repos, '0.0.1')
        manage_container.create()
        container = manage_container.container
        self.tmp_containers.append(container)
        # print('docker attach', container.name)
        # spot-check files in the 3 repos in the container
        for local_wc_repo in manage_container.local_wc_repos:
            container_wc_repo_dir = os.path.join(manage_container.container_repo_dir,
                os.path.basename(local_wc_repo))
            container_core_py_file = os.path.join(container_wc_repo_dir, 'wc_env/core.py')
            DockerUtils.cmp_files(self, container, container_core_py_file,
                host_filename=os.path.join(self.sample_repo, 'wc_env/core.py'))
            container_REPO_NAME_file = os.path.join(container_wc_repo_dir, 'REPO_NAME')
            DockerUtils.cmp_files(self, container, container_REPO_NAME_file,
                host_file_content=os.path.basename(local_wc_repo))

    def test_create_file_copying(self):
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

        DockerUtils.cmp_files(self, manage_container.container, '/root/.ssh/id_rsa', host_filename=test_ssh_key)
        DockerUtils.cmp_files(self, manage_container.container, '/root/.ssh/id_rsa.pub',
            host_file_content=test_ssh_key_content+'.pub')
        DockerUtils.cmp_files(self, manage_container.container, '/root/.gitconfig',
            host_filename=test_git_config_file)

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
        DockerUtils.cmp_files(self, manage_container.container, path_in_container, host_file_content=self.moving_text)
