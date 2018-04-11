""" wc_env

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import os
from datetime import datetime
from pathlib import Path
import tempfile
import tarfile
import docker
import subprocess


class Error(Exception):
    """ Base class for exceptions in `wc_env`

    Attributes:
        message (:obj:`str`): the exception's message
    """
    def __init__(self, message=None):
        super().__init__(message)


class EnvError(Error):
    """ Exception raised for errors in `wc_env`

    Attributes:
        message (:obj:`str`): the exception's message
    """
    def __init__(self, message=None):
        super().__init__(message)


# :todo: replace with defaults in a config file
CONTAINER_DEFAULTS = dict(
    ssh_key='~/.ssh/id_rsa',
    configs_repo_username='karr-lab-daemon-public',
    git_config_file='assets/.gitconfig',
    bash_profile_file='assets/.bash_profile',
    python_version='3.6.4',
    docker_image_name='local_env',
    container_repo_dir='/usr/git_repos',
    configs_repo_pwd_file='tokens/configs_repo_password',
    karr_lab_repo_root='https://GitHub.com/KarrLab/',
    container_root_dir='/root/',
    container_local_repos='/usr/local_repos/',
    wc_env_container_name_prefix='wc_env',
)


class ManageImage(object):
    """ Manage a Docker image for `wc_env`

    Attributes:
        x (:obj:`str`): name of the Docker container being managed
    """

    def __init__(self, arg1):
        """
        Args:
            arg1 (:obj:`str`): name of the Docker container being managed
        """
        pass


class ManageContainer(object):
    """ Manage a Docker container for `wc_env`

    Attributes:
        local_wc_repos (:obj:`list` of `str`): directories of local KarrLab repos being modified
        image_version (:obj:`str`): version of the KarrLab Docker image at Docker Hub
        image_name (:obj:`str`): name of the KarrLab Docker image at Docker Hub
        python_version (:obj:`str`): Python version to use to set up the container
        container_repo_dir (:obj:`str`): pathname to dir containing mounted active repos
        configs_repo_username (:obj:`str`): username for the private repo `KarrLab/karr_lab_config`
        configs_repo_pwd_file (:obj:`str`): password for the private repo `KarrLab/karr_lab_config`
        ssh_key (:obj:`str`): the path to a private ssh key file that can access GitHub;
            it cannot be protected by a passphrase
        git_config_file (:obj:`str`): a .gitconfig file that indicates how to access GitHub
        verbose (:obj:`bool`): if True, produce verbose output
        docker_client (:obj:`docker.client.DockerClient`): client connected to the docker daemon
        container (:obj:`Container`): the Docker container being managed
        container_name (:obj:`str`): name of the Docker container being managed
    """

    def __init__(self,
        local_wc_repos,
        image_version,
        image_name=CONTAINER_DEFAULTS['docker_image_name'],
        python_version=CONTAINER_DEFAULTS['python_version'],
        container_repo_dir=CONTAINER_DEFAULTS['container_repo_dir'],
        configs_repo_username=CONTAINER_DEFAULTS['configs_repo_username'],
        configs_repo_pwd_file=CONTAINER_DEFAULTS['configs_repo_pwd_file'],
        ssh_key=CONTAINER_DEFAULTS['ssh_key'],
        git_config_file=CONTAINER_DEFAULTS['git_config_file'],
        verbose=False):
        """
        Args:
            local_wc_repos (:obj:`list` of `str`): directories of local KarrLab repos being modified
            image_version (:obj:`str`): version of the KarrLab Docker image at Docker Hub
            image_name (:obj:`str`, optional): name of the KarrLab Docker image at Docker Hub
            python_version (:obj:`str`, optional): Python version to use to set up the container
            container_repo_dir (:obj:`str`, optional): pathname to dir containing mounted active repos
            configs_repo_username (:obj:`str`): username for the private repo `KarrLab/karr_lab_config`
            configs_repo_pwd_file (:obj:`str`): password for the private repo `KarrLab/karr_lab_config`
            ssh_key (:obj:`str`): the path to a private ssh key file that can access GitHub;
                it cannot be protected by a passphrase
            git_config_file (:obj:`str`): a .gitconfig file that indicates how to access GitHub
            verbose (:obj:`bool`, optional): if True, produce verbose output

        Raises:
            :obj:`EnvError`: if any local_wc_repos are not readable directories
        """
        # resolve local_wc_repos as absolute paths
        self.local_wc_repos = []
        # todo: cannot have multiple repos with the same name
        errors = []
        for local_wc_repo_dir in local_wc_repos:
            path = os.path.abspath(os.path.expanduser(local_wc_repo_dir))
            if not(os.access(path, os.R_OK) and Path(path).is_dir()):
                errors.append(local_wc_repo_dir)
            self.local_wc_repos.append(path)
        if errors:
            raise EnvError("local WC repo dir(s) '{}' are not readable directories".format(', '.join(errors)))

        self.image_version = image_version
        self.image_name = image_name
        self.python_version = python_version
        self.container_repo_dir = container_repo_dir
        self.configs_repo_username = configs_repo_username
        self.configs_repo_pwd_file = configs_repo_pwd_file
        self.ssh_key = ssh_key
        self.git_config_file = git_config_file
        self.verbose = verbose
        # todo: use self.verbose and logging
        self.container = None
        self.container_name = None
        self.docker_client = docker.from_env()
        self.check_credentials()

    def check_credentials(self):
        """ Validate the credentials needed in a Docker container for `wc_env`

        Raises:
            :obj:`EnvError`: if the credentials are incomplete or incorrect
        """
        # determine which files exist
        credential_file_attrs = ['configs_repo_pwd_file', 'ssh_key', 'git_config_file']
        for attr in credential_file_attrs:
            file = getattr(self, attr)
            if file is None:
                continue
            path = os.path.abspath(os.path.expanduser(file))
            if Path(path).is_file():
                try:
                    open(path, 'r')
                    setattr(self, attr, path)
                except Exception:
                    setattr(self, attr, None)
            else:
                setattr(self, attr, None)

        # ensure that credentials are available
        if self.configs_repo_pwd_file is None and self.ssh_key is None:
            raise EnvError("No credentials available: either an ssh key or the password "
                "to KarrLab/karr_lab_config must be provided.")

        # todo: test credentials against GitHub and the config repo

    def create(self):
        """ create a Docker container for `wc_env`

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`docker.errors.APIError`: description of raised exceptions
        """
        # todo after image stored on Hub: pull the Docker wc_env image from Docker Hub
        # create a unique container name
        # todo: let user specify the container name
        self.container_name = "{}_{}".format(CONTAINER_DEFAULTS['wc_env_container_name_prefix'],
            datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
        # create the container that shares r/w access to local WC repos
        env_image = "karrlab/{}:{}".format(self.image_name, self.image_version)
        # mount wc repo directories in the container
        volumes_data = {}
        for local_wc_repo in self.local_wc_repos:
            local_wc_repo_basename = os.path.basename(local_wc_repo)
            container_wc_repo_dir = os.path.join(self.container_repo_dir, local_wc_repo_basename)
            volumes_data[local_wc_repo] = {'bind': container_wc_repo_dir, 'mode': 'rw'}

        try:
            self.container = self.docker_client.containers.run(env_image, command='bash',
                name=self.container_name,
                volumes=volumes_data,
                stdin_open=True,
                tty=True,
                detach=True)
        except Exception as e:
            raise EnvError("Error: cannot run container: {}".format(e))

        # load access credentials into the Docker container
        if self.ssh_key:
            self.cp(self.ssh_key, '/root/.ssh/id_rsa')
            self.cp(self.ssh_key+'.pub', '/root/.ssh/id_rsa.pub')
            exit_code, output = self.container.exec_run("bash ssh-keyscan github.com >> /root/.ssh/known_hosts".split())

        if self.git_config_file:
            # copy a .gitconfig file into the home directory of root in the container
            self.cp(self.git_config_file, '/root/.gitconfig')

        # use pip to install KarrLab pkg_utils and karr_lab_build_utils in the container
        # clone KarrLab GitHub repos into the container
        # create a PYTHONPATH for the container with local KarrLab repos ahead of cloned KarrLab repos
        # copy a custom .bash_profile file into the container
        # attach to the running container

    def run(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Run a Docker container for `wc_env`

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def use(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Use an existing Docker container for `wc_env`

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def stop(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Stop a running Docker container for `wc_env`

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def delete(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Delete a previously built Docker container for `wc_env`

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def report(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Report on the status of a `wc_env` Docker container

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def revise(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Revise a `wc_env` Docker container

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    def refresh(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Refresh a `wc_env` Docker container

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        # step 1
        # step 2
        pass

    # utility functions and methods
    def cp(self, path, dest_dir):
        """ Copy a file or directory into the `wc_env` Docker container

        Use the command `docker cp path dest_dir` to copy path.

        Unfortunately, the Docker API currently (2018-04-09) lacks a cp command
        (see https://github.com/docker/docker-py/issues/1771). Alternatively, one could write a method
        that takes a path, builds a temporary tar archive and calls put_archive() to put the archive
        in the container. Code from the Docker API could be reused for that approach.

        Args:
            path (:obj:`str`): the path of a file or directory to copy into the container
            dest_dir (:obj:`str`): the container's directory which will store the copied file or directory

        Raises:
            :obj:`EnvError`: if `path` does not exist or `container_name` has not been initialized
            :obj:`subprocess.CalledProcessError`: if 'docker cp' fails; see error conditions in the docker documentation
        """
        # check path and self.container_name
        if not Path(path).exists():
            raise EnvError("Error: path '{}' does not exist".format(path))
        if self.container_name is None or not self.container_name:
            raise EnvError('Error: container_name not initialized')
        command = ['docker', 'cp', path, '{}:{}'.format(self.container_name, dest_dir)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.stdout = result.stdout.decode('utf-8')
        result.stderr = result.stderr.decode('utf-8')
        result.check_returncode()


class ExampleClass(object):
    """ Descipton of ExampleClass

    Attributes:
        attr_1 (:obj:`type of attr_1`): description of attr_1
        attr_2 (:obj:`type of attr_2`): description of attr_2
        ...
    """

    def __init__(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """
        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            arg_2 (:obj:`type of arg_2`): description of arg_2
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            kwarg_2 (:obj:`type of kwarg_2`, optional): description of kwarg_2
            ...
        """
        self.attr_1 = arg_1
        self.attr_2 = arg_2

    def method_1(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Description of method_1

        Args:
            arg_1 (:obj:`type of arg_1`): description of arg_1
            arg_2 (:obj:`type of arg_2`): description of arg_2
            kwarg_1 (:obj:`type of kwarg_1`, optional): description of kwarg_1
            kwarg_2 (:obj:`type of kwarg_2`, optional): description of kwarg_2
            ...

        Returns:
            :obj:`type of return value`: description of return value

        Raises:
            :obj:`type of raised exception(s)`: description of raised exceptions
        """
        pass
