Tutorial for developers of WC models and WC modeling tools
==========================================================

Developers should follow these steps to build and use WC modeling computing environments (Docker images and containers) to test, debug, and run WC models and WC modeling tools.

#. Use *wc_env_manager* to pull existing WC modeling Docker images
#. Use *wc_env_manager* to create Docker containers with volumes mounted from the host and installations of software packages contained on the house
#. Run models and tools inside the Docker containers created by *wc_env_manager*


Pulling existing Docker images
------------------------------

First, use the following command to pull existing WC modeling Docker images. This will pull both the base image with third part dependencies, *wc_env_dependencies*, and the image with WC models and modeling tools, *wc_env*.::

  wc-env-manager pull

The following commands can also be used to pull the individual images.::

  wc-env-manager base-image pull
  wc-env-manager image pull


Building containers for WC modeling
-----------------------------------

Second, set the configuration for the containers created by *wc_env_manager* by creating a configuration file `./wc_env_manager.cfg` following the schema outlined in `/path/to/wc_env_manager/wc_env_manager/config/core.schema.cfg` and the defaults in `/path/to/wc_env_manager/wc_env_manager/config/core.default.cfg`.

    * Configure additional Docker containers that should be run and linked to the main container. For example, the configuration below will generate a second container based on the ``postgres:10.5-alpine`` image with the host name ``postgres_hostname`` on the ``wc_network`` Docker network and the environment variable ``POSTGRES_USER`` set to ``postgres_user``. The main Docker image will also be added to the same ``wc_network`` Docker network, which will make the second image accessible to the main image with the host name ``postgres_hostname``. In this example, it will then be possible to login to the Postgres service from the main container with the command ``psql -h postgres_hostname -U postgres_user <DB>``.

        [wc_env_manager]
            [[network]]
                name = wc_network
                [[[containers]]]
                    [[[[postgres_hostname]]]]
                        image = postgres:10.5-alpine
                        [[[[[environment]]]]]
                            POSTGRES_USER = postgres_user

    * Configure environment variables that should be set in the Docker container. The following example illustrates how to set the ``PYTHONPATH`` environment variable to the paths to *wc_lang* and *wc_sim*. Note, we recommend using *pip* to manipulate the Python path rather than directly manipulating the ``PYTHONPATH`` environment variable. We only recommend manipulating the ``PYTHONPATH`` environment variable for packages that don't have ``setup.py`` scripts or for packages that ``setup.py`` scripts that you temporarily don't want to run.::

        [wc_env_manager]
            [[container]]
                [[[environment]]]
                    PYTHONPATH = '/root/host/Documents/wc_lang:/root/host/Documents/wc_utils'

    * Configure the host paths that should be mounted into the containers. Typically, this should including mounting the parent directory of your Git repositories into the container. For example, this configuration will map (a) the Documents directory of your host (`${HOME}/Documents`) to the `/root/host/Documents` directory of the container and (b) your the WC modeling configuration directory of your host (`${HOME}/.wc`) to the WC modeling configuration directory of the container (`/root/.wc`). `${HOME}` will be substituted for the path to your home directory on your host.::

        [wc_env_manager]
            [[container]]
                [[[paths_to_mount]]]
                    [[[[${HOME}/Documents]]]]
                        bind = /root/host/Documents
                        mode = rw
                    [[[[${Home}/.wc]]]]
                        bind = /root/.wc
                        mode = rw

    * Configure the WC modeling packages that should be installed into *wc_env*. This should be specified in the *pip* requirements.txt format and should be specified in terms of paths within the container. The following example illustrates how to create editable installations of clones of *wc_lang* and *wc_utils* mounted from the host into the container.::

        [wc_env_manager]
            [[container]]
                python_package = '''
                    -e /root/host/Documents/wc_lang
                    -e /root/host/Documents/wc_utils
                    '''

    * Configure additional command(s) that should be run when the main Docker container is created. These commands will be run within a bash shell. For example, this configuration will restore the datanator database when the container is created.::

        [wc_env_manager]
            [[container]]
                setup_script = '''
                    if [ -x "$$(command -v datanator)" ]; then
                        datanator db create
                        datanator db migrate
                        datanator db restore --restore-schema --do-not-exit-on-error
                    fi
                    '''

    * Configure the ports that should be exposed by the container. The following example illustrates how to expose port 8888 as 8888.::

        [wc_env_manager]
            [[container]]
                [[[ports]]]
                    8888 = 8888

    * Configure all credentials required by the packages and tools used by the container. These should be installed in config (`*.cfg`) files that can be accessed by `wc-env-manager`. `~/.wc` is a standard location for whole-cell config files. Failure to install credentials will likely generate `Authentication error` exceptions.

Third, use the following command to use *wc_env* to construct a network of Docker containers.::

  wc-env-manager container build

This will print out the id of the WC container that was built. This is the main container that
you should use to run WC models and WC modeling tools.


Using containers to run WC models and WC modeling tools
-------------------------------------------------------

Fourth, use the following command to execute the container. This launches the container and runs an interactive *bash* shell inside the container.::

  docker exec --interactive --tty <container_id> bash

Fifth, use the integrated WC modeling command line program, `*wc_cli* <https://github.com/KarrLab/wc_cli>`_, to run WC models and WC modeling tools. For example, the following command illustrates how to get help for the *wc_cli* program. See the `*wc_cli* documentation <https://docs.karrlab.org/wc_cli>`_ for more information.::

  container >> wc-cli --help

Using containers to develop WC models and WC modeling tools
-----------------------------------------------------------

Sixth, use command line programs inside the container, such as *python*, *coverage* or *pytest*, to
run WC models and tools. Note, only mounted host paths will be accessible in the container.

Using WC modeling computing environments with an external IDE such as PyCharm
-----------------------------------------------------------------------------

The Docker images created with *wc_env_manager* can be used with external integrated development environments (IDEs) such as PyCharm. See the links below for instructions on how to use these tools with Docker images created with *wc_env_manager*.

* `Jupyter Notebook <https://jupyter-docker-stacks.readthedocs.io/>`_
* `PyCharm Professional Edition <https://www.jetbrains.com/help/pycharm/docker.html>`_
* Other IDEs:

    #. Install the IDE in a Docker image
    #. Use X11 forwarding to render graphical output from a Docker container to your host. See `Using GUI's with Docker <https://jupyter-docker-stacks.readthedocs.io>`_ for more information.

Exiting and removing containers
-------------------------------

Next, exit the container by executing *exit* or typing control-d. The container can be restarted using the following commands::

    docker restart <container_id>
    docker exec --interactive --tty <container_id> bash

Finally, remove the container by executing the following command::
    
    wc-env-manager container remove
