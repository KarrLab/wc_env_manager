Overview
========

`wc_env` provides an easy-to-use approach for running, developing and testing KarrLab whole cell (WC) software on your machine.
`wc_env` sets up a local computing environment that provides all software packages needed by the WC software.
It facilitates development of components of WC software because it can use your local KarrLab git repositories instead of the KarrLab repositories published on GitHub.
This enables you to use your customized WC software repos in the full WC software pipeline.

`wc_env` incorporates these types of software packages:

* Non-Python packages needed by WC software pipeline
* `PyPI <https://pypi.python.org/pypi>_` packages used by WC software pipeline
* Other Python package needed by WC software pipeline
* The WC software pipeline, cloned from the `KarrLab GitHub repo <https://github.com/KarrLab/>_`
* Optionally, your local, customized clones of some KarrLab GitHub repos
* Optionally, your other local software that you make available to `wc_env`

These last two are shared between your local computing environment and `wc_env`. See "How `wc_env` works"
below for more details.

-------------------------------------
Installing `wc_env`
-------------------------------------

`wc_env` only requires only four pieces of software on your computer: `Python`, `git`, the `cement` Python package, `Docker`, and `wc_env` itself. These lightweight requirements make `wc_env` very portable. Install them from these locations:

* `Python <https://www.python.org/downloads/>`_, version 3.5 or later
* `git <https://git-scm.com/downloads>`_
* `cement <http://cement.readthedocs.io/en/latest/dev/installation/>`_
* `Docker Community Edition <https://docs.docker.com/install/>_`
* `wc_env <https://github.com/KarrLab/wc_env>_`

-------------------------------------
Using `wc_env`
-------------------------------------

After installation, use `wc_env` by creating a wc environment, and then executing commands in the environment. `wc` is the primary application for using the environment. It supports multiple commands, which in turn have sub-commands, options and arguments:

* Run `wc create` to create a new wc environment. `wc -h` and `wc help create` provide more directions on using `create`.
* Run `wc reuse <name>` to reuse an existing environment called `<name>`. `wc help use` provides instructions for using `use`.

-------------------------------------
Rationale for  `wc_env`
-------------------------------------

`wc_env` emerged from the need to conveniently and easily deploy the WC software pipeline. Due to its size and complexity,
the pipeline uses many non-python, PyPI, and other Python components. As WC software pipeline grew it became
increasingly more difficult to install and maintain on any particular machine and operating system.
To solve this problem, we decided to create a highly portable wc environment that could be maintained by one or two
people and easily used by many beneficiaries.

-------------------------------------
How `wc_env` works
-------------------------------------

`wc_env` uses the Docker container system to create the environment, and to make the environment portable to the major operating systems that Docker supports, including Mac OSX, Linux and Windows.
`wc_env` has a layered architecture:

* At the top, shared file system links (`Docker volumes`) to a user's local customized clones of KarrLab GitHub repos and other software they make available to `wc_env`. The access to these packages is managed by changing the container's `PYTHONPATH` environment variable. This layer also include security credentials and other configuration data.
* The WC software pipeline, cloned from the `KarrLab GitHub repo <https://github.com/KarrLab/>_`. This layer and the next one are loaded into a `Docker container` created by `wc create`.
* Other Python package needed by WC software pipeline
* Python and the essential non-Python packages needed by the WC software pipeline. These bottom two layers are loaded into a `wc_env` Docker image.
* At the bottom, a Docker container running Ubuntu Linux

-------------------------------------
Precautions when using `wc_env`
-------------------------------------

Shared volumes


-------------------------------------
Other text
-------------------------------------

Since different parts of the WC software pipeline use different packages and repos, and some packages are only
required for certain functionality (optional requirements) the set of required software depends on the pipeline parts and
functionality being used.
