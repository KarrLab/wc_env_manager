import setuptools
try:
    import pkg_utils
except ImportError:
    import pip._internal.main
    pip._internal.main.main(['install', 'pkg_utils'])
    import pkg_utils
import os

name = 'wc_env_manager'
dirname = os.path.dirname(__file__)
package_data = {
    name: [
        'VERSION',
        'config/*.cfg',
        'assets/*'
        'assets/**/*'
    ],
}

# get package metadata
md = pkg_utils.get_package_metadata(dirname, name, package_data_filename_patterns=package_data)

# install package
setuptools.setup(
    name=name,
    version=md.version,
    description="Tools for managing computing environments for whole-cell modeling",
    long_description=md.long_description,
    url="https://github.com/KarrLab/" + name,
    download_url='https://github.com/KarrLab/' + name,
    author="Karr Lab",
    author_email="info@karrlab.org",
    license="MIT",
    keywords='whole-cell computational systems biology docker dependencies',
    packages=setuptools.find_packages(exclude=['tests', 'tests.*']),
    package_data=md.package_data,
    install_requires=md.install_requires,
    extras_require=md.extras_require,
    tests_require=md.tests_require,
    dependency_links=md.dependency_links,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    entry_points={
        'console_scripts': [
            'wc-env-manager = wc_env_manager.__main__:main',
        ],
    },
)
