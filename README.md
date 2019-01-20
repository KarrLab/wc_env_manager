[![PyPI package](https://img.shields.io/pypi/v/wc_env_manager.svg)](https://pypi.python.org/pypi/wc_env_manager)
[![Documentation](https://img.shields.io/badge/docs-latest-green.svg)](https://docs.karrlab.org/wc_env_manager)
[![Test results](https://circleci.com/gh/KarrLab/wc_env_manager.svg?style=shield)](https://circleci.com/gh/KarrLab/wc_env_manager)
[![Test coverage](https://coveralls.io/repos/github/KarrLab/wc_env_manager/badge.svg)](https://coveralls.io/github/KarrLab/wc_env_manager)
[![Code analysis](https://api.codeclimate.com/v1/badges/aa64537fefad5a9d37b9/maintainability)](https://codeclimate.com/github/KarrLab/wc_env_manager)
[![License](https://img.shields.io/github/license/KarrLab/wc_env_manager.svg)](LICENSE)
![Analytics](https://ga-beacon.appspot.com/UA-86759801-1/wc_env_manager/README.md?pixel)

# *wc_env_manager*: Tools for managing computing environments for whole-cell modeling

*wc_env_manager* helps modelers and software developers setup customizable computing environments for developing, testing, and running whole-cell (WC) models and WC modeling software. This eliminates the need for each modeler and software developer to install and configure the numerous dependencies required for WC modeling. This helps modelers and software developers focus on developing WC models and software tools, rather than on installing and maintaining complicated dependencies.

In addition, *wc_env_manager* facilitates collaboration by helping WC modelers and software developers share a common computing environment. Furthermore, *wc_env_manager* helps software developers anticipate and debug issues in deployment by enabling developers to replicate the same environment used to test and deploy WC models and tools in systems such as Amazon EC2, CircleCI, and Heroku.

*wc_env_manager* uses [Docker](https://www.docker.com>) to setup customizable computing environments that contains all of the software packages needed to run WC models and WC modeling software. This includes

* Required non-Python packages
* Required Python packages from [PyPI](https://pypi.python.org/pypi>) and other sources
* [WC models and WC modeling tools](https://github.com/KarrLab)
* Optionally, local packages on the user's machine such as clones of these WC models and WC modeling tools

*wc_env_manager* supports two modes:

* **Development:** *wc_env_manager* can run WC models and WC modeling software that is located on the user's machine. This is useful for testing WC models and WC modeling software before committing it to GitHub.
* **Deployment:** *wc_env_manager* can run WC models and WC modeling software from external sources such as GitHub.

## Installation and usage
Please see the [documentation](http://docs.karrlab.org/wc_env_manager).

## Documentation
Please see the [API documentation](http://docs.karrlab.org/wc_env_manager).

## License
The package is released under the [MIT license](LICENSE).

## Development team
This package was developed by the [Karr Lab](http://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York, USA.

## Questions and comments
Please contact the [Karr Lab](http://www.karrlab.org) with any questions or comments.
