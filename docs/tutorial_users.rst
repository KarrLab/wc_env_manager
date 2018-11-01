Tutorial for users of WC models and WC modeling tools
=====================================================

Users of WC models and WC modeling tools should follow these steps to use *wc_env_manager* to use WC models and WC modeling tools

#. Use *wc_env_manager* to pull existing computing environments for WC modeling (Docker images)
#. Use *wc_env_manager* to create Docker containers for WC modeling
#. Run models and tools inside the Docker containers created by *wc_env_manager*


Pulling existing Docker images
------------------------------

First, use the following command to pull existing WC modeling Docker images. This will pull both the base image with third part dependencies, *wc_env_dependencies*, and the image with WC models and modeling tools, *wc_env*.::

  wc_env_manager pull

The following commands can also be used to pull the individual images.::

  wc_env_manager base-image pull
  wc_env_manager image pull


Building containers for WC modeling
-----------------------------------

Second, use the following command to use *wc_env* to construct a network of Docker containers.::

  wc_env_manager container build

This will print out the id of the WC container that was built. This is the main container that
you should use to run WC models and WC modeling tools.


Using containers to run WC models and WC modeling tools
-------------------------------------------------------

Third, use the following command to execute the container. This launches the container and runs an interactive *bash* shell inside the container.::

  docker exec --interactive --tty <container_id> bash

Fourth, use the integrated WC modeling command line program, `*wc* <https://github.com/KarrLab/wc>`_, to run WC models and WC modeling tools. For example, the following command illustrates how to get help for the *wc* program. See the `*wc* documentation <https://docs.karrlab.org/wc>`_ for more information.::

  container >> wc --help


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
    
    wc_env_manager container remove
