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
import re
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

RUN_LONG_TESTS = False


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvManagerBuildRemoveBaseImageTestCase(unittest.TestCase):
    def setUp(self):
        self.remove_images()

        docker_image_context_path = tempfile.mkdtemp()
        dockerfile_template_path = os.path.join(docker_image_context_path, 'Dockerfile')
        with open(dockerfile_template_path, 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('ENV VAR1=val1\n')
            file.write('ENV VAR2=val2\n')
            file.write('ENV VAR3=val3\n')
            file.write('RUN echo "abc" >> /tmp/test.txt\n')
            file.write('RUN rm /tmp/test.txt\n')
            file.write('CMD bash\n')

        self.mgr = wc_env_manager.core.WcEnvManager({
            'base_image': {
                'repo_unsquashed': 'karrlab/test_unsquashed',
                'repo': 'karrlab/test',
                'tags': ['0.0.1', 'latest'],
                'dockerfile_template_path': dockerfile_template_path,
                'context_path': docker_image_context_path,
            },
        })
        self.mgr.config['image']['python_packages'] = '''
        git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1[all]
        git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1[all]
        '''

    def tearDown(self):
        self.remove_images()
        shutil.rmtree(self.mgr.config['base_image']['context_path'])

    def remove_images(self):
        client = docker.from_env()
        try:
            client.images.remove('karrlab/test_unsquashed:0.0.1')
        except docker.errors.ImageNotFound:
            pass
        try:
            client.images.remove('karrlab/test_unsquashed:latest')
        except docker.errors.ImageNotFound:
            pass
        try:
            client.images.remove('karrlab/test:0.0.1')
        except docker.errors.ImageNotFound:
            pass
        try:
            client.images.remove('karrlab/test:latest')
        except docker.errors.ImageNotFound:
            pass

    def test_get_required_python_packages(self):
        mgr = self.mgr
        self.mgr.config['image']['python_packages'] = '''
        git+https://github.com/KarrLab/kinetic_datanator.git#egg=kinetic_datanator-0.0.1[all]
        git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1[all]
        git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1[all]
        git+https://github.com/KarrLab/pkg_utils.git#egg=pkg_utils-0.0.3[all]
        git+https://github.com/KarrLab/pkg_utils.git#egg=pkg_utils-0.0.3[all]
        '''
        reqs = mgr.get_required_python_packages()
        self.assertIn('numpy', reqs)
        self.assertIn('requests', reqs)
        self.assertIn('requests_cache', reqs)
        self.assertIn('git+https://github.com/KarrLab/log.git#egg=log-2016.10.12', reqs)
        self.assertIn('git+https://github.com/davidfischer/requirements-parser.git#egg=requirements_parser-0.2.0 >= 0.2.0', reqs)

    def test_build_base_image(self):
        mgr = self.mgr
        config = mgr.config
        config['image']['python_packages'] = '''
        git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1[all]
        git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1[all]
        '''

        image = mgr.build_base_image()
        self.assertIsInstance(image, docker.models.images.Image)
        self.assertEqual(
            set(image.tags),
            set([config['base_image']['repo'] + ':' + tag for tag in config['base_image']['tags']]))

        image = mgr._docker_client.images.get(config['base_image']['repo_unsquashed'] + ':' + config['base_image']['tags'][0])
        self.assertEqual(
            set(image.tags),
            set([config['base_image']['repo_unsquashed'] + ':' + tag for tag in config['base_image']['tags']]))

        image = mgr._docker_client.images.get(config['base_image']['repo'] + ':' + config['base_image']['tags'][0])
        self.assertEqual(
            set(image.tags),
            set([config['base_image']['repo'] + ':' + tag for tag in config['base_image']['tags']]))

    def test_build_base_image_verbose(self):
        mgr = self.mgr
        mgr.config['verbose'] = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_base_image()
            self.assertRegex(capture_output.get_text(), r'Step 1/\d+ : FROM ubuntu')

    def test_build_base_image_context_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        context_path = mgr.config['base_image']['context_path']

        mgr.config['base_image']['context_path'] += '.null'
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, ' must be a directory'):
            mgr._build_image(mgr.config['base_image']['repo_unsquashed'],
                             mgr.config['base_image']['tags'],
                             mgr.config['base_image']['dockerfile_template_path'],
                             mgr.config['base_image']['build_args'],
                             mgr.config['base_image']['context_path'])

        mgr.config['base_image']['context_path'] = context_path
        mgr.config['base_image']['dockerfile_template_path'] = '/Dockerfile'
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, ' must be inside '):
            mgr._build_image(mgr.config['base_image']['repo_unsquashed'],
                             mgr.config['base_image']['tags'],
                             mgr.config['base_image']['dockerfile_template_path'],
                             mgr.config['base_image']['build_args'],
                             mgr.config['base_image']['context_path'])

    @unittest.skipUnless(whichcraft.which('systemctl'), 'Unable to stop Docker service')
    def test_build_base_image_connection_error(self):
        mgr = self.mgr

        # stop Docker service
        subprocess.check_call(['systemctl', 'stop', 'docker'])

        # check for error
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'Docker connection error:'):
            mgr.build_base_image()

        # restart Docker service
        subprocess.check_call(['systemctl', 'start', 'docker'])

    def test_build_base_image_api_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.config['base_image']['dockerfile_template_path'], 'w') as file:
            file.write('FROM2 ubuntu\n')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'Docker API error:'):
            mgr.build_base_image()

    def test_build_base_image_build_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with open(mgr.config['base_image']['dockerfile_template_path'], 'w') as file:
            file.write('FROM ubuntu\n')
            file.write('RUN exit 1')
            file.write('CMD bash\n')

        # check for error
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'Docker build error:'):
            mgr.build_base_image()

    def test_build_base_image_other_error(self):
        mgr = self.mgr

        # introduce typo into Dockerfile
        with mock.patch.object(docker.models.images.ImageCollection, 'build', side_effect=Exception('message')):
            with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'Exception:\n  message'):
                mgr.build_base_image()

    def test_remove_image(self):
        mgr = self.mgr

        image = mgr.build_base_image()
        for tag in mgr.config['base_image']['tags']:
            mgr._docker_client.images.get(mgr.config['base_image']['repo_unsquashed'] + ':' + tag)
            mgr._docker_client.images.get(mgr.config['base_image']['repo'] + ':' + tag)

        mgr.remove_image(mgr.config['base_image']['repo_unsquashed'], mgr.config['base_image']['tags'])
        mgr.remove_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])
        for tag in mgr.config['base_image']['tags']:
            with self.assertRaises(docker.errors.ImageNotFound):
                mgr._docker_client.images.get(mgr.config['base_image']['repo_unsquashed'] + ':' + tag)
            with self.assertRaises(docker.errors.ImageNotFound):
                mgr._docker_client.images.get(mgr.config['base_image']['repo'] + ':' + tag)

    def test_set_image(self):
        mgr = self.mgr
        mgr.build_base_image()
        image_unsquashed = mgr.get_latest_image(mgr.config['base_image']['repo_unsquashed'])
        image = mgr.get_latest_image(mgr.config['base_image']['repo'])

        mgr._base_image_unsquashed = None
        mgr._base_image = None
        mgr._image = None
        mgr.set_image(mgr.config['base_image']['repo_unsquashed'], image_unsquashed)
        mgr.set_image(mgr.config['base_image']['repo'], image)
        self.assertEqual(mgr._base_image_unsquashed, image_unsquashed)
        self.assertEqual(mgr._base_image, image)
        self.assertEqual(mgr._image, None)

        mgr._base_image_unsquashed = None
        mgr._base_image = None
        mgr._image = None
        mgr.set_image(mgr.config['base_image']['repo_unsquashed'], image.tags[0])
        mgr.set_image(mgr.config['base_image']['repo'], image.tags[0])
        self.assertEqual(mgr._base_image_unsquashed, image)
        self.assertEqual(mgr._base_image, image)
        self.assertEqual(mgr._image, None)

        mgr._base_image_unsquashed = None
        mgr._base_image = None
        mgr._image = None
        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['base_image']['repo_unsquashed'] = None
        mgr.config['base_image']['repo'] = None
        mgr.set_image(mgr.config['image']['repo'], image.tags[0])
        self.assertEqual(mgr._base_image_unsquashed, None)
        self.assertEqual(mgr._base_image, None)
        self.assertEqual(mgr._image, image)

    def test_get_latest_image(self):
        mgr = self.mgr
        mgr.build_base_image()
        image = mgr.get_latest_image(mgr.config['base_image']['repo'])
        self.assertIsInstance(image, docker.models.images.Image)

    def test_get_image_version(self):
        mgr = self.mgr
        mgr.build_base_image()
        version = mgr.get_image_version(mgr._base_image)
        self.assertRegex(version, r'^\d+\.\d+\.\d+[a-z0A-Z-9]*$')


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvManagerBuildRemoveImageTestCase(unittest.TestCase):
    def setUp(self):
        self.mgr = wc_env_manager.core.WcEnvManager()

    @unittest.skipUnless(os.path.isdir(os.path.expanduser(os.path.join('~', '.wc'))),
                         'config files package must be installed')
    def test_get_config_file_paths_to_copy_to_image(self):
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
        with open(os.path.join(temp_dir_name, 'pkg.cfg'), 'w') as file:
            pass
        paths = mgr.get_config_file_paths_to_copy_to_image()

        self.assertEqual(3, len(paths))
        self.assertIn({
            'host': os.path.join(temp_dir_name, 'pkg.cfg'),
            'image': '/root/.wc/pkg.cfg',
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

    def test_build_image(self):
        mgr = self.mgr
        mgr.config['verbose'] = True

        mgr.config['image']['tags'] = ['test']

        temp_dir_name = tempfile.mkdtemp()
        with open(os.path.join(temp_dir_name, 'a'), 'w') as file:
            file.write('ABC')
        with open(os.path.join(temp_dir_name, 'b'), 'w') as file:
            file.write('DEF')
        os.mkdir(os.path.join(temp_dir_name, 'c'))
        mgr.config['image']['paths_to_copy'] = {
            'a': {
                'host': os.path.join(temp_dir_name, 'a'),
                'image': '/tmp/a',
            },
            'b': {
                'host': os.path.join(temp_dir_name, 'b'),
                'image': '/tmp/b',
            },
            'c': {
                'host': os.path.join(temp_dir_name, 'c'),
                'image': '/tmp/c',
            },
        }

        mgr.config['image']['python_packages'] = '''
        git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1[all]
        git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1[all]
        '''

        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.build_image()
            text = capture_output.get_text()
            self.assertRegex(text, 'Successfully installed .*?wc-lang-')
            self.assertRegex(text, 'Successfully installed .*?wc-utils-')
            self.assertRegex(text, 'Successfully built')
        mgr.build_container()

        mgr.copy_path_from_container('/tmp/a',
                                     os.path.join(temp_dir_name, 'a2'))
        mgr.copy_path_from_container('/tmp/b',
                                     os.path.join(temp_dir_name, 'b2'))
        mgr.copy_path_from_container('/tmp/c',
                                     os.path.join(temp_dir_name, 'c'))
        with open(os.path.join(temp_dir_name, 'a2'), 'r') as file:
            self.assertEqual(file.read(), 'ABC')
        with open(os.path.join(temp_dir_name, 'b2'), 'r') as file:
            self.assertEqual(file.read(), 'DEF')
        self.assertTrue(os.path.isdir(os.path.join(temp_dir_name, 'c')))

        shutil.rmtree(temp_dir_name)
        mgr.stop_container()
        mgr.remove_containers()
        mgr.remove_image(mgr.config['image']['repo'], mgr.config['image']['tags'])


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvManagerDockerHubTestCase(unittest.TestCase):
    def setUp(self):
        mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.pull_image(mgr.config['base_image']['repo_unsquashed'], mgr.config['base_image']['tags'])
        mgr.pull_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])

    def test_login_docker_hub(self):
        mgr = self.mgr
        self.assertNotIn('docker.io', mgr._docker_client.api._auth_configs['auths'])
        mgr.login_docker_hub()  # test for no runtime error

    def test_push_image(self):
        mgr = self.mgr
        mgr.login_docker_hub()
        mgr.push_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])

    def test_push_image_error(self):
        mgr = self.mgr
        mgr.config['base_image']['repo'] = 'karrlab/does_not_exist'
        mgr.config['base_image']['tags'] = ['latest']
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'failed'):
            mgr.push_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])

    def test_pull_image(self):
        mgr = self.mgr
        image = mgr.pull_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])
        self.assertIsInstance(image, docker.models.images.Image)

        mgr.config['image']['repo'] = mgr.config['base_image']['repo']
        mgr.config['image']['tags'] = mgr.config['base_image']['tags']
        mgr.config['base_image']['repo'] = None
        mgr.config['base_image']['tags'] = None
        image = mgr.pull_image(mgr.config['image']['repo'], mgr.config['image']['tags'])
        self.assertIsInstance(image, docker.models.images.Image)


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvManagerNetworkTestCase(unittest.TestCase):
    def setUp(self):
        self.mgr = mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.config['network']['name'] = 'test_network__'
        mgr.config['network']['containers'] = {
            'test_db_container__': {
                'image': 'circleci/postgres:10.5-alpine-ram',
                'environment': {
                    'POSTGRES_USER': 'postgres',
                    'POSTGRES_DB': 'TestDatabase',
                },
            },
        }

        self.tearDown()

    def tearDown(self):
        mgr = self.mgr

        try:
            container = mgr._docker_client.containers.get('test_db_container__')
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            container = mgr._docker_client.containers.get('test_client_container__')
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            network = mgr._docker_client.networks.get('test_network__')
            network.remove()
        except docker.errors.NotFound:
            pass

    def test_build(self):
        mgr = self.mgr

        with self.assertRaises(docker.errors.NotFound):
            mgr._docker_client.networks.get('test_network__')
        with self.assertRaises(docker.errors.NotFound):
            mgr._docker_client.containers.get('test_db_container__')

        mgr.build_network()

        mgr._docker_client.networks.get('test_network__')
        db_container = mgr._docker_client.containers.get('test_db_container__')

        # connect to DB container from another container
        container = mgr._docker_client.containers.run('karrlab/wc_env_dependencies',
                                                      name='test_client_container__',
                                                      network='test_network__',
                                                      detach=True,
                                                      stdin_open=True, tty=True,
                                                      entrypoint=[], command="bash")
        connected = False
        for i in range(10):
            # try connecting until Postgres boots up
            result = container.exec_run("psql -h test_db_container__ -U postgres TestDatabase -c '\\l'")
            if result.exit_code == 0 and 'TestDatabase' in result.output.decode('utf-8')[0:-1]:
                connected = True
                break
            time.sleep(1.)
        self.assertTrue(connected)

    def test_remove(self):
        mgr = self.mgr

        mgr.build_network()
        mgr.remove_network()

        with self.assertRaises(docker.errors.NotFound):
            mgr._docker_client.networks.get('test_network__')
        with self.assertRaises(docker.errors.NotFound):
            mgr._docker_client.containers.get('test_db_container__')

        mgr.remove_network()


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvManagerContainerTestCase(unittest.TestCase):
    def setUp(self):
        mgr = self.mgr = wc_env_manager.core.WcEnvManager()
        mgr.pull_image(mgr.config['base_image']['repo'], mgr.config['base_image']['tags'])

        mgr.config['image']['tags'] = ['test']
        mgr.config['image']['python_packages'] = ''
        mgr.build_image()

        mgr.config['network']['name'] = '__test__'
        mgr.config['network']['containers'] = {}

    def tearDown(self):
        mgr = self.mgr
        mgr.remove_containers(force=True)
        mgr.remove_network()
        mgr.remove_image(mgr.config['image']['repo'], mgr.config['image']['tags'])

    def test_build_container(self):
        mgr = self.mgr

        temp_dir_name_a = tempfile.mkdtemp()
        temp_dir_name_b = tempfile.mkdtemp()

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
        container = mgr.build_container()
        self.assertIsInstance(container, docker.models.containers.Container)

        mgr.run_process_in_container('bash -c "echo abc >> /root/host/mount-a/test_a"')
        mgr.run_process_in_container('bash -c "echo 123 >> /root/host/mount-b/test_b"')

        with open(os.path.join(temp_dir_name_a, 'test_a'), 'r') as file:
            self.assertEqual(file.read(), 'abc\n')
        with open(os.path.join(temp_dir_name_b, 'test_b'), 'r') as file:
            self.assertEqual(file.read(), '123\n')

        shutil.rmtree(temp_dir_name_a)
        shutil.rmtree(temp_dir_name_b)

    def test_make_container_name(self):
        mgr = self.mgr
        mgr.config['container']['name_format'] = 'wc_env-%Y'
        self.assertEqual(mgr.make_container_name(), 'wc_env-{}'.format(datetime.datetime.now().year))

    def test_setup_container(self):
        mgr = self.mgr
        mgr.config['verbose'] = True

        temp_dir_name = tempfile.mkdtemp()
        git.Repo.clone_from('https://github.com/KarrLab/wc_utils.git',
                            os.path.join(temp_dir_name, 'wc_utils'))
        git.Repo.clone_from('https://github.com/KarrLab/wc_kb.git',
                            os.path.join(temp_dir_name, 'wc_kb'))
        mgr.config['container']['paths_to_mount'] = {
            temp_dir_name: {
                'bind': '/root/host/Documents',
                'mode': 'rw',
            }
        }

        mgr.config['container']['python_packages'] = '''
        /root/host/Documents/wc_utils
        -e /root/host/Documents/wc_kb
        '''

        mgr.build_container()
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_container()
            text = capture_output.get_text()
        self.assertRegex(text, r'Processing .*?wc_utils')
        self.assertRegex(text, r'Successfully installed .*?wc-utils-')

        mgr.run_process_in_container(['rm', '-r', '/root/host/Documents/wc_kb/wc_kb.egg-info'])
        shutil.rmtree(temp_dir_name)

    def test_setup_container_with_python_packages(self):
        mgr = self.mgr
        mgr.config['verbose'] = True
        container = mgr.build_container()

        # not upgrade
        mgr.config['container']['python_packages'] = 'pip'
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_container()
            self.assertRegex(capture_output.get_text(), 'Requirement already satisfied: pip')

        # upgrade, process dependency links
        mgr.config['container']['python_packages'] = 'pip'
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.setup_container(upgrade=True)
            self.assertRegex(capture_output.get_text(), '(Successfully installed|Requirement already up-to-date)')

    def test_setup_container_with_python_packages_error(self):
        mgr = self.mgr
        mgr.config['image']['python_packages'] = ''

        container = mgr.build_container()
        mgr.config['container']['python_packages'] = 'undefined_package'
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'No matching distribution'):
            mgr.setup_container()

    def test_setup_container_with_python_path(self):
        mgr = self.mgr
        mgr.config['image']['python_packages'] = ''
        mgr.config['container']['python_packages'] = ''
        mgr.config['container']['environment'] = {
            'PYTHONPATH': ':'.join([
                '/root/host/Documents/package_1',
                '/root/host/Documents/package_2'
            ]),
        }

        container = mgr.build_container()
        mgr.setup_container()
        output, _ = mgr.run_process_in_container(['bash', '-c', 'echo $PYTHONPATH'])
        self.assertEqual(output, (
            '/root/host/Documents/package_1:'
            '/root/host/Documents/package_2'
        ))

    def test_copy_path_to_from_docker_container(self):
        mgr = self.mgr
        mgr.build_container()

        temp_dir_name = tempfile.mkdtemp()
        temp_file_name = os.path.join(temp_dir_name, 'test.txt')
        with open(temp_file_name, 'w') as file:
            file.write('abc')

        mgr.copy_path_to_container(temp_file_name, '/tmp/test.txt')
        mgr.copy_path_to_container(temp_file_name, '/tmp/test.txt')  # overwrite
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'exists'):
            mgr.copy_path_to_container(temp_file_name, '/tmp/test.txt', overwrite=False)

        os.remove(temp_file_name)
        mgr.copy_path_from_container('/tmp/test.txt', temp_file_name)
        mgr.copy_path_from_container('/tmp/test.txt', temp_file_name)  # overwrite
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, 'exists'):
            mgr.copy_path_from_container('/tmp/test.txt', temp_file_name, overwrite=False)

        with open(temp_file_name, 'r') as file:
            self.assertEqual(file.read(), 'abc')

        shutil.rmtree(temp_dir_name)

    def test_set_container(self):
        mgr = self.mgr
        container = mgr.build_container()
        self.assertEqual(mgr._container, container)
        self.assertEqual(mgr.get_latest_container(), container)

        mgr._container = None
        mgr.set_container(container)
        self.assertEqual(mgr._container, container)

        mgr._container = None
        mgr.set_container(container.name)
        self.assertEqual(mgr._container, container)

    def test_get_latest_container(self):
        mgr = self.mgr
        container = mgr.build_container()
        self.assertEqual(mgr.get_latest_container(), container)

    def test_get_containers(self):
        mgr = self.mgr
        container = mgr.build_container()
        containers = mgr.get_containers()
        self.assertEqual(containers, [container])

    def test_run_process_in_container(self):
        mgr = self.mgr
        mgr.build_container()

        # not verbose
        mgr.config['verbose'] = False
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), '')

        # verbose
        mgr.config['verbose'] = True
        with capturer.CaptureOutput(relay=False) as capture_output:
            mgr.run_process_in_container(['echo', 'here'])
            self.assertEqual(capture_output.get_text(), 'here')

        # error
        mgr.config['verbose'] = False
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, '  exit code: 126'):
            mgr.run_process_in_container(['__undefined__'])

        # error, specified working directory
        mgr.config['verbose'] = False
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, '  working directory: /root'):
            mgr.run_process_in_container(['__undefined__'], work_dir='/root')

        # error, specified environment
        mgr.config['verbose'] = False
        with self.assertRaisesRegex(wc_env_manager.WcEnvManagerError, '    key: val'):
            mgr.run_process_in_container(['__undefined__'], env={'key': 'val'})

    def test_get_container_stats(self):
        mgr = self.mgr
        mgr.build_container()
        stats = mgr.get_container_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('cpu_stats', stats)
        self.assertIn('memory_stats', stats)

    def test_stop_container(self):
        mgr = self.mgr
        container = mgr.build_container()
        self.assertEqual(container.status, 'created')
        mgr.stop_container()
        self.assertEqual(container.status, 'created')

    def test_remove_container(self):
        mgr = self.mgr
        container = mgr.build_container()
        self.assertNotEqual(mgr._container, None)
        mgr.remove_container(force=True)
        self.assertEqual(mgr._container, None)
        self.assertEqual(mgr.get_containers(), [])

    def test_remove_containers(self):
        mgr = self.mgr
        container = mgr.build_container()
        self.assertNotEqual(mgr._container, None)
        mgr.remove_containers(force=True)
        self.assertEqual(mgr._container, None)
        self.assertEqual(mgr.get_containers(), [])


@unittest.skipIf(whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class WcEnvHostTestCase(unittest.TestCase):
    def setUp(self):
        self.mgr = wc_env_manager.core.WcEnvManager()

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


@unittest.skipIf(not RUN_LONG_TESTS or whichcraft.which('docker') is None, 'Test requires Docker and Docker isn''t installed.')
class FullWcEnvTestCase(unittest.TestCase):
    def setUp(self):
        self.mgr = mgr = wc_env_manager.core.WcEnvManager()

        config = mgr.config
        # config['image']['tags'] = ['test']
        # config['network']['name'] = '__test__'

    def tearDown(self):
        mgr = self.mgr
        config = mgr.config
        mgr.remove_containers(force=True)
        if 'test' in config['image']['tags']:
            mgr.remove_image(config['image']['repo'], config['image']['tags'])

    def test(self):
        mgr = self.mgr
        config = mgr.config
        config['verbose'] = True

        mgr.login_docker_hub()

        # build base image
        #mgr.pull_image(config['base_image']['repo_unsquashed'], config['base_image']['tags'])
        #mgr.pull_image(config['base_image']['repo'], config['base_image']['tags'])
        mgr.build_base_image()
        mgr.push_image(config['base_image']['repo_unsquashed'], config['base_image']['tags'])
        mgr.push_image(config['base_image']['repo'], config['base_image']['tags'])

        # build image
        #mgr.pull_image(config['image']['repo'], config['image']['tags'])
        mgr.build_image()
        mgr.push_image(config['image']['repo'], config['image']['tags'])

        # build container
        mgr.build_container()
        mgr.setup_container()

        with capturer.CaptureOutput(relay=True) as capture_output:
            mgr.run_process_in_container(['wc', '--help'])
            self.assertRegex(capture_output.get_text(), r'usage: wc \[\-h\]')


class ExampleTestCase(unittest.TestCase):
    def test(self):
        self.assertTrue(True)
        self.assertFalse(False)
