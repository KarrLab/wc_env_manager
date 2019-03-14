""" wc_env_manager command line interface

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-04-04
:Copyright: 2018, Karr Lab
:License: MIT
"""

import cement
import wc_env_manager
import wc_env_manager.core

VERBOSE = True


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "Whole-cell modeling environment manager"
        arguments = [
            (['-v', '--version'], dict(action='version', version=wc_env_manager.__version__)),
        ]

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()


class BaseImageController(cement.Controller):
    """ Build, push, and pull the base image, *wc_env_dependencies* """

    class Meta:
        label = 'base-image'
        description = 'Build, push, pull, and remove the base image, `wc_env_dependencies`'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = []

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()

    @cement.ex(help='Build base image')
    def build(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.build_base_image()
        print('Built base image {}:{{{}}}'.format(
            mgr.config['base_image']['repo'], ', '.join(mgr.config['base_image']['tags'])))

    @cement.ex(help='Push base image')
    def push(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['base_image']
        mgr.login_docker_hub()
        mgr.push_image(config['repo_unsquashed'], config['tags'])
        mgr.push_image(config['repo'], config['tags'])

    @cement.ex(help='Pull base image')
    def pull(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['base_image']
        mgr.pull_image(config['repo_unsquashed'], config['tags'])
        mgr.pull_image(config['repo'], config['tags'])

    @cement.ex(help='Remove base image')
    def remove(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['base_image']
        mgr.remove_image(config['repo_unsquashed'], config['tags'], force=True)
        mgr.remove_image(config['repo'], config['tags'], force=True)

    @cement.ex(help='Get base image version')
    def version(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        print(mgr.get_image_version(mgr._base_image))


class ImageController(cement.Controller):
    """ Build, push, and pull the image, *wc_env* """

    class Meta:
        label = 'image'
        description = 'Build, push, pull, and remove the image, `wc_env`'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = []

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()

    @cement.ex(help='Build image')
    def build(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.build_image()
        print('Built image {}:{{{}}}'.format(
            mgr.config['image']['repo'], ', '.join(mgr.config['image']['tags'])))

    @cement.ex(help='Push image')
    def push(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['image']
        mgr.login_docker_hub()
        mgr.push_image(config['repo'], config['tags'])

    @cement.ex(help='Pull image')
    def pull(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['image']
        mgr.pull_image(config['repo'], config['tags'])

    @cement.ex(help='Remove image')
    def remove(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        config = mgr.config['image']
        mgr.remove_image(config['repo'], config['tags'], force=True)

    @cement.ex(help='Get image version')
    def version(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        print(mgr.get_image_version(mgr._image))


class NetworkController(cement.Controller):
    """ Build and remove a Docker network """

    class Meta:
        label = 'network'
        description = 'Build and remove a Docker network'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = []

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()

    @cement.ex(help='Build network')
    def build(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.build_network()

    @cement.ex(help='Remove network')
    def remove(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.remove_network()


class ContainerController(cement.Controller):
    """ Build and remove containers of *wc_env* """

    class Meta:
        label = 'container'
        description = 'Build and remove containers of `wc_env`'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
        ]

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()

    @cement.ex(help='Build container')
    def build(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.build_container()
        mgr.setup_container()
        print('Built container {}'.format(mgr._container.name))

    @cement.ex(help='Remove container')
    def remove(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.remove_containers(force=True)


class AllController(cement.Controller):
    """ Build, push, pull, and remove images and containers """

    class Meta:
        label = 'all'
        description = 'Build, push, pull, and remove images and containers'
        stacked_on = 'base'
        stacked_type = 'embedded'
        arguments = [
        ]

    # @cement.ex(hide=True)
    # def _default(self):
    #   self._parser.print_help()

    @cement.ex(help='Build base image, image, and container')
    def build(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.remove_containers()
        mgr.build_base_image()
        mgr.build_image()
        mgr.build_container()

        print('Built base image {}:{{{}}}'.format(
            mgr.config['base_image']['repo'], ', '.join(mgr.config['base_image']['tags'])))
        print('Built image {}:{{{}}}'.format(
            mgr.config['image']['repo'], ', '.join(mgr.config['image']['tags'])))
        print('Built container {}'.format(mgr._container.name))

    @cement.ex(help='Push base image and image')
    def push(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})
        mgr.login_docker_hub()

        config = mgr.config['base_image']
        mgr.push_image(config['repo_unsquashed'], config['tags'])

        config = mgr.config['base_image']
        mgr.push_image(config['repo'], config['tags'])

        config = mgr.config['image']
        mgr.push_image(config['repo'], config['tags'])

    @cement.ex(help='Pull base image and image')
    def pull(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})

        config = mgr.config['base_image']
        mgr.pull_image(config['repo_unsquashed'], config['tags'])

        config = mgr.config['base_image']
        mgr.pull_image(config['repo'], config['tags'])

        config = mgr.config['image']
        mgr.pull_image(config['repo'], config['tags'])

    @cement.ex(help='Remove base image, image, and containers')
    def remove(self):
        mgr = wc_env_manager.core.WcEnvManager({'verbose': VERBOSE})

        config = mgr.config['base_image']
        mgr.remove_image(config['repo_unsquashed'], config['tags'], force=True)

        config = mgr.config['base_image']
        mgr.remove_image(config['repo'], config['tags'], force=True)

        config = mgr.config['image']
        mgr.remove_image(config['repo'], config['tags'], force=True)

        mgr.remove_containers(force=True)


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'wc-env-manager'
        base_controller = 'base'
        handlers = [
            BaseController,
            BaseImageController,
            ImageController,
            NetworkController,
            ContainerController,
            AllController,
        ]


def main():
    with App() as app:
        app.run()
