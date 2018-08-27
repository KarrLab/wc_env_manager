""" Tests for wc_env_manager.core

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-08-23
:Copyright: 2018, Karr Lab
:License: MIT
"""

from capturer import CaptureOutput
from inspect import currentframe, getframeinfo
import capturer
import datetime
import docker
import git
import mock
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
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
            base_docker_image_repo='karrlab/test',
            base_docker_image_tags=['0.0.1', 'latest'],
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

        image = mgr.build_base_docker_image()
        self.assertIsInstance(image, docker.models.images.Image)
        self.assertEqual(
            set(image.tags),
            set([mgr.base_docker_image_repo + ':' + tag for tag in mgr.base_docker_image_tags]))

        image = mgr._docker_client.images.get(mgr.base_docker_image_repo + ':' + mgr.base_docker_image_tags[0])
        self.assertEqual(
            set(image.tags),
            set([mgr.base_docker_image_repo + ':' + tag for tag in mgr.base_docker_image_tags]))

    def test_build_docker_image_verbose(self):
        mgr = self.mgr
        mgr.verbose = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_base_docker_image()
            self.assertRegex(capture_output.get_text(), r'Step 1/2 : FROM ubuntu')

    def test_build_docker_image_context_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        docker_image_context_path = mgr.docker_image_context_path
        mgr.docker_image_context_path += '.null'

        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, ' must be a directory'):
            mgr.build_base_docker_image()

        mgr.docker_image_context_path = docker_image_context_path

    @unittest.skipUnless(whichcraft.which('systemctl'), 'Unable to stop Docker service')
    def test_build_docker_image_connection_error(self):
        mgr = self.mgr

        # stop Docker service
        subprocess.check_call(['systemctl', 'stop', 'docker'])

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker connection error:'):
            mgr.build_base_docker_image()

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
            mgr.build_base_docker_image()

    def test_build_docker_image_build_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.dockerfile_path, 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('RUN exit 1')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker build error:'):
            mgr.build_base_docker_image()

    def test_build_docker_image_other_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with mock.patch.object(docker.models.images.ImageCollection, 'build', side_effect=Exception('message')):
            with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Exception:\n  message'):
                mgr.build_base_docker_image()

    def test_remove_docker_image(self):
        mgr = self.mgr

        image = mgr.build_base_docker_image()
        for tag in mgr.base_docker_image_tags:
            mgr._docker_client.images.get(mgr.base_docker_image_repo + ':' + tag)

        mgr.remove_docker_image()
        for tag in mgr.base_docker_image_tags:
            with self.assertRaises(docker.errors.ImageNotFound):
                mgr._docker_client.images.get(mgr.base_docker_image_repo + ':' + tag)


class WcEnvManagerTestCase(unittest.TestCase):
    def setUp(self):
        mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.pull_docker_image()
        mgr.remove_docker_containers(force=True)

    def tearDown(self):
        # todo: remove
        # self.mgr.remove_docker_containers(force=True)
        pass

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

        temp_dir_name_a = tempfile.mkdtemp()
        temp_dir_name_b = tempfile.mkdtemp()

        mgr.paths_to_mount_to_docker_container = {
            temp_dir_name_a: {
                'bind': '/root/host/mount-a',
                'mode': 'rw',
            },
            temp_dir_name_b: {
                'bind': '/root/host/mount-b',
                'mode': 'rw',
            },
        }
        container = mgr.create_docker_container()
        self.assertIsInstance(container, docker.models.containers.Container)

        mgr.run_process_in_docker_container('bash -c "echo abc >> /root/host/mount-a/test_a"')
        mgr.run_process_in_docker_container('bash -c "echo 123 >> /root/host/mount-b/test_b"')

        with open(os.path.join(temp_dir_name_a, 'test_a'), 'r') as file:
            self.assertEqual(file.read(), 'abc\n')
        with open(os.path.join(temp_dir_name_b, 'test_b'), 'r') as file:
            self.assertEqual(file.read(), '123\n')

        shutil.rmtree(temp_dir_name_a)
        shutil.rmtree(temp_dir_name_b)

    def test_make_docker_container_name(self):
        mgr = self.mgr
        mgr.docker_container_name_format = 'wc_env-%Y'
        self.assertEqual(mgr.make_docker_container_name(), 'wc_env-{}'.format(datetime.datetime.now().year))

    def test_setup_docker_container(self):
        mgr = self.mgr
        mgr.verbose = True

        temp_dir_name = tempfile.mkdtemp()

        with open(os.path.join(temp_dir_name, 'a'), 'w') as file:
            file.write('ABC')
        with open(os.path.join(temp_dir_name, 'b'), 'w') as file:
            file.write('DEF')
        mgr.paths_to_copy_to_docker_container = {
            'a': {
                'host': os.path.join(temp_dir_name, 'a'),
                'container': '/tmp/a',
            },
            'b': {
                'host': os.path.join(temp_dir_name, 'b'),
                'container': '/tmp/b',
            },
        }

        git.Repo.clone_from('https://github.com/KarrLab/wc_utils.git',
                            os.path.join(temp_dir_name, 'wc_utils'))
        mgr.paths_to_mount_to_docker_container = {
            temp_dir_name: {
                'bind': '/root/host/Documents',
                'mode': 'rw',
            }
        }

        mgr.python_packages_from_github = '''
        git+https://github.com/KarrLab/mycoplasma_pneumoniae.git#egg=mycoplasma_pneumoniae-0.0.1[all]
        git+https://github.com/KarrLab/intro_to_wc_modeling.git#egg=intro_to_wc_modeling-0.0.1[all]
        '''
        mgr.python_packages_from_host = '''
        /root/host/Documents/wc_utils
        '''

        mgr.create_docker_container()
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_docker_container()
            text = capture_output.get_text()
        self.assertRegex(text, r'Processing /root/host/Documents/wc_utils')
        self.assertRegex(text, r'Successfully installed wc-utils')

        mgr.copy_path_from_docker_container('/tmp/a',
                                            os.path.join(temp_dir_name, 'a2'))
        mgr.copy_path_from_docker_container('/tmp/b',
                                            os.path.join(temp_dir_name, 'b2'))
        with open(os.path.join(temp_dir_name, 'a2'), 'r') as file:
            self.assertEqual(file.read(), 'ABC')
        with open(os.path.join(temp_dir_name, 'b2'), 'r') as file:
            self.assertEqual(file.read(), 'DEF')

        shutil.rmtree(temp_dir_name)

    @unittest.skip('long test')
    def test_setup_docker_container_full(self):
        mgr = self.mgr
        mgr.verbose = True
        mgr.create_docker_container()
        mgr.setup_docker_container()

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_copy_config_files_to_docker_container(self):
        mgr = self.mgr
        mgr.create_docker_container()
        mgr.copy_config_files_to_docker_container()

        result, _ = mgr.run_process_in_docker_container('bash -c "if [ -d ~/.wc ]; then echo 1; fi"')
        self.assertEqual(result, '1')

        result, _ = mgr.run_process_in_docker_container('bash -c "if [ -f ~/.wc/third_party/paths.yml ]; then echo 1; fi"')
        self.assertEqual(result, '1')

        result, _ = mgr.run_process_in_docker_container('bash -c "if [ -f ~/.ssh/id_rsa ]; then echo 1; fi"')
        self.assertEqual(result, '1')

    def test_copy_path_to_from_docker_container(self):
        mgr = self.mgr
        mgr.create_docker_container()

        temp_dir_name = tempfile.mkdtemp()
        temp_file_name = os.path.join(temp_dir_name, 'test.txt')
        with open(temp_file_name, 'w') as file:
            file.write('abc')

        mgr.copy_path_to_docker_container(temp_file_name, '/tmp/test.txt')
        mgr.copy_path_to_docker_container(temp_file_name, '/tmp/test.txt')  # overwrite
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'exists'):
            mgr.copy_path_to_docker_container(temp_file_name, '/tmp/test.txt', overwrite=False)

        os.remove(temp_file_name)
        mgr.copy_path_from_docker_container('/tmp/test.txt', temp_file_name)
        mgr.copy_path_from_docker_container('/tmp/test.txt', temp_file_name)  # overwrite
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'exists'):
            mgr.copy_path_from_docker_container('/tmp/test.txt', temp_file_name, overwrite=False)

        with open(temp_file_name, 'r') as file:
            self.assertEqual(file.read(), 'abc')

        shutil.rmtree(temp_dir_name)

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_install_github_ssh_host_in_docker_container(self):
        mgr = self.mgr
        mgr.create_docker_container()
        mgr.copy_config_files_to_docker_container()
        mgr.install_github_ssh_host_in_docker_container()

        _, temp_file_name = tempfile.mkstemp()
        mgr.copy_path_from_docker_container('/root/.ssh/known_hosts', temp_file_name)
        with open(temp_file_name, 'r') as file:
            self.assertRegex(file.read(), r'github\.com ssh-rsa')
        os.remove(temp_file_name)

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_install_github_ssh_host_in_docker_container_upgrade(self):
        mgr = self.mgr
        mgr.create_docker_container()
        mgr.copy_config_files_to_docker_container()
        mgr.install_github_ssh_host_in_docker_container(upgrade=True)

        _, temp_file_name = tempfile.mkstemp()
        mgr.copy_path_from_docker_container('/root/.ssh/known_hosts', temp_file_name)
        with open(temp_file_name, 'r') as file:
            self.assertRegex(file.read(), r'github\.com ssh-rsa')
        os.remove(temp_file_name)

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_test_github_ssh_access_in_docker_container(self):
        mgr = self.mgr
        mgr.create_docker_container()
        mgr.copy_config_files_to_docker_container()
        mgr.install_github_ssh_host_in_docker_container()

        self.assertTrue(mgr.test_github_ssh_access_in_docker_container())

    def test_install_python_packages_in_docker_container(self):
        mgr = self.mgr
        mgr.verbose = True
        container = mgr.create_docker_container()

        # not upgrade
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.install_python_packages_in_docker_container(
                '''
                # comment
                pip
                ''')
            self.assertRegex(capture_output.get_text(), 'Requirement already satisfied: pip')

        # upgrade, process dependency links
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.install_python_packages_in_docker_container(
                '''
                # comment
                pytest
                ''', upgrade=True, process_dependency_links=True)
            self.assertRegex(capture_output.get_text(), 'Successfully installed pytest')

    def test_install_python_packages_in_docker_container_error(self):
        mgr = self.mgr
        mgr.python_packages_from_github = ''
        mgr.python_packages_from_host = ''
        container = mgr.create_docker_container()
        mgr.setup_docker_container()
        mgr.run_process_in_docker_container(['bash', '-c', 'rm ~/.gitconfig'])

        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'No matching distribution'):
            mgr.install_python_packages_in_docker_container(
                'undefined_package')
        
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'could not read Username'):
            mgr.install_python_packages_in_docker_container(
                'git+https://github.com/KarrLab/undefined_package.git#egg=undefined_package-0.0.1[all]')

        mgr.copy_config_files_to_docker_container(overwrite=True)
        mgr.run_process_in_docker_container(['bash', '-c', 'rm ~/.ssh/known_hosts'])
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Host key verification failed'):
            mgr.install_python_packages_in_docker_container(
                'git+https://github.com/KarrLab/undefined_package.git#egg=undefined_package-0.0.1[all]')

        mgr.copy_config_files_to_docker_container(overwrite=True)
        mgr.install_github_ssh_host_in_docker_container()
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Repository not found'):
            mgr.install_python_packages_in_docker_container(
                'git+https://github.com/KarrLab/undefined_package.git#egg=undefined_package-0.0.1[all]')

    def test_convert_host_to_container_path(self):
        mgr = self.mgr
        mgr.paths_to_mount_to_docker_container = {
            '/home/test_host_dir': {
                'bind': '/root/test_container_dir',
                'mode': 'rw',
            },
            '.': {
                'bind': '/root/package',
                'mode': 'rw',
            }
        }
        self.assertEqual(mgr.convert_host_to_container_path(
            '/home/test_host_dir/test_file'),
            '/root/test_container_dir/test_file')
        self.assertEqual(mgr.convert_host_to_container_path(
            '/home/test_host_dir/a/b/c/test_file'),
            '/root/test_container_dir/a/b/c/test_file')

        self.assertEqual(mgr.convert_host_to_container_path(
            'tests/test_core.py'),
            '/root/package/tests/test_core.py')

        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'not mounted'):
            mgr.convert_host_to_container_path(
                '/home/not_mounted/a/b/c/test_file')

    def test_convert_container_to_host_path(self):
        mgr = self.mgr
        mgr.paths_to_mount_to_docker_container = {
            '/home/test_host_dir': {
                'bind': '/root/test_container_dir',
                'mode': 'rw',
            },
            '.': {
                'bind': '/root/package',
                'mode': 'rw',
            }
        }
        self.assertEqual(mgr.convert_container_to_host_path(
            '/root/test_container_dir/test_file'),
            '/home/test_host_dir/test_file')
        self.assertEqual(mgr.convert_container_to_host_path(
            '/root/test_container_dir/a/b/c/test_file'),
            '/home/test_host_dir/a/b/c/test_file')

        self.assertEqual(mgr.convert_container_to_host_path(
            '/root/package/tests/test_core.py'),
            './tests/test_core.py')

        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'not mounted'):
            mgr.convert_container_to_host_path(
                '/root/not_mounted/a/b/c/test_file')

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

    def test_run_process_in_docker_container(self):
        mgr = self.mgr
        mgr.create_docker_container()

        # not verbose
        mgr.verbose = False
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_docker_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), '')

        # verbose
        mgr.verbose = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_docker_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), 'here')

        # error
        mgr.verbose = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '  exit code: 126'):
            mgr.run_process_in_docker_container(['__undefined__'])

        # error, specified working directory
        mgr.verbose = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '  working directory: /root'):
            mgr.run_process_in_docker_container(['__undefined__'], work_dir='/root')

        # error, specified environment
        mgr.verbose = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '    key: val'):
            mgr.run_process_in_docker_container(['__undefined__'], env={'key': 'val'})

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

    def test_run_process_on_host(self):
        mgr = self.mgr

        mgr.verbose = False
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_on_host(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), '')

        mgr.verbose = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_on_host(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), 'here')


class ExampleTestCase(unittest.TestCase):
    def test(self):
        self.assertTrue(True)
        self.assertFalse(False)
