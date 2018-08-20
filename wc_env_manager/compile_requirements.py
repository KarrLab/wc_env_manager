""" Compile package requirements from our git repos

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2018-03-29
:Copyright: 2018, Karr Lab
:License: MIT
"""

from glob import glob
from itertools import chain
import os
import re
import subprocess
import tempfile


# todo: move this to config
KARR_LAB_GIT_HUB_URL = 'git+https://github.com/karrlab/'
# for all wc_repos not already known, get their requirements, continuing until all repos are searched


class CompileRequirements(object):

    @staticmethod
    def get_recursive_wc_requirements(wc_repo):
        """ Obtain all WC requirements for a WC repo, following recursive dependencies

        Args:
             wc_repo (:obj:`str`): a directory containing a clone of a wc repo

        Returns:
            :obj:`set`: set of names of required wc repos, including optional wc repos
        """
        pass

    @staticmethod
    def get_repos_requirements(repo, only_wc_repos=True, karr_lab_git_hub_url=KARR_LAB_GIT_HUB_URL):
        """ Obtain a repo's requirements

        Requirements must be stored in `pip` `requirements.txt` files in the standard locations.

        Args:
            repo (:obj:`str`): path to a directory containing a repository
            only_wc_repos (:obj:`bool`, optional): if set, filter to KarrLab repos; default True
            karr_lab_git_hub_url (:obj:`str`, optional): URL prefix for KarrLab GitHub account

        Returns:
            :obj:`set`: set of names of required repos, optionallly filtered to KarrLab repos
        """
        # obtain all requirements from requirement(s) files in repo
        requirements_files = ['requirements.txt',
                              'tests/requirements.txt',
                              'docs/requirements.txt',
                              'requirements.optional.txt']
        requirements_lines = []
        for requirements_file in requirements_files:
            requirements_path = os.path.join(repo, requirements_file)
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r') as file:
                    requirements_lines.extend(file.readlines())
        requirements_set = CompileRequirements.get_requirements_list(requirements_lines)

        # keep only Karr Lab repos
        wc_repos = set()
        non_wc_repos = set()
        pattern = re.escape(karr_lab_git_hub_url) + '(.+)' + re.escape('.git')
        for req in requirements_set:
            result = re.match(pattern, req)
            if result:
                wc_repos.add(result.group(1))
            else:
                non_wc_repos.add(req)

        if only_wc_repos:
            return wc_repos
        else:
            return wc_repos | non_wc_repos

    @staticmethod
    def get_requirements_list(requirements_lines):
        """ Obtain unique, sorted requirements from list of lines in requirements files

        Args:
             requirements_lines (:obj:`line`): a list of requirements file lines

        Returns:
            :obj:`list`: sorted list of names of required repos

        Raises:
            :obj:`ValueError`: if line continuations ('\') is used
        """
        required_repos = set()
        for line in requirements_lines:
            line = line.rstrip('\n')

            # ignore comments
            if line.startswith('#'):
                continue
            result = re.match('(.+)[ \t]+#', line)
            if result:
                line = result.group(1)

            if line.endswith('\\'):
                # todo: handle line continuations (\), or use a requirements file parser that does
                raise ValueError("line continuations (\) not supported; found in: '{}'".format(line))

            # remove white space
            line = line.strip()

            # remove option headings
            if line and line[0] == '[':
                continue

            # remove version information
            if '>' in line:
                line = line[0:line.find('>')]
            if '<' in line:
                line = line[0:line.find('<')]

            # remove white space, again
            line = line.strip()

            # to detect uniqueness, replace '-' with '_' and use lower case
            line = line.replace('-', '_')
            line = line.lower()

            if line:
                required_repos.add(line)
        return sorted(list(required_repos))

    '''
    Determine all Python requirements for a wc_env image being built, which are the union of:
    1. the Python requirements for the active local wc repos
    2. the requirements for all other KarrLab wc repos (the KarrLab repos minus the local wc repos)
    todo: #2 can be narrowed by determining all requirements for the active local wc repos, recursively.
    Could support active set of repos that includes a specified set of local and other repos.

    Method:
    Inputs: local repos, KarrLab URL and credentials, list of KarrLab WC repos, output file
    Output: output file containing list of repos
    Approach:
    a) gather requirements from all local repos
    b) gather requirements from WC_requirements = {KarrLab repos} - {local repos}
        clone WC_requirements
        gather their requirements
    c) union a) and b)
    '''

    def all_requirements(self, local_wc_repo_paths, karr_lab_wc_repos, karr_lab_git_hub_url=KARR_LAB_GIT_HUB_URL):
        """ Determine all Python requirements for a wc_env image being built

        Args:
            local_wc_repo_paths (:obj:`list` of `str`): full pathnames of local KarrLab repos being modified
            karr_lab_wc_repos (:obj:`list` of `str`): names of all KarrLab WC repos
            karr_lab_git_hub_url (:obj:`str`, optional): URL prefix for KarrLab GitHub account

        Returns:
            :obj:`list` of `str`: list of required repos

        Raises:
            :obj:`subprocess.CalledProcessError`: if 'docker cp' fails; see error conditions in the docker documentation
        """
        # 1) gather requirements from all local wc repos
        all_requirements = set()
        for local_wc_repo_path in local_wc_repo_paths:
            all_requirements |= CompileRequirements.get_repos_requirements(local_wc_repo_path)

        # 2) gather requirements from {KarrLab WC repos} - {local wc repos}
        local_wc_repos = set([os.path.basename(local_wc_repo_path) for local_wc_repo_path in local_wc_repo_paths])
        print('local_wc_repos', local_wc_repos)
        karr_lab_wc_repos = set(karr_lab_wc_repos)
        print('karr_lab_wc_repos', karr_lab_wc_repos)
        other_wc_repos = karr_lab_wc_repos - local_wc_repos
        print('other_wc_repos', other_wc_repos)

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            other_wc_repos_requirements = set()
            for other_wc_repo in other_wc_repos:
                # clone other_wc_repo
                wc_repo_dir = os.path.join(tmp_dir_name, other_wc_repo)
                command = "git clone {}/{}.git {}".format(karr_lab_git_hub_url, other_wc_repo, wc_repo_dir).split()
                print('command', command)
                '''
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result.stdout = result.stdout.decode('utf-8')
                result.stderr = result.stderr.decode('utf-8')
                result.check_returncode()
                other_wc_repos_requirements |= CompileRequirements.get_repos_requirements(wc_repo_dir)
                '''

        # return union of requirements in 1) and 2)

    '''
    def all_requirements(self, kwargs):
        if not os.path.isdir('tmp'):
            os.mkdir('tmp')

        with open(args.output_file, 'w') as file:
            file.truncate()

        # collect requirements
        pkg_requirements = []
        for path in chain(glob('../../**/requirements.txt'),
                          glob('../../**/requirements.optional.txt'),
                          glob('../../**/tests/requirements.txt'),
                          glob('../../**/docs/requirements.txt')):
            with open(path, 'r') as file:
                for line in file.readlines():
                    # to minimize requirement dependencies on other packages, DO NOT use the KarrLab pkg_utils package
                    line = line.strip()

                    # ignore most comments
                    if line.startswith('#'):
                        continue
                    if ' #' in line:
                        line = line[0:line.find(' #')]

                    # remove option headings
                    if line and line[0] == '[':
                        continue

                    # remove version information
                    if '>' in line:
                        line = line[0:line.find('>')]

                    # remove white space
                    line = line.strip()

                    # to detect uniqueness, replace '-' with '_' and use lower case
                    line = line.replace('-', '_')
                    line = line.lower()

                    if line:
                        pkg_requirements.append(line)

        # generate dependencies on PyPI packages, and the modified log package
        requirements = list(filter(lambda req: '://github.com/' not in req, pkg_requirements))
        requirements.extend(list(filter(lambda req: 'egg=log' in req, pkg_requirements)))

        # get unique requirements
        requirements = list(set(requirements))

        # sort requirements for readability
        requirements = natsorted(requirements, alg=ns.IGNORECASE)

        # write to file, which will be used by a Dockerfile
        with open(args.output_file, 'w') as file:
            file.write('\n'.join(requirements))
            file.write('\n')
    '''
