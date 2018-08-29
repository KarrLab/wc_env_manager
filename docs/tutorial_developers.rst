Tutorial for developers of WC models and WC modeling tools
==========================================================

Developers should follow these steps to build and use WC modeling computing environments (Docker images and containers) to test, debug, and run WC models and WC modeling tools.

#. Use *wc_env_manager* to pull existing WC modeling Docker images
#. Use *wc_env_manager* to create Docker containers with volumes mounted from the host and installations of software packages contained on the house
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

Second, set the configuration for the containers created by *wc_env_manager* by creating a configuration file `./wc_env_manager.cfg` following the schema outlined in `/path/to/wc_env_manager/wc_env_manager/config/core.schema.cfg` and the defaults in `/path/to/wc_env_manager/wc_env_manager/config/core.default.cfg`.

    * Set the host paths that should be mounted into the containers. This should include the root directory of your clones of WC models and WC modeling tools (e.g. map host:~/Documents to container:/root/Documents-Host).
    * Set the WC modeling packages that should be installed into *wc_env*. This should be specified in the pip requirements.txt format and should be specified in terms of paths within the container. The following example illustrates how install clones of *wc_lang* and *wc_utils* mounted from the host into the container.::

        /root/Documents-Host/wc_lang
        /root/Documents-Host/wc_utils

Third, use the following command to use *wc_env* to construct a Docker container.::

  wc_env_manager container build

This will print out the id of the created container.


Using containers to run WC models and WC modeling tools
-------------------------------------------------------

Fourth, use the following command to log in the container.::

  docker exec -it <container_id>

Fifth, use the integrated WC modeling command line program, `*wc* <https://github.com/KarrLab/wc>`_, to run WC models and WC modeling tools. For example, the following command illustrates how to get help for the *wc* program. See the `*wc* documentation <https://docs.karrlab.org/wc>`_ for more information.::

  container >> wc --help


Using WC modeling computing environments with an external IDE such as PyCharm
-----------------------------------------------------------------------------

The Docker images created with *wc_env_manager* can be used with external integrated development environments (IDEs) such as PyCharm. See the links below for instructions on how to use these tools with Docker images created with *wc_env_manager*.

* `Jupyter Notebook <https://jupyter-docker-stacks.readthedocs.io/>`_
* `PyCharm Professional Edition <https://www.jetbrains.com/help/pycharm/docker.html>`_
* Other IDEs:
    
    #. Install the IDE in a Docker image
    #. Use X11 forwarding to render graphical output from a Docker container to your host. See `Using GUI's with Docker <https://jupyter-docker-stacks.readthedocs.io>`_ for more information.
