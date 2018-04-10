import pkg_resources

# read version
with open(pkg_resources.resource_filename('wc_env', 'VERSION'), 'r') as file:
    __version__ = file.read().strip()

# API
from .core import (EnvError, ManageContainer)
