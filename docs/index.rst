`wc_env_manager`: Tools for managing computing environments for WC modeling
=========================================================================

`wc_env_manager` helps modelers and software developers setup computing environments for developing, testing, and running whole-cell (WC) models and WC modeling software. This eliminates the need for each modeler and software developer to install and configure the numerous dependencies required for WC modeling. This helps modelers and software developers focus on developing WC models and software tools rather than on installing and maintaining complicated dependencies.

In addition, `wc_env_manager` facilitates collaboration by helping WC modelers and software developers share a common computing environment. Furthermore, `wc_env_manager` helps helps software developers anticipate and debug issues in deployment by eanbling developers to replicate the same environment used to test and deploy WC models and tools in systems such as Amazon EC2, CircleCI, and Heroku.

`wc_env_manager` uses `Docker <https://www.docker.com>`_ to setup a local computing environment that contains all of the software packages needed to run WC models and WC modeling software. This includes

    * Required non-Python packages
    * Required Python packages from `PyPI <https://pypi.python.org/pypi>`_ and other sources
    * WC software packages from the `Karr Lab GitHub repository <https://github.com/KarrLab>`_
    * Optionally, local clones of these WC modeling software packages
    * Optionally, other local software

`wc_env_manager` supports two modes:

    * **Development:** `wc_env_manager` runs WC models and WC modeling software that is located on your machine. This is useful for testing WC models and WC modeling software before committing it to GitHub.
    * **Deployment:** `wc_env_manager` runs WC models and WC modeling software from GitHub.

Contents
--------

.. toctree::
   :maxdepth: 3
   :numbered:

   installation.rst
   overview.rst
   API documentation <source/modules.rst>
   about.rst