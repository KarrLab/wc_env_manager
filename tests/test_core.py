""" Tests for wc_env_manager.core

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-08-20
:Copyright: 2018, Karr Lab
:License: MIT
"""

from capturer import CaptureOutput
from inspect import currentframe, getframeinfo
import capturer
import datetime
import docker
import mock
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import wc_env_manager.core
import whichcraft


class WcEnvManagerBuildRemoveImageTestCase(unittest.TestCase):
    def setUp(self):
        self.remove_images()

        docker_image_context_path = tempfile.mkdtemp()
        dockerfile_path = os.path.join(docker_image_context_path, 'Dockerfile')
        with open(dockerfile_path, 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('CMD bash\n')

        mgr = self.mgr = wc_env_manager.core.WcEnvManager(
            docker_image_repo='karrlab/test',
            docker_image_tags=['0.0.1', 'latest'],
            dockerfile_path=dockerfile_path,
            docker_image_context_path=docker_image_context_path)

    def tearDown(self):
        self.remove_images()
        shutil.rmtree(self.mgr.docker_image_context_path)

    def remove_images(self):
        client = docker.from_env()
        try:
            client.images.remove('karrlab/test:0.0.1')
        except docker.errors.ImageNotFound:
            pass
        try:
            client.images.remove('karrlab/test:latest')
        except docker.errors.ImageNotFound:
            pass

    def test_build_docker_image(self):
        mgr = self.mgr

        image = mgr.build_docker_image()
        self.assertIsInstance(image, docker.models.images.Image)
        self.assertEqual(
            set(image.tags),
            set([mgr.docker_image_repo + ':' + tag for tag in mgr.docker_image_tags]))

        image = mgr._docker_client.images.get(mgr.docker_image_repo + ':' + mgr.docker_image_tags[0])
        self.assertEqual(
            set(image.tags),
            set([mgr.docker_image_repo + ':' + tag for tag in mgr.docker_image_tags]))

    def test_build_docker_image_verbose(self):
        mgr = self.mgr
        mgr.verbose = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_docker_image()
            self.assertRegex(capture_output.get_text(), r'Step 1/2 : FROM ubuntu')

    def test_build_docker_image_context_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        docker_image_context_path = mgr.docker_image_context_path
        mgr.docker_image_context_path += '.null'

        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, ' must be a directory'):
            mgr.build_docker_image()

        mgr.docker_image_context_path = docker_image_context_path

    @unittest.skipUnless(whichcraft.which('systemctl'), 'Unable to stop Docker service')
    def test_build_docker_image_connection_error(self):
        mgr = self.mgr

        # stop Docker service
        subprocess.check_call(['systemctl', 'stop', 'docker'])

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker connection error:'):
            mgr.build_docker_image()

        # restart Docker service
        subprocess.check_call(['systemctl', 'start', 'docker'])

    def test_build_docker_image_api_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.dockerfile_path, 'w') as file:
            file.write('FROM2 ubuntu\n')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker API error:'):
            mgr.build_docker_image()

    def test_build_docker_image_build_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.dockerfile_path, 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('RUN exit 1')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker build error:'):
            mgr.build_docker_image()

    def test_build_docker_image_other_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with mock.patch.object(docker.models.images.ImageCollection, 'build', side_effect=Exception('message')):
            with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Exception:\n  message'):
                mgr.build_docker_image()

    def test_remove_docker_image(self):
        mgr = self.mgr

        image = mgr.build_docker_image()
        for tag in mgr.docker_image_tags:
            mgr._docker_client.images.get(mgr.docker_image_repo + ':' + tag)

        mgr.remove_docker_image()
        for tag in mgr.docker_image_tags:
            with self.assertRaises(docker.errors.ImageNotFound):
                mgr._docker_client.images.get(mgr.docker_image_repo + ':' + tag)


class WcEnvManagerTestCase(unittest.TestCase):
    def setUp(self):
        mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.pull_docker_image()
        mgr.remove_docker_containers(force=True)

    def tearDown(self):
        self.mgr.remove_docker_containers(force=True)

    def test_login_dockerhub(self):
        mgr = self.mgr
        self.assertNotIn('docker.io', mgr._docker_client.api._auth_configs['auths'])
        mgr.login_dockerhub()  # test for no runtime error
        self.assertIn('docker.io', mgr._docker_client.api._auth_configs['auths'])

    def test_push_docker_image(self):
        mgr = self.mgr
        mgr.login_dockerhub()
        mgr.push_docker_image()

    def test_pull_docker_image(self):
        mgr = self.mgr
        image = mgr.pull_docker_image()
        self.assertIsInstance(image, docker.models.images.Image)

    def test_set_docker_image(self):
        mgr = self.mgr
        image = mgr.get_latest_docker_image()

        mgr._docker_image = None
        mgr.set_docker_image(image)
        self.assertEqual(mgr._docker_image, image)

        mgr._docker_image = None
        mgr.set_docker_image(image.tags[0])
        self.assertEqual(mgr._docker_image, image)

    def test_get_latest_docker_image(self):
        mgr = self.mgr
        image = mgr.get_latest_docker_image()
        self.assertIsInstance(image, docker.models.images.Image)

    def test_get_docker_image_version(self):
        mgr = self.mgr
        version = mgr.get_docker_image_version()
        self.assertRegex(version, r'^\d+\.\d+\.\d+[a-z0A-Z-9]*$')

    def test_create_docker_container(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertIsInstance(container, docker.models.containers.Container)

    def test_make_docker_container_name(self):
        mgr = self.mgr
        mgr.docker_container_name_format = 'wc_env-%Y'
        self.assertEqual(mgr.make_docker_container_name(), 'wc_env-{}'.format(datetime.datetime.now().year))

    @unittest.skip('todo')
    def test_setup_docker_container(self):
        pass

    def test_set_docker_container(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertEqual(mgr._docker_container, container)
        self.assertEqual(mgr.get_latest_docker_container(), container)

        mgr._docker_container = None
        mgr.set_docker_container(container)
        self.assertEqual(mgr._docker_container, container)

        mgr._docker_container = None
        mgr.set_docker_container(container.name)
        self.assertEqual(mgr._docker_container, container)

    def test_get_latest_docker_container(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertEqual(mgr.get_latest_docker_container(), container)

    def test_get_docker_containers(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        containers = mgr.get_docker_containers()
        self.assertEqual(containers, [container])

    def test_get_docker_container_stats(self):
        mgr = self.mgr
        mgr.create_docker_container()
        stats = mgr.get_docker_container_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('cpu_stats', stats)
        self.assertIn('memory_stats', stats)

    def test_stop_docker_container(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertEqual(container.status, 'created')
        mgr.stop_docker_container()
        self.assertEqual(container.status, 'created')

    def test_remove_docker_container(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertNotEqual(mgr._docker_container, None)
        mgr.remove_docker_container(force=True)
        self.assertEqual(mgr._docker_container, None)
        self.assertEqual(mgr.get_docker_containers(), [])

    def test_remove_docker_containers(self):
        mgr = self.mgr
        container = mgr.create_docker_container()
        self.assertNotEqual(mgr._docker_container, None)
        mgr.remove_docker_containers(force=True)
        self.assertEqual(mgr._docker_container, None)
        self.assertEqual(mgr.get_docker_containers(), [])


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
        if exit_code == 0:
            return output.decode('utf-8')
        else:
            raise wc_env_manager.WcEnvManagerError("{}:{}: cat {} fails with exit_code {} "
                                                   "this is a Docker system race condition; rerun test".format(
                                                       frameinfo.filename, frameinfo.lineno, file, exit_code))

    @staticmethod
    def cmp_files(testcase, container, container_filename, host_file_content=None, host_filename=None):
        """ Make testcase comparison of content of file on host with file in container

        At least one of `host_file_content` or `host_filename` must be provided.
        Will not scale to huge files.

        Args:
            testcase (:obj:`unittest.TestCase`): testcase being run
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


# use pytest --durations to report slow tests
DONT_RUN_SLOW_TESTS = True

# todo: port to and test on Windows
# todo: perhaps try to speedup testing; could reuse containers


class WcEnvTestCase(unittest.TestCase):

    def setUp(self):
        # use mkdtemp() instead of TemporaryDirectory() so files can be saved for debugging containers
        #   after testing by setting `remove_temp_files`

        # put test_dir in /private/tmp which can contain a Docker volume by default
        self.test_dir = tempfile.mkdtemp(dir='/private/tmp')
        self.temp_dir_in_home = \
            tempfile.mkdtemp(dir=os.path.abspath(os.path.expanduser('~/tmp')))
        self.test_dir_in_home = os.path.join('~/tmp', os.path.basename(self.temp_dir_in_home))
        self.relative_path_file = os.path.join('tests', 'fixtures', 'relative_path_file.txt')

        self.absolute_path_file = os.path.join(os.getcwd(), self.relative_path_file)
        self.moving_text = 'I Have a Dream'
        with open(self.absolute_path_file, 'w') as f:
            f.write(self.moving_text)

        tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        self.relative_temp_path = tempfile.mkdtemp(dir=tmp_dir)

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
        # WCenvs with created containers that need to be removed
        self.tmp_container_managers = []

        self.manage_container = self.make_container(wc_repos=self.test_wc_repos)
        self.container = self.manage_container.create()

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
            shutil.rmtree(os.path.dirname(self.relative_temp_path))
            shutil.rmtree(self.test_dir)
            shutil.rmtree(self.temp_dir_in_home)

    @classmethod
    def tearDownClass(cls):
        list_all_containers = False
        if list_all_containers:
            DockerUtils.list_all()

    def make_test_repo(self, relative_path):
        # copy contents of self.sample_repo to a test repo at `relative_path`
        test_repo = os.path.abspath(os.path.expanduser(relative_path))
        shutil.copytree(self.sample_repo, test_repo)
        # create a unique repo name file
        with open(os.path.join(test_repo, 'REPO_NAME'), 'w') as f:
            f.write(os.path.basename(test_repo))

    def test_constructor(self):
        manage_container = wc_env_manager.WcEnv(self.test_wc_repos, '0.1')
        expected_repo_paths = [
            os.path.join(self.temp_dir_in_home, 'repo_a'),
            os.path.join(self.test_dir, 'repo_b'),
            os.path.join(os.getcwd(), self.relative_temp_path, 'repo_c')
        ]
        for computed_path, expected_path in zip(manage_container.local_wc_repos, expected_repo_paths):
            self.assertEqual(computed_path, expected_path)
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            wc_env_manager.WcEnv([self.absolute_path_file], '0.1')
        repo_a = os.path.join(self.temp_dir_in_home, 'repo_a')
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            # redundant repos
            wc_env_manager.WcEnv([repo_a, repo_a], '0.1')
        os.chmod(repo_a, 0)
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            # unreadable repo
            wc_env_manager.WcEnv([repo_a], '0.1')
        os.chmod(repo_a, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def do_check_credentials(self, test_configs_repo_pwd_file, expected):
        # check WcEnv.check_credentials()
        manage_container = wc_env_manager.WcEnv([], '0.1',
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
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            manage_container = wc_env_manager.WcEnv([], '0.1',
                                                    configs_repo_pwd_file=test_no_such_file, ssh_key=test_no_such_file)

    def test_build(self):
        manage_image = wc_env_manager.WcEnv([], '0.0.1', verbose=True)
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            with open(os.path.join(os.path.dirname(__file__),
                                   'fixtures/docker_files/bad_Dockerfile'), 'rb') as dockerfile_fileobj:
                manage_image.build(fileobj=dockerfile_fileobj)
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            path = os.path.join(os.path.dirname(__file__), 'fixtures/docker_files/empty_dir')
            manage_image.build(path=path)
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            manage_image.build(path='dummy', fileobj='dummy')
        with CaptureOutput() as capturer:
            with open(os.path.join(os.path.dirname(__file__),
                                   'fixtures/docker_files/simple_busybox_Dockerfile'), 'rb') as dockerfile_fileobj:
                image = manage_image.build(fileobj=dockerfile_fileobj)
                self.assertTrue(type(image), docker.models.images.Image)
                expected_output = ['Docker build command: docker build --pull --file',
                                   'Running: docker_client.build',
                                   'Successfully built', ]
                for line in expected_output:
                    self.assertIn(line, capturer.get_text())

    def test_build_default_path(self):
        current = os.getcwd()
        docker_dir = os.path.join(os.path.dirname(__file__), 'fixtures/docker_files')
        os.chdir(docker_dir)
        manage_image = wc_env_manager.WcEnv([], '0.0.1')
        self.assertTrue(type(manage_image.build()), docker.models.images.Image)
        os.chdir(current)

    def test_create(self):
        # spot-check files in the 3 repos in the container
        for local_wc_repo in self.manage_container.local_wc_repos:
            container_wc_repo_dir = os.path.join(self.manage_container.container_repo_dir,
                                                 os.path.basename(local_wc_repo))
            container_core_py_file = os.path.join(container_wc_repo_dir, 'tests/requirements.txt')
            DockerUtils.cmp_files(self, self.container, container_core_py_file,
                                  host_filename=os.path.join(self.sample_repo, 'tests/requirements.txt'))
            container_REPO_NAME_file = os.path.join(container_wc_repo_dir, 'REPO_NAME')
            DockerUtils.cmp_files(self, self.container, container_REPO_NAME_file,
                                  host_file_content=os.path.basename(local_wc_repo))

        # just ssh_key
        manage_container = wc_env_manager.WcEnv([], '0.0.1', git_config_file=None)
        self.tmp_container_managers.append(manage_container)
        manage_container.create()

        # just .gitconfig
        manage_container = wc_env_manager.WcEnv([], '0.0.1', ssh_key=None)
        self.tmp_container_managers.append(manage_container)
        manage_container.create()

    def test_create_exceptions(self):
        manage_container = wc_env_manager.WcEnv([], '0.0.1')
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            manage_container.create(name='bad container name, spaces not legal')

    def test_cp(self):
        with self.assertRaises(subprocess.CalledProcessError):
            # it is an error if DEST_PATH does not exist and ends with /
            self.manage_container.cp(self.absolute_path_file, '/root/tmp/no such dir/')
        path_in_container = os.path.join('/tmp/', os.path.basename(self.absolute_path_file))
        self.manage_container.cp(self.absolute_path_file, path_in_container)
        DockerUtils.cmp_files(self, self.manage_container.container, path_in_container, host_file_content=self.moving_text)

    def test_pp_to_karr_lab_repos(self):
        pythonpath = self.manage_container.pp_to_karr_lab_repos()
        for wc_repo_path in self.test_wc_repos:
            wc_repo = os.path.basename(wc_repo_path)
            self.assertIn(wc_repo, pythonpath)
        for cloned_karr_lab_repo in wc_env_manager.WcEnv.all_wc_repos():
            self.assertIn(cloned_karr_lab_repo, pythonpath)
        for wc_repo_path in self.test_wc_repos:
            wc_repo = os.path.basename(wc_repo_path)
            for cloned_karr_lab_repo in wc_env_manager.WcEnv.all_wc_repos():
                self.assertTrue(pythonpath.index(wc_repo) <= pythonpath.index(cloned_karr_lab_repo))

    def make_container(self, wc_repos=None, save_container=False, verbose=False):
        # make a test container
        # provide wc_repos to create volumes for them
        # set save_container to save the container for later investigation
        # set verbose to produce verbose output
        if wc_repos is None:
            wc_repos = []
        manage_container = wc_env_manager.WcEnv(wc_repos, '0.0.1', verbose=verbose)
        container = manage_container.create()
        if save_container:
            print("docker attach {}".format(container.name))
        else:
            self.tmp_container_managers.append(manage_container)
        return manage_container

    @unittest.skipIf(DONT_RUN_SLOW_TESTS, "skipping slow tests")
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
                               'pip install karr_lab_build_utils --', ]
            for line in expected_output:
                self.assertIn(line, capturer.get_text())

    def test_clone_karr_lab_repos(self):
        manage_container = self.make_container()
        manage_container.clone_karr_lab_repos()
        kl_repos = manage_container.exec_run('ls {}'.format(manage_container.container_local_repos))
        kl_repos = set(kl_repos.split('\n'))
        self.assertTrue(set(wc_env_manager.WcEnv.all_wc_repos()).issubset(kl_repos))

    @unittest.skipIf(DONT_RUN_SLOW_TESTS, "skipping slow tests")
    def test_run(self):
        manage_container = self.make_container(wc_repos=self.test_wc_repos)
        self.assertEqual(type(manage_container.run()), docker.models.containers.Container)

    def test_cp_exceptions(self):
        manage_container = wc_env_manager.WcEnv([], '0.0.1')
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            manage_container.cp(self.absolute_path_file, '')
        with self.assertRaises(wc_env_manager.WcEnvManagerError):
            manage_container.cp('no such file', '')

    def test_exec_run(self):
        with CaptureOutput(relay=False) as capturer:
            manage_container = self.make_container(verbose=True)
            with self.assertRaises(wc_env_manager.WcEnvManagerError):
                manage_container.exec_run('no_such_command x')
            ls = set(manage_container.exec_run('ls').split('\n'))
            self.assertTrue(set('usr bin home tmp root etc lib'.split()).issubset(ls))
            verbose_output = ['Running: containers.run',
                              'Running: container.exec_run(ssh-keyscan',
                              'Running: container.exec_run(no_such_command x)',
                              'Running: container.exec_run(ls)']
            for verbose_line in verbose_output:
                self.assertIn(verbose_line, capturer.get_text())
