""" Configuration

:Author: Jonathan Karr <jonrkarr@gmail.com>
:Date: 2018-02-09
:Copyright: 2018, Karr Lab
:License: MIT
"""

import configobj
import os
import pathlib
import pkg_resources
import wc_utils.config


def get_config(extra=None):
    """ Get configuration

    Args:
        extra (:obj:`dict`, optional): additional configuration to override

    Returns:
        :obj:`configobj.ConfigObj`: nested dictionary with the configuration settings loaded from the configuration source(s).
    """
    paths = wc_utils.config.ConfigPaths(
        default=pkg_resources.resource_filename('wc_env_manager', 'config/core.default.cfg'),
        schema=pkg_resources.resource_filename('wc_env_manager', 'config/core.schema.cfg'),
        user=(
            'wc_env_manager.cfg',
            os.path.expanduser('~/.wc/wc_env_manager.cfg'),
        ),
    )

    context = {
        'HOME': str(pathlib.Path.home()),
    }

    return wc_utils.config.ConfigManager(paths).get_config(extra=extra, context=context)
