Tutorial for administrators of the *wc_env* and *wc_env_dependencies* images
============================================================================

Administrators should follow these steps to build and disseminate the *wc_env* and *wc_env_dependencies* images.

#. Create contexts for building the *wc_env* and *wc_env_dependencies* Docker images.
#. Create Dockerfile templates for the *wc_env* and *wc_env_dependencies* Docker images.
#. Set the configuration for *wc_env_manager*.
#. Use *wc_env_manager* to build the *wc_env* and *wc_env_dependencies* Docker images.
#. Use *wc_env_manager* to push the *wc_env* and *wc_env_dependencies* Docker images to DockerHub.


Create contexts for building the *wc_env* and *wc_env_dependencies* images
--------------------------------------------------------------------------

First, create contexts for building the images. This can include licenses and installers for proprietary software packages.

#. Prepare CPLEX installation
   
   a. Download CPLEX installer from `https://ibm.onthehub.com <https://ibm.onthehub.com>`_
   b. Save the installer to the base image context
   c. Set the execution bit for the installer by running `chmod ugo+x /path/to/installer`

#. Prepare Gurobi installation
   
   a. Create license at `http://www.gurobi.com/downloads/licenses/license-center <http://www.gurobi.com/downloads/licenses/license-center>`_
   b. Copy the license to the `gurobi_license` build argument for the base image in the *wc_env_manager* configuration

#. Prepare Mosek installation
   
   a. Request an academic license at `https://license.mosek.com/academic/ <https://license.mosek.com/academic/>`_
   b. Receive a license by email
   c. Save the license to the context for the base image as `mosek.lic`

#. Prepare XPRESS installation

   a. Install the XPRESS license server on another machine

      i. Download XPRESS from `https://clientarea.xpress.fico.com <https://clientarea.xpress.fico.com>`_
      ii. Use the `xphostid` utility to get your host id
      iii. Use the host id to create a floating license at `https://app.xpress.fico.com <https://app.xpress.fico.com>`_
      iv. Save the license file to the context for the base image as `xpauth.xpr`
      v. Run the installation program and follow the onscreen instructions

   b. Copy the IP address or hostname of the license server to the `xpress_license_server` build argument for the base image in the *wc_env_manager* configuration.
   c. Save the license file to the context for the base image as `xpauth.xpr`.
   d. Edit the server property in the first line of `xpauth.xpr` in the context for the base image. Set the property to the IP address or hostname of the license server.


Create Dockerfile templates for *wc_env* and *wc_env_dependencies*
------------------------------------------------------------------

Second, create templates for the Dockerfiles to be rendered by `Jinja <http://jinja.pocoo.org>`_, and save the Dockerfiles within the contexts for the images. The default templates illustrate how to create the Dockerfile templates.

* `/path/to/wc_env_manager/wc_env_manager/assets/base-image/Dockerfile.template`
* `/path/to/wc_env_manager/wc_env_manager/assets/image/Dockerfile.template`


Set the configuration for *wc_env_manager*
------------------------------------------

Third, Set the configuration for *wc_env_manager* by creating a configuration file `./wc_env_manager.cfg` following the schema outlined in `/path/to/wc_env_manager/wc_env_manager/config/core.schema.cfg` and the defaults in `/path/to/wc_env_manager/wc_env_manager/config/core.default.cfg`.

* Set the repository and tags for *wc_env* and *wc_env_dependencies*.
* Set the paths for the Dockerfile templates.
* Set the contexts for building the Docker images and the files that should be copied into the images.
* Set the build arguments for building the Docker images. This can include licenses for proprietary software packages.
* Set the WC modeling packages that should be installed into *wc_env*.
* Set your DockerHub username and password.


Build the *wc_env* and *wc_env_dependencies* Docker images
----------------------------------------------------------

Use the following command to build the *wc_env* and *wc_env_dependencies* images::

    wc_env_manager build


Push the *wc_env* and *wc_env_dependencies* Docker images to DockerHub
----------------------------------------------------------------------

Use the following command to push the *wc_env* and *wc_env_dependencies* images to GitHub::

    wc_env_manager push
