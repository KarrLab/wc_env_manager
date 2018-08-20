""" wc_env_manager

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-08-20
:Copyright: 2018, Karr Lab
:License: MIT
"""

from datetime import datetime
from pathlib import Path
import io
import docker
import os
import requests
import subprocess


class WcEnvManagerError(Exception):
    """ Base class for exceptions in `wc_env_manager`

    Attributes:
        message (:obj:`str`): the exception's message
    """

    def __init__(self, message=None):
        super().__init__(message)


# todo: ensure that pytest and pytest-cov are installed by pip
# todo: use logging
# todo: clarify terminology for cloned & local WC/KarrLab repos
# todo: use configs_repo_pwd_file if ssh_key not available
# todo: use a regular user, not /root/: see 'Use USER' section of http://www.projectatomic.io/docs/docker-image-author-guidance/
# todo: replace CONTAINER_DEFAULTS with defaults in a config file
# todo: handle git branching; allow specification of branches as well as repos
CONTAINER_DEFAULTS = dict(
    ssh_key='~/.ssh/id_rsa_github',     # an ssh key that accesses karr_lab_repo_root, and doesn't need a passphrase
    configs_repo_username='karr-lab-daemon-public',
    git_config_file='assets/.gitconfig',
    bash_profile_file='assets/.bash_profile',
    python2_version='2.7.14',
    python3_version='3.6.4',
    version_openbabel='2.4.1',
    docker_image_name='local_env',
    container_repo_dir='/usr/git_repos',
    configs_repo_pwd_file='tokens/configs_repo_password',
    karr_lab_repo_root='https://GitHub.com/KarrLab/',
    container_user_home_dir='/root/',
    container_local_repos='/usr/local_repos/',
    wc_env_container_name_prefix='wc_env_manager',
)


class WcEnvManager(object):
    """ Manage a Docker image and container for `wc_env_manager`

    Attributes:
        local_wc_repos (:obj:`list` of `str`): directories of local KarrLab repos being modified
        image_version (:obj:`str`): version of the KarrLab Docker image at Docker Hub
        image_name (:obj:`str`): name of the KarrLab Docker image at Docker Hub
        python3_version (:obj:`str`): Python version to use to set up the container
        container_repo_dir (:obj:`str`): pathname to dir containing mounted active repos
        container_user_home_dir (:obj:`str`): pathname to home dir of container user
        container_local_repos (:obj:`str`): pathname to dir in container with clones of KarrLab repos
        configs_repo_username (:obj:`str`): username for the private repo `KarrLab/karr_lab_config`
        configs_repo_pwd_file (:obj:`str`): password for the private repo `KarrLab/karr_lab_config`
        ssh_key (:obj:`str`): the path to a private ssh key file that can access GitHub;
            it cannot be protected by a passphrase
        git_config_file (:obj:`str`): a .gitconfig file that indicates how to access GitHub
        verbose (:obj:`bool`): if True, produce verbose output
        docker_client (:obj:`docker.client.DockerClient`): client connected to the docker daemon
        container (:obj:`docker.models.containers.Container`): the Docker container being managed
        volumes (:obj:`dict`): the specification of the volumes used by the Docker container being managed
        container_name (:obj:`str`): name of the Docker container being managed
    """

    def __init__(self,
                 local_wc_repos,
                 image_version,
                 image_name=CONTAINER_DEFAULTS['docker_image_name'],
                 python3_version=CONTAINER_DEFAULTS['python3_version'],
                 container_repo_dir=CONTAINER_DEFAULTS['container_repo_dir'],
                 container_user_home_dir=CONTAINER_DEFAULTS['container_user_home_dir'],
                 container_local_repos=CONTAINER_DEFAULTS['container_local_repos'],
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
            python3_version (:obj:`str`, optional): Python version to use to set up the container
            container_repo_dir (:obj:`str`, optional): pathname to dir containing mounted active repos
            container_user_home_dir (:obj:`str`, optional): pathname to home dir of container user
            container_local_repos (:obj:`str`, optional): pathname to dir in container with clones of KarrLab repos
            configs_repo_username (:obj:`str`): username for the private repo `KarrLab/karr_lab_config`
            configs_repo_pwd_file (:obj:`str`): password for the private repo `KarrLab/karr_lab_config`
            ssh_key (:obj:`str`): the path to a private ssh key file that can access GitHub;
                it cannot be protected by a passphrase
            git_config_file (:obj:`str`): a .gitconfig file that indicates how to access GitHub
            verbose (:obj:`bool`, optional): if True, produce verbose output

        Raises:
            :obj:`WcEnvManagerError`: if any local_wc_repos are not readable directories or are provided repeatedly
        """
        # resolve local_wc_repos as absolute paths
        self.local_wc_repos = []
        repo_names = set()
        errors = []
        for local_wc_repo_dir in local_wc_repos:
            path = os.path.abspath(os.path.expanduser(local_wc_repo_dir))
            # repo must be a readable directory
            if not(os.access(path, os.R_OK) and Path(path).is_dir()):
                errors.append("local WC repo dir '{}' is not a readable directory".format(path))
                continue
            # cannot have multiple repos with the same name
            repo_name = os.path.basename(path)
            if repo_name in repo_names:
                errors.append("repo '{}' appears multiple times in local_wc_repos".format(repo_name))
                continue
            repo_names.add(repo_name)
            self.local_wc_repos.append(path)
        if errors:
            raise WcEnvManagerError(', '.join(errors))

        self.image_version = image_version
        self.image_name = image_name
        self.python3_version = python3_version
        self.container_repo_dir = container_repo_dir
        self.container_user_home_dir = container_user_home_dir
        self.container_local_repos = container_local_repos
        self.configs_repo_username = configs_repo_username
        self.configs_repo_pwd_file = configs_repo_pwd_file
        self.ssh_key = ssh_key
        self.git_config_file = git_config_file
        self.verbose = verbose
        self.container = None
        self.container_name = None
        self.docker_client = docker.from_env()
        self.check_credentials()

    def check_credentials(self):
        """ Validate the credentials needed in a Docker container for `wc_env_manager`

        Raises:
            :obj:`WcEnvManagerError`: if the credentials are incomplete or incorrect
        """
        # set attribute to None for credential files that don't exist
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
            raise WcEnvManagerError("No credentials available: either an ssh key or the password "
                           "to KarrLab/karr_lab_config must be provided.")

        # todo: test credentials against GitHub and the config repo

    def build_command(self, path, fileobj, tag, buildargs):
        """ Prepare `docker build` command line that is equivalent to `WcEnv.build()`

        One of `path` and `fileobj` must be not `None`.

        Args:
            path (:obj:`str`): path to the directory containing the Dockerfile, or `None`
            fileobj (:obj:`io.BufferedReader`): file object to use as the Dockerfile, or `None`
            tag (:obj:`str`): file object to use as the Dockerfile, or `None`
            buildargs (:obj:`dict`): file object to use as the Dockerfile, or `None`

        Returns:
            :obj:`str`: a `docker build` command line equivalent to `WcEnv.build()`
        """
        cmd = ['docker', 'build', '--pull']
        if path is not None:
            cmd.append("--file {}".format(os.path.join(path, 'Dockerfile')))
        if fileobj is not None:
            cmd.append("--file {}".format(fileobj.name))
        for k, v in buildargs.items():
            cmd.append("--build-arg {}={}".format(k, v))
        # todo: figure out how to specify the context
        cmd.append(".")
        return ' '.join(cmd)

    def build(self, path=None, fileobj=None, push=False):
        """ Build a Docker image for `wc_env_manager`

        Args:
            path (:obj:`str`, optional): path to the directory containing the Dockerfile; default is
                the current working directory
            fileobj (:obj:`io.TextIOWrapper`, optional): file object to use as the Dockerfile
            push (:obj:`bool`, optional): if True, push the image that's built to Docker Hub; default is False

        Returns:
            :obj:`docker.models.images.Image`: the Docker image created

        Raises:
            :obj:`WcEnvManagerError`: if both `path` and `fileobj` are set
        """
        # compile requirements for the image
        if path is not None and fileobj is not None:
            raise WcEnvManagerError("path '{}' and fileobj '{}' cannot both be set".format(path, fileobj))
        if path is None and fileobj is None:
            path = os.getcwd()
        tag = 'karrlab/wc_env_manager:{}'.format(self.image_version)
        buildargs = dict(
            version_py2=CONTAINER_DEFAULTS['python2_version'],
            version_py3=CONTAINER_DEFAULTS['python3_version'],
            version_openbabel=CONTAINER_DEFAULTS['version_openbabel'],
        )
        if self.verbose:
            print('Docker build command:', self.build_command(path, fileobj, tag, buildargs))
        try:
            if self.verbose:
                print("Running: docker_client.build(path={}, tag={}, etc.)".format(path, tag))
            print("Building Docker image; this may take awhile ...")
            # build the image; setting pull obtains an updated FROM image
            image, logs = self.docker_client.images.build(path=path,
                                                          fileobj=fileobj,
                                                          tag=tag,
                                                          buildargs=buildargs,
                                                          pull=True)
        # todo: automate these tests
        except requests.exceptions.ConnectionError as e:    # pragma: no cover     # tested by hand
            raise WcEnvManagerError("ConnectionError: Docker cannot build image: ensure that Docker is running: {}".format(e))
        except docker.errors.BuildError as e:   # pragma: no cover     # tested by hand
            raise WcEnvManagerError("BuildError: Docker cannot build image: check the Internet connection and the Dockerfile: {}".format(e))
        except Exception as e:
            raise WcEnvManagerError("Error: cannot build image: {}".format(e))
        self.image = image
        if self.verbose:
            for entry in logs:
                if 'stream' in entry:
                    print(entry['stream'], end='')
                elif 'id' in entry and 'status' in entry:
                    print('{}: {}'.format(entry['id'], entry['status']))
        # todo: test the image
        # optionally, push to Docker Hub
        return image

    def make_container_name(self):
        """ Create a timestamped name for a `wc_env_manager` Docker container

        Returns:
            :obj:`str`: the container name
        """
        return "{}_{}".format(CONTAINER_DEFAULTS['wc_env_container_name_prefix'],
                              datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))

    def create(self, name=None):
        """ Create a Docker container for `wc_env_manager`

        Args:
            name (:obj:`str`, optional): the container's name; default provided by ``

        Returns:
            :obj:`docker.models.containers.Container`: the container created `make_container_name()`

        Raises:
            :obj:`docker.errors.APIError`: description of raised exceptions
        """
        # todo: after image stored on Hub: pull the Docker wc_env_manager image from Docker Hub
        self.container_name = name
        if name is None:
            self.container_name = self.make_container_name()

        # create the container that shares r/w access to local WC repos
        env_image = "karrlab/{}:{}".format(self.image_name, self.image_version)

        # todo: use pp_to_karr_lab_repos
        # mount wc repo directories in the container
        self.volumes = {}
        for local_wc_repo in self.local_wc_repos:
            local_wc_repo_basename = os.path.basename(local_wc_repo)
            container_wc_repo_dir = os.path.join(self.container_repo_dir, local_wc_repo_basename)
            self.volumes[local_wc_repo] = {'bind': container_wc_repo_dir, 'mode': 'rw'}

        try:
            if self.verbose:
                print("Running: containers.run({}, name='{}', etc.)".format(env_image, self.container_name))
            self.container = self.docker_client.containers.run(env_image, command='bash',
                                                               name=self.container_name,
                                                               volumes=self.volumes,
                                                               stdin_open=True,
                                                               tty=True,
                                                               detach=True)
        except requests.exceptions.ConnectionError as e:    # pragma: no cover     # tested by hand
            raise WcEnvManagerError("ConnectionError: Docker cannot run container: ensure that Docker is running: {}".format(e))
        except Exception as e:
            raise WcEnvManagerError("Error: cannot run container: {}".format(e))

        # load access credentials into the Docker container
        if self.ssh_key:
            self.cp(self.ssh_key, os.path.join(self.container_user_home_dir, '.ssh/id_rsa'))
            self.cp(self.ssh_key+'.pub', os.path.join(self.container_user_home_dir, '.ssh/id_rsa.pub'))
            cmd = "ssh-keyscan github.com >> {}".format(os.path.join(self.container_user_home_dir, '.ssh/known_hosts'))
            self.exec_run(cmd)

        if self.git_config_file:
            # copy a .gitconfig file into the home directory of root in the container
            self.cp(self.git_config_file, os.path.join(self.container_user_home_dir, '.gitconfig'))
        return self.container

    def load_karr_lab_tools(self):
        """ Use pip to install KarrLab pkg_utils and karr_lab_build_utils in the container

        Raises:
            :obj:`WcEnvManagerError`: if pip commands fail
        """
        major, minor, _ = self.python3_version.split('.')
        python_version_major_minor = "{}.{}".format(major, minor)
        print('pip install pkg_utils --')
        cmd = "pip{} install -U --process-dependency-links "\
            "git+https://github.com/KarrLab/pkg_utils.git#egg=pkg_utils".format(python_version_major_minor)
        self.exec_run(cmd)

        print('pip install karr_lab_build_utils --')
        cmd = "pip{} install -U --process-dependency-links "\
            "git+https://github.com/KarrLab/karr_lab_build_utils.git#egg=karr_lab_build_utils".format(
                python_version_major_minor)
        self.exec_run(cmd)

    def clone_karr_lab_repos(self):
        """ Use git to clone KarrLab GitHub repos into the container

        Raises:
            :obj:`WcEnvManagerError`: if mkdir or git commands fail
        """
        self.exec_run("mkdir {}".format(self.container_local_repos))
        for wc_repo in WcEnv.all_wc_repos():
            cmd = "git clone https://github.com/KarrLab/{}.git".format(wc_repo)
            self.exec_run(cmd, workdir=self.container_local_repos)

    def pp_to_karr_lab_repos(self):
        """ Create bash command to append KarrLab repos to `PYTHONPATH` in container

        Local KarrLab repos mounted on volumes come ahead of cloned KarrLab repos.

        Returns:
            :obj:`str`: `PYTHONPATH` export command
        """
        pythonpath = []
        # paths for mounted local wc_repos
        for local_wc_repo in self.local_wc_repos:
            local_wc_repo_basename = os.path.basename(local_wc_repo)
            pythonpath.append(os.path.join(self.container_repo_dir, local_wc_repo_basename))

        # paths for repos cloned into container
        for wc_repo in WcEnv.all_wc_repos():
            pythonpath.append(os.path.join(self.container_local_repos, wc_repo))

        rv = 'export PYTHONPATH="$PYTHONPATH:{}"'.format(':'.join(pythonpath))
        return rv

    def run(self):
        """ Run a Docker container for `wc_env_manager`

        Returns:
            :obj:`docker.models.containers.Container`: the running container
        """
        container = self.create()
        self.load_karr_lab_tools()
        self.clone_karr_lab_repos()
        # todo: copy a custom .bash_profile file into the container
        return container

    def use(self, arg_1, arg_2, kwarg_1=None, kwarg_2=None):
        """ Use an existing Docker container for `wc_env_manager`

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
        """ Stop a running Docker container for `wc_env_manager`

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
        """ Delete a previously built Docker container for `wc_env_manager`

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
        """ Report on the status of a `wc_env_manager` Docker container

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
        """ Refresh a `wc_env_manager` Docker container

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
        """ Copy a file or directory into the `wc_env_manager` Docker container

        Use the command `docker cp path dest_dir` to copy path.

        Unfortunately, the Docker API currently (2018-04-09) lacks a cp command
        (see https://github.com/docker/docker-py/issues/1771). Alternatively, one could write a method
        that takes a path, builds a temporary tar archive and calls put_archive() to put the archive
        in the container. Code from the Docker API could be reused for that approach.

        Args:
            path (:obj:`str`): the path of a file or directory to copy into the container
            dest_dir (:obj:`str`): the container's directory which will store the copied file or directory

        Raises:
            :obj:`WcEnvManagerError`: if `path` does not exist or `container_name` has not been initialized
            :obj:`subprocess.CalledProcessError`: if 'docker cp' fails; see error conditions in the docker documentation
        """
        # check path and self.container_name
        if not Path(path).exists():
            raise WcEnvManagerError("Error: path '{}' does not exist".format(path))
        if self.container_name is None or not self.container_name:
            raise WcEnvManagerError('Error: container_name not initialized')
        command = ['docker', 'cp', path, '{}:{}'.format(self.container_name, dest_dir)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.stdout = result.stdout.decode('utf-8')
        result.stderr = result.stderr.decode('utf-8')
        result.check_returncode()

    def exec_run(self, command, **kwargs):
        """ Run exec_run on a container

        Args:
            command (:obj:`str`): the command to have `exec_run` run
            kwargs (:obj:`dict`): keyword arguments for `exec_run`

        Returns:
            :obj:`str`: output of `exec_run`

        Raises:
            :obj:`WcEnvManagerError`: if `self.container.exec_run` fails
        """
        kws = ', '.join(['{}={}'.format(k, v) for k, v in kwargs.items()])
        if kws:
            kws = ', ' + kws
        if self.verbose:
            print("Running: container.exec_run({}{})".format(command, kws))
        exit_code, output = self.container.exec_run(command.split(), **kwargs)
        if exit_code != 0:
            raise WcEnvManagerError("{}:\nself.container.exec_run({}{}) receives exit_code {}".format(__file__,
                                                                                             command, kws, exit_code))
        return output.decode('utf-8')

    @staticmethod
    def all_wc_repos():
        """ Get all WC repos

        Returns:
            :obj:`list` of `str`: list of names of all WC repos
        """
        # :todo: get these repos programatically
        ALL_WC_REPOS = 'wc_lang wc_sim wc_utils obj_model wc_kb kinetic_datanator wc_rules'
        return ALL_WC_REPOS.split()
