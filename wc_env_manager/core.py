""" Tools for managing computing environments for whole-cell modeling

* Build the Docker image
    
    * *wc_env*: image with WC models and WC modeling tools and their dependencies
    * *wc_env_dependencies*: base image with third party dependencies

* Remove the Docker images
* Push/pull the Docker images
* Create Docker containers

    1. Mount host directories into container
    2. Copy files (such as configuration files and authentication keys into container
    3. Install GitHub SSH key
    4. Verify access to GitHub
    5. Install Python packages in mounted directories from host

* Copy files to/from Docker container
* List Docker containers of the image
* Get CPU, memory, network usage statistics of Docker containers
* Stop Docker containers
* Remove Docker containers
* Login to DockerHub

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-08-23
:Copyright: 2018, Karr Lab
:License: MIT
"""

from datetime import datetime
import copy
import configobj
import dateutil.parser
import docker
import enum
import git
import glob
import jinja2
import os
import pkg_utils
import re
import requests
import requirements
import shutil
import subprocess
import tempfile
import time
import wc_env_manager.config.core
import yaml


class WcEnvUser(enum.Enum):
    """ WC environment users and their ids """
    root = 0
    container_user = 999


class WcEnvManager(object):
    """ Manage computing environments (Docker containers) for whole-cell modeling

    Attributes:
        config (:obj:`configobj.ConfigObj`): Dictionary of configuration options. See 
            `wc_env_manager/config/core.schema.cfg`.
        _docker_client (:obj:`docker.client.DockerClient`): client connected to the Docker daemon
        _base_image (:obj:`docker.models.images.Image`): current base Docker image
        _image (:obj:`docker.models.images.Image`): current Docker image
        _container (:obj:`docker.models.containers.Container`): current Docker container
    """

    # todo: update docs
    # todo: reduce privileges in Docker image by creating separate user; update docs
    # todo: manipulate Python path for packages without setup.py

    def __init__(self, config=None):
        """
        Args:
            config (:obj:`dict`, optional): Dictionary of configuration options. See 
            `wc_env_manager/config/core.schema.cfg`.
        """

        # get configuration
        self.config = config = wc_env_manager.config.core.get_config(extra={
            'wc_env_manager': config or {}})['wc_env_manager']

        # load Docker client
        self._docker_client = docker.from_env()

        # get image and current container
        self._base_image = None
        self._image = None
        self._container = None

        self.set_image(config['base_image']['repo'], self.get_latest_image(config['base_image']['repo']))
        self.set_image(config['image']['repo'], self.get_latest_image(config['image']['repo']))
        self.set_container(self.get_latest_container())

    def build_base_image(self):
        """ Build base Docker image for WC modeling environment

        Before executing this method, you must download CPLEX and obtain licenses for 
        Gurobi, MINOS, Mosek, and XPRESS. See the `documentation <building_images>` for more information.

        Returns:
            :obj:`docker.models.images.Image`: Docker image
        """
        config = self.config['base_image']

        # create temporary directory for build context
        temp_dir_name = tempfile.mkdtemp()
        shutil.rmtree(temp_dir_name)
        shutil.copytree(config['context_path'], temp_dir_name)

        # save list of Python package requirements to context path
        reqs = self.get_required_python_packages()
        with open(os.path.join(temp_dir_name, 'requirements.txt'), 'w') as file:
            file.write('\n'.join(reqs))

        # render Dockerfile
        template_dockerfile_name = config['dockerfile_template_path']
        with open(template_dockerfile_name) as file:
            template = jinja2.Template(file.read())

        dockerfile_path = os.path.join(temp_dir_name, 'Dockerfile')
        template.stream(**config['build_args']).dump(dockerfile_path)

        # build image
        image = self._build_image(config['repo'], config['tags'], dockerfile_path,
                                  config['build_args'], temp_dir_name,
                                  pull_base_image=True)

        # cleanup temporary directory
        shutil.rmtree(temp_dir_name)

        # return image
        return image

    def get_required_python_packages(self):
        """ Get Python packages required for the WC models and WC modeling
            tools (`config['image']['python_packages'])

        Returns:
            :obj:`list` of :obj:`str`: list of Python requirements in 
                requirements.txt format
        """
        # make temporary directory
        temp_dir_name = tempfile.mkdtemp()

        # save requirements for image to temp file and parse requirements
        _, dependency_links = pkg_utils.parse_requirement_lines(
            self.config['image']['python_packages'].split('\n'),
            include_extras=False, include_specs=False, include_markers=False)

        # collate requirements for packages
        reqs = set()
        for dependency_link in dependency_links:
            if dependency_link.startswith('git+https://'):
                url, _, egg = dependency_link[4:].partition('#')
                _, _, package_name = egg.partition('=')
                package_name, _, _ = package_name.partition('-')

                dir_name = os.path.join(temp_dir_name, package_name)
                max_tries = 5
                for i_try in range(max_tries):
                    try:
                        git.Repo.clone_from(url, dir_name)
                        break
                    except git.exc.GitCommandError as exception:  # pragma: no cover
                        if i_try == max_tries - 1:  # pragma: no cover
                            raise exception  # pragma: no cover
                        time.sleep(1.)

                def strip_github_packages(file_name):
                    if os.path.isfile(file_name):
                        with open(file_name, 'r') as file:
                            lines = file.readlines()
                        lines = filter(lambda line: 'git+https://' not in line, lines)
                        with open(file_name, 'w') as file:
                            file.writelines(lines)

                strip_github_packages(os.path.join(dir_name, 'requirements.txt'))
                strip_github_packages(os.path.join(dir_name, 'requirements.optional.txt'))
                strip_github_packages(os.path.join(dir_name, 'tests', 'requirements.txt'))
                strip_github_packages(os.path.join(dir_name, 'docs', 'requirements.txt'))

                install_requires, extras_require, _, _ = \
                    pkg_utils.get_dependencies(dir_name)
                reqs.update(set(install_requires))
                reqs.update(set(extras_require['all']))

        reqs_dict = {}
        for req in reqs:
            req_obj = requirements.parser.Requirement.parse_line(req)
            if req_obj.extras:
                raise WcEnvManagerError('Extras are not supported: {}'.format(req))
            if ';' in req:
                raise WcEnvManagerError('Specifiers are not supported: {}'.format(req))
            if req_obj.name not in reqs_dict:
                reqs_dict[req_obj.name] = set()
            if req_obj.specs:
                reqs_dict[req_obj.name].add(tuple(req_obj.specs))

        reqs = []
        for name, specs in reqs_dict.items():
            if len(specs) > 1:
                raise WcEnvManagerError('Conflicting specs for {}'.format(name))
            if specs:
                name += ' ' + ','.join(' '.join(spec) for spec in list(specs)[0])
            reqs.append(name)

        # remove temporary directory
        shutil.rmtree(temp_dir_name)

        # return requirements
        return sorted(reqs)

    def build_image(self):
        """ Build Docker image for WC modeling environment

        Returns:
            :obj:`docker.models.images.Image`: Docker image

        Raises:
            :obj:`WcEnvManagerError`: if a copied configuration file clashes with 
        """
        # create temporary directory for build context
        temp_dir_name = tempfile.mkdtemp()

        # add files to context and prepare for copy directives in Dockerfile
        paths_to_copy = \
            self.get_config_file_paths_to_copy_to_image() \
            + copy.deepcopy(self.config['image']['paths_to_copy'].values())

        for path in paths_to_copy:
            temp_path_host = os.path.join(temp_dir_name, os.path.abspath(path['host'])[1:])

            if not os.path.isdir(os.path.dirname(temp_path_host)):
                os.makedirs(os.path.dirname(temp_path_host))

            if os.path.isfile(path['host']):
                shutil.copyfile(path['host'], temp_path_host)
            else:
                shutil.copytree(path['host'], temp_path_host)
            path['host'] = os.path.abspath(path['host'])[1:]

        if self.config['image']['python_packages']:
            host_requirements_file_name = os.path.join(temp_dir_name, 'requirements.txt')
            if os.path.isfile(host_requirements_file_name):
                raise WcEnvManagerError('Copied files cannot have name `requirements.txt`')  # pragma: no cover
            paths_to_copy.append({
                'host': 'requirements.txt',
                'image': os.path.join('/tmp', 'requirements.txt'),
            })
            with open(host_requirements_file_name, 'w') as file:
                file.write(self.config['image']['python_packages'])

            image_requirements_file_name = os.path.join('/tmp', 'requirements.txt')
        else:
            image_requirements_file_name = None

        context = {
            'repo': self.config['base_image']['repo'],
            'tags': self.config['base_image']['tags'],
            'paths_to_copy': paths_to_copy,
            'python_version': self.config['image']['python_version'],
            'requirements_file_name': image_requirements_file_name,
        }

        # render Dockerfile
        template_dockerfile_name = self.config['image']['dockerfile_template_path']
        with open(template_dockerfile_name) as file:
            template = jinja2.Template(file.read())

        dockerfile_name = os.path.join(temp_dir_name, 'Dockerfile')
        template.stream(**context).dump(dockerfile_name)

        # build image
        config = self.config['image']
        image = self._build_image(config['repo'], config['tags'],
                                  dockerfile_name, {}, temp_dir_name)

        # cleanup temporary directory
        shutil.rmtree(temp_dir_name)

        # return image
        return image

    def _build_image(self, image_repo, image_tags,
                     dockerfile_path, build_args, context_path,
                     pull_base_image=False):
        """ Build Docker image

        Args:
            image_repo (:obj:`str`): image repository
            image_tags (:obj:`list` of :obj:`str`): list of tags
            dockerfile_path (:obj:`str`): path to Dockerfile            
            build_args (:obj:`dict`): build arguments for Dockerfile
            context_path (:obj:`str`): path to context for Dockerfile
            pull_base_image (:obj:`bool`, optional): if :obj:`True`, pull the 
                latest version of the base image

        Returns:
            :obj:`docker.models.images.Image`: Docker image

        Raises:
            :obj:`WcEnvManagerError`: if image context is not a directory, the image
                context doesn't contain the Dockerfile file, or there is an error building 
                the image
        """
        # build image
        if self.config['verbose']:
            print('Building image {} with tags {{{}}} ...'.format(
                image_repo, ', '.join(image_tags)))

        if not os.path.isdir(context_path):
            raise WcEnvManagerError('Docker image context "{}" must be a directory'.format(
                context_path))

        if os.path.dirname(dockerfile_path) != context_path:
            raise WcEnvManagerError('Dockerfile must be inside `context_path`')

        try:
            image, log = self._docker_client.images.build(
                path=context_path,
                dockerfile=os.path.basename(dockerfile_path),
                pull=pull_base_image,
                buildargs=build_args,
                rm=True,
            )
        except requests.exceptions.ConnectionError as exception:
            raise WcEnvManagerError("Docker connection error: service must be running:\n  {}".format(
                str(exception).replace('\n', '\n  ')))
        except docker.errors.APIError as exception:
            raise WcEnvManagerError("Docker API error: Dockerfile contains syntax errors:\n  {}".format(
                str(exception).replace('\n', '\n  ')))
        except docker.errors.BuildError as exception:
            raise WcEnvManagerError("Docker build error: Error building Dockerfile:\n  {}".format(
                str(exception).replace('\n', '\n  ')))
        except Exception as exception:
            raise WcEnvManagerError("{}:\n  {}".format(
                exception.__class__.__name__, str(exception).replace('\n', '\n  ')))

        # tag image
        for tag in image_tags:
            assert(image.tag(image_repo, tag=tag))

        # re-get image because tags don't automatically update on image object
        image.reload()

        # print log
        if self.config['verbose']:
            for entry in log:
                if 'stream' in entry:
                    print(entry['stream'], end='')
                elif 'id' in entry and 'status' in entry:
                    print('{}: {}'.format(entry['id'], entry['status']))
                else:
                    pass

        # store reference to latest image
        if image_repo == self.config['base_image']['repo'] and image_tags == self.config['base_image']['tags']:
            self._base_image = image
        elif image_repo == self.config['image']['repo'] and image_tags == self.config['image']['tags']:
            self._image = image

        return image

    def get_config_file_paths_to_copy_to_image(self):
        """ Get list of configuration file paths to copy from ~/.wc to Docker image 

        Returns:
            :obj:`list` of :obj:`dict`: configuration file paths to copy from ~/.wc to Docker image 
        """
        host_dirname = self.config['image']['config_path']
        image_dirname = os.path.join('/root', '.wc')

        paths_to_copy_to_image = []

        if os.path.isdir(host_dirname):
            # copy config files from host to image
            for path in glob.glob(os.path.join(host_dirname, '*.cfg')):
                paths_to_copy_to_image.append({
                    'host': path,
                    'image': os.path.join(image_dirname, os.path.basename(path)),
                })

            # copy third party config files to image
            filename = os.path.join(host_dirname, 'third_party', 'paths.yml')
            with open(filename, 'r') as file:
                paths = yaml.load(file)

            for rel_src, abs_dest in paths.items():
                abs_src = os.path.join(host_dirname, 'third_party', rel_src)
                if abs_dest[0:2] == '~/':
                    abs_dest = os.path.join('/root', abs_dest[2:])
                paths_to_copy_to_image.append({'host': abs_src, 'image': abs_dest})

        return paths_to_copy_to_image

    def remove_image(self, image_repo, image_tags, force=False):
        """ Remove version of Docker image

        Args:
            image_repo (:obj:`str`): image repository
            image_tags (:obj:`list` of :obj:`str`): list of tags
            force (:obj:`bool`, optional): if :obj:`True`, force removal of the version of the
                image (e.g. even if a container with the image is running)
        """
        for tag in image_tags:
            self._docker_client.images.remove('{}:{}'.format(image_repo, tag), force=True)

    def login_docker_hub(self):
        """ Login to DockerHub """
        config = self.config['docker_hub']
        self._docker_client.login(config['username'], password=config['password'])

    def push_image(self, image_repo, image_tags):
        """ Push Docker image to DockerHub 

        Args:
            image_repo (:obj:`str`): image repository
            image_tags (:obj:`list` of :obj:`str`): list of tags
        """
        for tag in image_tags:
            messages = self._docker_client.images.push(image_repo, tag, stream=True, decode=True)
            errors = []
            for message in messages:
                if 'error' in message:
                    errors.append(message['error'])
            if errors:
                raise WcEnvManagerError('Push {}:{} failed:\n  {}'.format(image_repo, tag, '\n  '.join(errors)))

    def pull_image(self, image_repo, image_tags):
        """ Pull Docker image for WC modeling environment

        Args:
            image_repo (:obj:`str`): image repository
            image_tags (:obj:`list` of :obj:`str`): list of tags

        Returns:
            :obj:`docker.models.images.Image`: Docker image
        """
        for tag in image_tags:
            image = self._docker_client.images.pull(image_repo, tag=tag)
        if image_repo == self.config['base_image']['repo'] and image_tags == self.config['base_image']['tags']:
            self._base_image = image
        elif image_repo == self.config['image']['repo'] and image_tags == self.config['image']['tags']:
            self._image = image
        return image

    def set_image(self, image_repo, image):
        """ Set the Docker image for WC modeling environment

        Args:
            image_repo (:obj:`str`): image repository
            image (:obj:`docker.models.images.Image` or :obj:`str`): Docker image
                or name of Docker image
        """
        if isinstance(image, str):
            image = self._docker_client.images.get(image)

        if image_repo == self.config['base_image']['repo']:
            self._base_image = image
        elif image_repo == self.config['image']['repo']:
            self._image = image

    def get_latest_image(self, image_repo):
        """ Get the lastest version of the Docker image for the WC modeling environment

        Args:
            image_repo (:obj:`str`): image repository

        Returns:
            :obj:`docker.models.images.Image`: Docker image
        """
        try:
            return self._docker_client.images.get(image_repo)
        except docker.errors.ImageNotFound:
            return None

    def get_image_version(self, image):
        """ Get the version of the Docker image

        Args:
            image (:obj:`docker.models.images.Image`): image

        Returns:
            :obj:`str`: docker image version
        """

        for tag in image.tags:
            _, _, version = tag.partition(':')
            if re.match(r'^\d+\.\d+\.\d+[a-zA-Z0-9]*$', version):
                return version

    def build_container(self, tty=True):
        """ Create Docker container for WC modeling environmet

        Args:
            tty (:obj:`bool`): if :obj:`True`, allocate a pseudo-TTY

        Returns:
            :obj:`docker.models.containers.Container`: Docker container
        """
        name = self.make_container_name()
        container = self._container = self._docker_client.containers.run(
            self.config['image']['repo'] + ':' + self.config['image']['tags'][0], name=name,
            volumes=self.config['container']['paths_to_mount'],
            stdin_open=True, tty=tty,
            detach=True,
            user=WcEnvUser.root.name)
        return container

    def make_container_name(self):
        """ Create a timestamped name for a Docker container

        Returns:
            :obj:`str`: container name
        """
        return datetime.now().strftime(self.config['container']['name_format'])

    def setup_container(self, upgrade=False, process_dependency_links=True):
        """ Install Python packages into Docker container

        Args:
            upgrade (:obj:`bool`, optional): if :obj:`True`, upgrade package
            process_dependency_links (:obj:`bool`, optional): if :obj:`True`, install packages from provided
                URLs
        """
        # save requirements to temporary file on host
        file, host_temp_filename = tempfile.mkstemp(suffix='.txt')
        os.write(file, self.config['container']['python_packages'].encode('utf-8'))
        os.close(file)

        # copy requirements to temporary file in container
        container_temp_filename, _ = self.run_process_in_container('mktemp', container_user=WcEnvUser.root)
        self.copy_path_to_container(host_temp_filename, container_temp_filename)

        # install requirements
        cmd = ['pip{}'.format(self.config['image']['python_version']), 'install', '-r', container_temp_filename]
        if upgrade:
            cmd.append('-U')
        if process_dependency_links:
            cmd.append('--process-dependency-links')
        self.run_process_in_container(cmd, container_user=WcEnvUser.root)

        # remove temporary files
        os.remove(host_temp_filename)
        self.run_process_in_container(['rm', container_temp_filename], container_user=WcEnvUser.root)

    def copy_path_to_container(self, local_path, container_path, overwrite=True, container_user=WcEnvUser.root):
        """ Copy file or directory to Docker container

        Implemented using subprocess because docker-py does not (as 2018-08-22)
        provide a copy method.

        Args:
            local_path (:obj:`str`): path to local file/directory to copy to container
            container_path (:obj:`str`): path to copy file/directory within container
            overwrite (:obj:`bool`, optional): if :obj:`True`, overwrite file

        Raises:
            :obj:`WcEnvManagerError`: if the container_path already exists and 
                :obj:`overwrite` is :obj:`False`
        """
        is_path, _ = self.run_process_in_container(
            'bash -c "if [ -f {0} ] || [ -d {0} ]; then echo 1; fi"'.format(container_path),
            container_user=container_user)
        if is_path and not overwrite:
            raise WcEnvManagerError('File {} already exists'.format(container_path))
        self.run_process_on_host([
            'docker', 'cp',
            local_path,
            self._container.name + ':' + container_path,
        ])

    def copy_path_from_container(self, container_path, local_path, overwrite=True):
        """ Copy file/directory from Docker container

        Implemented using subprocess because docker-py does not (as 2018-08-22)
        provide a copy method.

        Args:
            container_path (:obj:`str`): path to file/directory within container
            local_path (:obj:`str`): local path to copy file/directory from container
            overwrite (:obj:`bool`, optional): if :obj:`True`, overwrite file

        Raises:
            :obj:`WcEnvManagerError`: if the container_path already exists and 
                :obj:`overwrite` is :obj:`False`
        """
        is_file = os.path.isfile(local_path) or os.path.isdir(local_path)
        if is_file and not overwrite:
            raise WcEnvManagerError('File {} already exists'.format(local_path))
        self.run_process_on_host([
            'docker', 'cp',
            self._container.name + ':' + container_path,
            local_path,
        ])

    def set_container(self, container):
        """ Set the Docker containaer

        Args:
            container (:obj:`docker.models.containers.Container` or :obj:`str`): Docker container
                or name of Docker container
        """
        if isinstance(container, str):
            container = self._docker_client.containers.get(container)
        self._container = container

    def get_latest_container(self):
        """ Get current Docker container

        Returns:
            :obj:`docker.models.containers.Container`: Docker container
        """
        containers = self.get_containers(sort_by_read_time=True)
        if containers:
            return containers[0]
        else:
            return None

    def get_containers(self, sort_by_read_time=False):
        """ Get list of Docker containers that are WC modeling environments

        Args:
            sort_by_read_time (:obj:`bool`): if :obj:`True`, sort by read time in descending order
                (latest first)

        Returns:
            :obj:`list` of :obj:`docker.models.containers.Container`: list of Docker containers
                that are WC modeling environments
        """
        containers = []
        for container in self._docker_client.containers.list(all=True):
            try:
                datetime.strptime(container.name, self.config['container']['name_format'])
                containers.append(container)
            except ValueError:
                pass

        if sort_by_read_time:
            containers.sort(reverse=True, key=lambda container: dateutil.parser.parse(container.stats(stream=False)['read']))

        return containers

    def run_process_in_container(self, cmd, work_dir=None, env=None, check=True,
                                 container_user=WcEnvUser.root):
        """ Run a process in the current Docker container

        Args:
            cmd (:obj:`list` of :obj:`str` or :obj:`str`): command to run
            work_dir (:obj:`str`, optional): path to working directory within container
            env (:obj:`dict`, optional): key/value pairs of environment variables
            check (:obj:`bool`, optional): if :obj:`True`, raise exception if exit code is not 0
            container_user (:obj:`WcEnvUser`, optional): user to run commands in container

        Returns:
            :obj:`str`: output of the process

        Raises:
            :obj:`WcEnvManagerError`: if the command is not executed successfully
        """
        if not env:
            env = {}

        # execute command
        result = self._container.exec_run(
            cmd, workdir=work_dir, environment=env, user=container_user.name)

        # print output
        if self.config['verbose']:
            print(result.output.decode('utf-8')[0:-1])

        # check for errors
        if check and result.exit_code != 0:
            if not work_dir:
                result2 = self._container.exec_run('pwd', user=container_user.name)
                work_dir = result2.output.decode('utf-8')[0:-1]
            raise WcEnvManagerError(
                ('Command not successfully executed in Docker container:\n'
                 '  command: {}\n'
                 '  working directory: {}\n'
                 '  environment:\n    {}\n'
                 '  exit code: {}\n'
                 '  output: {}').format(
                    cmd, work_dir,
                    '\n    '.join('{}: {}'.format(key, val) for key, val in env.items()),
                    result.exit_code,
                    result.output.decode('utf-8')))

        return (result.output.decode('utf-8')[0:-1], result.exit_code)

    def get_container_stats(self):
        """ Get statistics about the CPU, io, memory, network performance of the Docker container

        Returns:
            :obj:`dict`: statistics about the CPU, io, memory, network performance of the Docker container
        """
        return self._container.stats(stream=False)

    def stop_container(self):
        """ Remove current Docker container """
        self._container.stop()

    def remove_container(self, force=False):
        """ Remove current Docker container

        Args:
            force (:obj:`bool`, optional): if :obj:`True`, force removal of the container
                (e.g. remove container even if it is running)
        """
        self._container.remove(force=force)
        self._container = None

    def remove_containers(self, force=False):
        """ Remove Docker all containers that are WC modeling environments

        Args:
            force (:obj:`bool`, optional): if :obj:`True`, force removal of the container
                (e.g. remove containers even if they are running)
        """
        for container in self.get_containers():
            container.remove(force=force)
        self._container = None

    def run_process_on_host(self, cmd):
        """ Run a process on the host

        Args:
            cmd (:obj:`list` of :obj:`str` or :obj:`str`): command to run
        """
        if self.config['verbose']:
            stdout = None
            stderr = None
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        subprocess.run(cmd, stdout=stdout, stderr=stderr, check=True)


class WcEnvManagerError(Exception):
    """ Base class for exceptions in `wc_env_manager`

    Attributes:
        message (:obj:`str`): the exception's message
    """

    def __init__(self, message=None):
        super().__init__(message)
