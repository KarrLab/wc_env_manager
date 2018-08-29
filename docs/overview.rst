Overview
========


Features
-------------------------------------
*wc_env_manager* provides a high-level interface for the following modeling tasks

* Build WC modeling computing environments (Docker images and containers)

    1. Copy files (such as configuration files and authentication keys) into image
    2. Install GitHub SSH key into image
    3. Install WC models and WC modeling tools from GitHub into image
    4. Mount host directories (e.g. with clones of WC models and WC modeling tools) into container
    5. Install Python packages in mounted directories (e.g. clones of WC models and WC modeling tools) from host

* Copy files to/from containers
* List containers of the images
* Get CPU, memory, network usage statistics of containers
* Login to DockerHub
* Push and pull images to/from DockerHub
* Remove images and containers


How *wc_env_manager* works
-------------------------------------

*wc_env_manager* is based on Docker images and containers which enable virtual environments within all major operating systems including Linux, Mac OSX, and Windows, and the DockerHub repository for versioning and sharing virtual environments.

1. *wc_env_manager* creates a Docker image, *wc_env_dependencies* with the third-party dependencies needed for WC modeling or pulls this image from DockerHub. This image represents an Ubuntu Linux machine.
2. *wc_env_manager* uses this Docker image to create another Docker image, *wc_env* with the WC models, WC modeling tools, and the configuration files and authentication keys needed for WC modeling.
3. *wc_env_manager* uses this image to create a Docker container to run WC models and WC modeling tools. Optionally, the container can have volumes mounted from the host to run code on the host inside the Docker container, which is helpful for using the container to test and debug WC models and tools.

The images and containers created by *wc_env_manager* can be customized using a configuration file.


Caveats and troubleshooting
-------------------------------------

* Code run in containers created by *wc_env_manager* can create host files and overwrite existing host files. This is because *wc_env_manager* mounts host directories into containers.
* Containers created by *wc_env_manager* can be used to run code located on your host machine. However, using different versions of Python between your host and the Docker containers can create Python caches and compiled Python files that are incompatible between your host and the Docker containers. Before switching between running code on your host your and the Docker containers, you may need to remove all ``__pycache__`` subdirectories and ``*.pyc`` files from host packages mounted into the containers.
* Code run in Docker containers will not have access to the absolute paths of your host and vice-versa. Consequently, arguments that represent absolute host paths or which contain absolute host paths must be mapped from absolute host paths to the equivalent container path. Similarly, outputs which represent or contain absolute container paths must be mapped to the equivalent host paths.
* Running code in containers created with *wc_env_manager* will be slower than running the same code on your host. This is because *wc_env_manager* is based on Docker containers, which add an additional layer of abstraction between your code and your processor.
