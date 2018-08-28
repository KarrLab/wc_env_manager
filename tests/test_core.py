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
import yaml


class WcEnvManagerBuildRemoveBaseImageTestCase(unittest.TestCase):
    def setUp(self):
        self.remove_images()

        docker_image_context_path = tempfile.mkdtemp()
        dockerfile_path = os.path.join(docker_image_context_path, 'Dockerfile')
        with open(dockerfile_path, 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('CMD bash\n')

        self.mgr = wc_env_manager.core.WcEnvManager({
            'base_image': {
                'repo': 'karrlab/test',
                'tags': ['0.0.1', 'latest'],
                'dockerfile_path': dockerfile_path,
                'context_path': docker_image_context_path,
            },
        })

    def tearDown(self):
        self.remove_images()
        shutil.rmtree(self.mgr.config['base_image']['context_path'])

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

    def test_build_base_docker_image(self):
        mgr = self.mgr
        config = mgr.config

        image = mgr.build_base_docker_image()
        self.assertIsInstance(image, docker.models.images.Image)
        self.assertEqual(
            set(image.tags),
            set([config['base_image']['repo'] + ':' + tag for tag in config['base_image']['tags']]))

        image = mgr._docker_client.images.get(config['base_image']['repo'] + ':' + config['base_image']['tags'][0])
        self.assertEqual(
            set(image.tags),
            set([config['base_image']['repo'] + ':' + tag for tag in config['base_image']['tags']]))

    def test_build_base_docker_image_verbose(self):
        mgr = self.mgr
        mgr.config['verbose'] = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_base_docker_image()
            self.assertRegex(capture_output.get_text(), r'Step 1/2 : FROM ubuntu')

    def test_build_base_docker_image_context_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        context_path = mgr.config['base_image']['context_path']

        mgr.config['base_image']['context_path'] += '.null'
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, ' must be a directory'):
            mgr.build_base_docker_image()

        mgr.config['base_image']['context_path'] = context_path
        mgr.config['base_image']['dockerfile_path'] = '/Dockerfile'
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, ' must be inside '):
            mgr.build_base_docker_image()

    @unittest.skipUnless(whichcraft.which('systemctl'), 'Unable to stop Docker service')
    def test_build_base_docker_image_connection_error(self):
        mgr = self.mgr

        # stop Docker service
        subprocess.check_call(['systemctl', 'stop', 'docker'])

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker connection error:'):
            mgr.build_base_docker_image()

        # restart Docker service
        subprocess.check_call(['systemctl', 'start', 'docker'])

    def test_build_base_docker_image_api_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.config['base_image']['dockerfile_path'], 'w') as file:
            file.write('FROM2 ubuntu\n')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker API error:'):
            mgr.build_base_docker_image()

    def test_build_base_docker_image_build_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.config['base_image']['dockerfile_path'], 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('RUN exit 1')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Docker build error:'):
            mgr.build_base_docker_image()

    def test_build_base_docker_image_other_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with mock.patch.object(docker.models.images.ImageCollection, 'build', side_effect=Exception('message')):
            with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'Exception:\n  message'):
                mgr.build_base_docker_image()

    def test_remove_docker_image(self):
        mgr = self.mgr

        image = mgr.build_base_docker_image()
        for tag in mgr.config['base_image']['tags']:
            mgr._docker_client.images.get(mgr.config['base_image']['repo'] + ':' + tag)

        mgr.remove_docker_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])
        for tag in mgr.config['base_image']['tags']:
            with self.assertRaises(docker.errors.ImageNotFound):
                mgr._docker_client.images.get(mgr.config['base_image']['repo'] + ':' + tag)


class WcEnvManagerBuildRemoveImageTestCase(unittest.TestCase):
    def setUp(self):
        self.mgr = wc_env_manager.core.WcEnvManager()

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_get_config_file_paths_to_copy_to_docker_image(self):
        mgr = self.mgr

        temp_dir_name = tempfile.mkdtemp()
        os.mkdir(os.path.join(temp_dir_name, 'third_party'))
        with open(os.path.join(temp_dir_name, 'third_party', 'paths.yml'), 'w') as file:
            yaml.dump({
                '.gitconfig': '/root/.gitconfig',
                'mosek.lic': '/root/mosek/mosek.lic',
            }, file)
        with open(os.path.join(temp_dir_name, 'third_party', '.gitconfig'), 'w') as file:
            pass
        with open(os.path.join(temp_dir_name, 'third_party', '.mosek.lic'), 'w') as file:
            pass

        mgr.config['image']['config_path'] = temp_dir_name
        paths = mgr.get_config_file_paths_to_copy_to_docker_image()

        self.assertEqual(3, len(paths))
        self.assertIn({
            'host': temp_dir_name,
            'image': '/root/.wc',
        }, paths)
        self.assertIn({
            'host': os.path.join(temp_dir_name, 'third_party', '.gitconfig'),
            'image': '/root/.gitconfig',
        }, paths)
        self.assertIn({
            'host': os.path.join(temp_dir_name, 'third_party', 'mosek.lic'),
            'image': '/root/mosek/mosek.lic',
        }, paths)

        shutil.rmtree(temp_dir_name)

    def test_build_docker_image(self):
        mgr = self.mgr
        mgr.config['verbose'] = True

        mgr.config['image']['tags'] = ['test']

        temp_dir_name = tempfile.mkdtemp()
        with open(os.path.join(temp_dir_name, 'a'), 'w') as file:
            file.write('ABC')
        with open(os.path.join(temp_dir_name, 'b'), 'w') as file:
            file.write('DEF')
        mgr.config['image']['paths_to_copy'] = {
            'a': {
                'host': os.path.join(temp_dir_name, 'a'),
                'image': '/tmp/a',
            },
            'b': {
                'host': os.path.join(temp_dir_name, 'b'),
                'image': '/tmp/b',
            },
        }

        mgr.config['image']['python_packages'] = '''
        git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1[all]
        git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1[all]
        '''

        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_docker_image()
            text = capture_output.get_text()
            self.assertRegex(text, 'Successfully installed .*?wc-lang-')
            self.assertRegex(text, 'Successfully installed .*?wc-utils-')
            self.assertRegex(text, 'Successfully built')
        mgr.create_docker_container()

        mgr.copy_path_from_docker_container('/tmp/a',
                                            os.path.join(temp_dir_name, 'a2'))
        mgr.copy_path_from_docker_container('/tmp/b',
                                            os.path.join(temp_dir_name, 'b2'))
        with open(os.path.join(temp_dir_name, 'a2'), 'r') as file:
            self.assertEqual(file.read(), 'ABC')
        with open(os.path.join(temp_dir_name, 'b2'), 'r') as file:
            self.assertEqual(file.read(), 'DEF')

        shutil.rmtree(temp_dir_name)
        mgr.stop_docker_container()
        mgr.remove_docker_containers()
        mgr.remove_docker_image(mgr.config['image']['repo'], mgr.config['image']['tags'])


class WcEnvManagerTestCase(unittest.TestCase):
    def setUp(self):
        mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.pull_docker_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])
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
        mgr.push_docker_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])

    def test_pull_docker_image(self):
        mgr = self.mgr
        image = mgr.pull_docker_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])
        self.assertIsInstance(image, docker.models.images.Image)

        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['base_image']['repo'] = None
        mgr.config['base_image']['tags'] = None
        image = mgr.pull_docker_image(mgr.config['image']['repo'], mgr.config['image']['tags'])
        self.assertIsInstance(image, docker.models.images.Image)

    def test_set_docker_image(self):
        mgr = self.mgr
        image = mgr.get_latest_docker_image(mgr.config['base_image']['repo'])

        mgr._base_image = None
        mgr._image = None
        mgr.set_docker_image(mgr.config['base_image']['repo'], image)
        self.assertEqual(mgr._base_image, image)
        self.assertEqual(mgr._image, None)

        mgr._base_image = None
        mgr._image = None
        mgr.set_docker_image(mgr.config['base_image']['repo'], image.tags[0])
        self.assertEqual(mgr._base_image, image)
        self.assertEqual(mgr._image, None)

        mgr._base_image = None
        mgr._image = None
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['base_image']['repo'] = None
        mgr.set_docker_image(mgr.config['image']['repo'], image.tags[0])
        self.assertEqual(mgr._base_image, None)
        self.assertEqual(mgr._image, image)

    def test_get_latest_docker_image(self):
        mgr = self.mgr
        image = mgr.get_latest_docker_image(mgr.config['base_image']['repo'])
        self.assertIsInstance(image, docker.models.images.Image)

    def test_get_docker_image_version(self):
        mgr = self.mgr
        version = mgr.get_docker_image_version(mgr._base_image)
        self.assertRegex(version, r'^\d+\.\d+\.\d+[a-z0A-Z-9]*$')

    def test_create_docker_container(self):
        mgr = self.mgr

        temp_dir_name_a = tempfile.mkdtemp()
        temp_dir_name_b = tempfile.mkdtemp()

        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['container']['paths_to_mount'] = {
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
        mgr.config['container']['name_format'] = 'wc_env-%Y'
        self.assertEqual(mgr.make_docker_container_name(), 'wc_env-{}'.format(datetime.datetime.now().year))

    def test_setup_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['verbose'] = True

        temp_dir_name = tempfile.mkdtemp()
        git.Repo.clone_from('https://github.com/KarrLab/wc_utils.git',
                            os.path.join(temp_dir_name, 'wc_utils'))
        mgr.config['container']['paths_to_mount'] = {
            temp_dir_name: {
                'bind': '/root/host/Documents',
                'mode': 'rw',
            }
        }

        mgr.config['container']['python_packages'] = '''
        /root/host/Documents/wc_utils
        '''

        mgr.create_docker_container()
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_docker_container()
            text = capture_output.get_text()
        self.assertRegex(text, r'Processing /root/host/Documents/wc_utils')
        self.assertRegex(text, r'Successfully installed .*?wc-utils-')

        shutil.rmtree(temp_dir_name)

    def test_setup_docker_container_with_python_packages(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['verbose'] = True
        container = mgr.create_docker_container()

        # not upgrade
        mgr.config['container']['python_packages'] = 'pip'
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_docker_container()
            self.assertRegex(capture_output.get_text(), 'Requirement already satisfied: pip')

        # upgrade, process dependency links
        mgr.config['container']['python_packages'] = 'pip'
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_docker_container(upgrade=True)
            self.assertRegex(capture_output.get_text(), '(Successfully installed|Requirement already up-to-date)')

    def test_setup_docker_container_with_python_packages_error(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['image']['python_packages'] = ''

        container = mgr.create_docker_container()
        mgr.config['container']['python_packages'] = 'undefined_package'
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, 'No matching distribution'):
            mgr.setup_docker_container()

    def test_copy_path_to_from_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
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

    def test_set_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        self.assertEqual(mgr._container, container)
        self.assertEqual(mgr.get_latest_docker_container(), container)

        mgr._container = None
        mgr.set_docker_container(container)
        self.assertEqual(mgr._container, container)

        mgr._container = None
        mgr.set_docker_container(container.name)
        self.assertEqual(mgr._container, container)

    def test_get_latest_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        self.assertEqual(mgr.get_latest_docker_container(), container)

    def test_get_docker_containers(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        containers = mgr.get_docker_containers()
        self.assertEqual(containers, [container])

    def test_run_process_in_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.create_docker_container()

        # not verbose
        mgr.config['verbose'] = False
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_docker_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), '')

        # verbose
        mgr.config['verbose'] = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_docker_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), 'here')

        # error
        mgr.config['verbose'] = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '  exit code: 126'):
            mgr.run_process_in_docker_container(['__undefined__'])

        # error, specified working directory
        mgr.config['verbose'] = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '  working directory: /root'):
            mgr.run_process_in_docker_container(['__undefined__'], work_dir='/root')

        # error, specified environment
        mgr.config['verbose'] = False
        with self.assertRaisesRegexp(wc_env_manager.WcEnvManagerError, '    key: val'):
            mgr.run_process_in_docker_container(['__undefined__'], env={'key': 'val'})

    def test_get_docker_container_stats(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.create_docker_container()
        stats = mgr.get_docker_container_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('cpu_stats', stats)
        self.assertIn('memory_stats', stats)

    def test_stop_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        self.assertEqual(container.status, 'created')
        mgr.stop_docker_container()
        self.assertEqual(container.status, 'created')

    def test_remove_docker_container(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        self.assertNotEqual(mgr._container, None)
        mgr.remove_docker_container(force=True)
        self.assertEqual(mgr._container, None)
        self.assertEqual(mgr.get_docker_containers(), [])

    def test_remove_docker_containers(self):
        mgr = self.mgr
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        container = mgr.create_docker_container()
        self.assertNotEqual(mgr._container, None)
        mgr.remove_docker_containers(force=True)
        self.assertEqual(mgr._container, None)
        self.assertEqual(mgr.get_docker_containers(), [])

    def test_run_process_on_host(self):
        mgr = self.mgr

        mgr.config['verbose'] = False
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_on_host(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), '')

        mgr.config['verbose'] = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_on_host(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), 'here')


class ExampleTestCase(unittest.TestCase):
    def test(self):
        self.assertTrue(True)
        self.assertFalse(False)
