Tutorial
========

After installation, use `wc_env_manager` by creating a wc environment, and then executing commands in the environment. `wc` is the primary application for using the environment. It supports multiple commands, which in turn have sub-commands, options and arguments:

* Run `wc create` to create a new wc environment.
* Run `wc reuse <name>` to reuse an existing environment called `<name>`.
* Run `wc --help` to obtain help for `wc_env_manager`, including descriptions of the 
  arguments for each command.


Using *wc_env* with an external IDE such as PyCharm
---------------------------------------------------

The Docker images created with *wc_env_manager* can be used with external integrated development environments (IDEs) such as PyCharm. See the links below for instructions on how to use these tools with Docker images created with *wc_env_manager*.

* `Jupyter Notebook <https://jupyter-docker-stacks.readthedocs.io/>`_
* `PyCharm Professional Edition <https://www.jetbrains.com/help/pycharm/docker.html>`_
* Other IDEs:
    
    #. Install the IDE in a Docker image
    #. Use X11 forwarding to render graphical output from a Docker container to your host. See `Using GUI's with Docker <https://jupyter-docker-stacks.readthedocs.io>`_ for more information.