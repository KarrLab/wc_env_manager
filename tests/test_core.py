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
from capturer import CaptureOutput
from inspect import currentframe, getframeinfo

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
            container (:obj:`docker.models.containers.Container`): a Docker container
            file (:obj:`str`): path to a file in `container`

        Returns:
            :obj:`str`: the contents of `file` in `container`

        Raises:
            :obj:`docker.errors.APIError`: if `container.exec_run` raises an error
        """
        exit_code, output = container.exec_run(['cat', file])
        frameinfo = getframeinfo(currentframe())
        if exit_code==0:
            return output.decode('utf-8')
        else:
            raise wc_env.EnvError("{}:{}: cat {} fails with exit_code {} "
                "this is a Docker system race condition; rerun test".format(
                frameinfo.filename, frameinfo.lineno, file, exit_code))

    @staticmethod
    def cmp_files(testcase, container, container_filename, host_file_content=None, host_filename=None):
        """ Make testcase comparison of content of file on host with file in container

        At least one of `host_file_content` or `host_filename` must be provided.
        Will not scale to huge files.

        Args:
            testcase (:obj:`testcase.TestCase`): testcase being run
            container (:obj:`docker.models.containers.Container`): Docker container storing `container_filename`
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


class TestManageImage(unittest.TestCase):

    def test_build(self):
        manage_image = wc_env.ManageImage('foo', '0.0.1', verbose=True)
        manage_image.build(path=os.path.join(os.path.dirname(__file__),
            '../wc_env/tmp_dockerfiles/'))


# todo: port to and test on Windows
# todo: perhaps try to speedup testing; could reuse containers
class TestManageContainer(unittest.TestCase):

    def setUp(self):
        # use mkdtemp() instead of TemporaryDirectory() so files can be saved after
        # testing to debug containers by setting `remove_temp_files`
        # put in temp dir in /private/tmp which can contain a Docker volume by default
        self.test_dir = tempfile.mkdtemp(dir='/private/tmp')
        self.temp_dir_in_home  = \
            tempfile.mkdtemp(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home))
        self.relative_path_file = os.path.join('tests', 'fixtures', 'relative_path_file.txt')
        self.absolute_path_file = os.path.join(os.getcwd(), self.relative_path_file)
        self.relative_temp_path = tempfile.mkdtemp(dir=os.path.join('tests', 'tmp'))
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
        # ManageContainers with created containers that need to be removed
        self.tmp_container_managers = []

    def tearDown(self):
        # remove containers created by these tests
        for container_manager in self.tmp_container_managers:
            container = container_manager.container
            try:
                container.stop()
                container.remove(v=True)
            except docker.errors.APIError as e:
                print("docker.errors.APIError: {}".format(e), file=sys.stderr)
        # remove temp files
        remove_temp_files = True
        if remove_temp_files:
            shutil.rmtree(self.relative_temp_path)
            shutil.rmtree(self.test_dir)
            shutil.rmtree(self.temp_dir_in_home)

    @classmethod
    def tearDownClass(cls):
        DockerUtils.list_all()
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
        with self.assertRaises(wc_env.EnvError):
            wc_env.ManageContainer([repo_a, repo_a], '0.1')
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
        # test ManageContainer.create()
        manage_container = self.make_container(wc_repos=self.test_wc_repos)
        container = manage_container.create()
        # spot-check files in the 3 repos in the container
        for local_wc_repo in manage_container.local_wc_repos:
            container_wc_repo_dir = os.path.join(manage_container.container_repo_dir,
                os.path.basename(local_wc_repo))
            container_core_py_file = os.path.join(container_wc_repo_dir, 'tests/requirements.txt')
            DockerUtils.cmp_files(self, container, container_core_py_file,
                host_filename=os.path.join(self.sample_repo, 'tests/requirements.txt'))
            container_REPO_NAME_file = os.path.join(container_wc_repo_dir, 'REPO_NAME')
            DockerUtils.cmp_files(self, container, container_REPO_NAME_file,
                host_file_content=os.path.basename(local_wc_repo))
        with self.assertRaises(subprocess.CalledProcessError):
            # it is an error if DEST_PATH does not exist and ends with /
            manage_container.cp(self.absolute_path_file, '/root/tmp/no such dir/')
        path_in_container = os.path.join('/tmp/', os.path.basename(self.absolute_path_file))
        manage_container.cp(self.absolute_path_file, path_in_container)
        DockerUtils.cmp_files(self, manage_container.container, path_in_container, host_file_content=self.moving_text)

        # test pp_to_karr_lab_repos
        pythonpath = manage_container.pp_to_karr_lab_repos()
        for wc_repo_path in self.test_wc_repos:
            wc_repo = os.path.basename(wc_repo_path)
            self.assertIn(wc_repo, pythonpath)
        for cloned_karr_lab_repo in wc_env.ManageContainer.all_wc_repos():
            self.assertIn(cloned_karr_lab_repo, pythonpath)
        for wc_repo_path in self.test_wc_repos:
            wc_repo = os.path.basename(wc_repo_path)
            for cloned_karr_lab_repo in wc_env.ManageContainer.all_wc_repos():
                self.assertTrue(pythonpath.index(wc_repo)<=pythonpath.index(cloned_karr_lab_repo))

    def make_container(self, wc_repos=None, save_container=False, verbose=False):
        # make a test container
        # provide wc_repos to create volumes for them
        # set save_container to save the container for later investigation
        # set verbose to produce verbose output
        if wc_repos is None:
            wc_repos = []
        manage_container = wc_env.ManageContainer(wc_repos, '0.0.1', verbose=verbose)
        container = manage_container.create()
        if save_container:
            print("docker attach {}".format(container.name))
        else:
            self.tmp_container_managers.append(manage_container)
        return manage_container

    def test_load_karr_lab_tools(self):
        manage_container = self.make_container()
        with CaptureOutput() as capturer:
            manage_container.load_karr_lab_tools()
            try:
                # test karr_lab_build_utils
                self.assertIn('karr_lab_build_utils', manage_container.exec_run("karr_lab_build_utils -h"))
            except Exception as e:
                self.fail('Exception thrown by exec_run("karr_lab_build_utils -h") {}'.format(e))
            expected_output = ['pip install pkg_utils --',
                'pip install karr_lab_build_utils --',]
            for line in expected_output:
                self.assertIn(line, capturer.get_text())

    def test_clone_karr_lab_repos(self):
        manage_container = self.make_container()
        manage_container.clone_karr_lab_repos()
        kl_repos = manage_container.exec_run('ls {}'.format(manage_container.container_local_repos))
        kl_repos = set(kl_repos.split('\n'))
        self.assertTrue(set(wc_env.ManageContainer.all_wc_repos()).issubset(kl_repos))

    def test_run(self):
        manage_container = self.make_container(wc_repos=self.test_wc_repos, save_container=True, verbose=True)
        manage_container.run()

    def test_cp_exceptions(self):
        manage_container = wc_env.ManageContainer([], '0.0.1')
        with self.assertRaises(wc_env.EnvError):
            manage_container.cp(self.absolute_path_file, '')
        with self.assertRaises(wc_env.EnvError):
            manage_container.cp('no such file', '')

    def test_exec_run(self):
        with CaptureOutput(relay=False) as capturer:
            manage_container = self.make_container(verbose=True)
            with self.assertRaises(wc_env.EnvError):
                manage_container.exec_run('no_such_command x')
            ls = set(manage_container.exec_run('ls').split('\n'))
            self.assertTrue(set('usr bin home tmp root etc lib'.split()).issubset(ls))
            verbose_output = ['Running: containers.run',
                'Running: container.exec_run(ssh-keyscan',
                'Running: container.exec_run(no_such_command x)',
                'Running: container.exec_run(ls)']
            for verbose_line in verbose_output:
                self.assertIn(verbose_line, capturer.get_text())
