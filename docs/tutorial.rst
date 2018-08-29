Tutorial
========

After installation, use `wc_env_manager` by creating a wc environment, and then executing commands in the environment. `wc` is the primary application for using the environment. It supports multiple commands, which in turn have sub-commands, options and arguments:

* Run `wc create` to create a new wc environment.
* Run `wc reuse <name>` to reuse an existing environment called `<name>`.
* Run `wc --help` to obtain help for `wc_env_manager`, including descriptions of the 
  arguments for each command.

.. _building_images:

Building WC modeling computing environments
-------------------------------------------

#. Prepare to install CPLEX
   a. Download CPLEX from https://ibm.onthehub.com
   b. Save to `tmp/cplex_studio12.7.1.linux-x86-64.bin`
   c. Set the execution bit `chmod ugo+x tmp/cplex_studio12.7.1.linux-x86-64.bin`
#. Prepare to install Gurobi
   a. Create license at http://www.gurobi.com/downloads/licenses/license-center
   b. Copy the license
   c. Save the license to `tokens/license_gurobi`
#. Prepare to install Mosek
   a. Request an academic license at https://license.mosek.com/academic/
   b. Recieve a license by email
   c. Save the license to `tokens/mosek.lic`
#. Prepare to install XPRESS
   a. Install the XPRESS license server on another machine
      i. Download XPRESS from https://clientarea.xpress.fico.com
      ii. Use the xphostid utility to get your host id
      iii. Use the host id to create a floating license at https://app.xpress.fico.com
      iv. Same the license file (`xpauth.xpr`)
      v. Run the installation program and follow the onscreen instructions
   b. Save the IP address or hostname of the license server to `tokens/xpress_license_server`
   c. Copy the same license file to `tokens/xpauth.xpr`
   d. Edit server property in the first line of `tokens/xpauth.xpr`. Set the property to the IP address
      or hostname of the license server
#. Run this script


Using *wc_env* with an external IDE such as PyCharm
---------------------------------------------------

The Docker images created with *wc_env_manager* can be used with external integrated development environments (IDEs) such as PyCharm. See the links below for instructions on how to use these tools with Docker images created with *wc_env_manager*.

* `Jupyter Notebook <https://jupyter-docker-stacks.readthedocs.io/>`_
* `PyCharm Professional Edition <https://www.jetbrains.com/help/pycharm/docker.html>`_
* Other IDEs:
    
    #. Install the IDE in a Docker image
    #. Use X11 forwarding to render graphical output from a Docker container to your host. See `Using GUI's with Docker <https://jupyter-docker-stacks.readthedocs.io>`_ for more information.