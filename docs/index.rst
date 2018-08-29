*wc_env_manager*: Tools for managing computing environments for whole-cell modeling
===================================================================================

*wc_env_manager* helps modelers and software developers setup customizable computing environments for developing, testing, and running whole-cell (WC) models and WC modeling software. This makes it easy for modelers and software developers to install and configure the numerous dependencies required for WC modeling. This helps modelers and software developers focus on developing WC models and software tools, rather than on installing, configuring, and maintaining complicated dependencies.

In addition, *wc_env_manager* facilitates collaboration by helping WC modelers and software developers share a common base computing environment with third party dependencies. Furthermore, *wc_env_manager* helps software developers anticipate and debug issues in deployment by enabling developers to replicate similar environments to those used to test and deploy WC models and tools in systems such as Amazon EC2, CircleCI, and Heroku.

*wc_env_manager* uses `Docker <https://www.docker.com>`_ to setup a customizable computing environment that contains all of the software packages needed to run WC models and WC modeling software. This includes

    * Required non-Python packages
    * Required Python packages from `PyPI <https://pypi.python.org/pypi>`_ and other sources
    * `WC models and WC modeling tools <https://github.com/KarrLab>`_
    * Optionally, local packages on the user's machine such as clones of these WC models and WC modeling tools

*wc_env_manager* supports both the development and deployment of WC models and WC modeling tools:

    * **Development:** *wc_env_manager* can run WC models and WC modeling software that is located on the user's machine. This is useful for testing WC models and WC modeling software before committing it to GitHub.
    * **Deployment:** *wc_env_manager* can run WC models and WC modeling software from external sources such as GitHub.

Contents
--------

.. toctree::
   :maxdepth: 3
   :numbered:

   installation.rst
   overview.rst
   tutorial.rst
   API documentation <source/modules.rst>
   about.rst