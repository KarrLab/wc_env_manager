"""
:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-03-31
:Copyright: 2018, Karr Lab
:License: MIT
"""

import unittest
import os
import sys
import tempfile
import shutil
import subprocess

from wc_env.compile_requirements import CompileRequirements


class TestCompileRequirements(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.test_repos = os.path.join(self.dirname, 'test_repos')
        os.mkdir(self.test_repos)

        # create a test repo
        req_files_n_lines = {}
        req_files_n_lines['requirements.txt'] = [
            '',
            'pip <= 9.0.1',
            'git+https://github.com/karrlab/log.git#egg=log_2016.10.12',
            '# pgmpy    # graphical models package',
            'git+https://github.com/KarrLab/pkg_utils.git#egg=pkg_utils-0.0.3[all]',
            'Cython>=0.21',
            'capturer # capture stdout',
        ]
        req_files_n_lines['tests/requirements.txt'] = [
            'capturer # to capture standard output in tests',
            'git+https://github.com/KarrLab/pkg_utils.git#egg=pkg_utils-0.0.3[all]',
            'git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1     # wc modeling language',
            'Cython>=0.21',
            'git+https://github.com/KarrLab/log.git#egg=log-2016.10.12 # >= 2016.10.12',
        ]
        req_files_n_lines['requirements.optional.txt'] = [
            'Cython>=0.21',
            'git+https://github.com/KarrLab/wc_kb.git#egg=wc_kb-0.0.1'
        ]
        self.wc_repo = self.make_test_repo('test_repo_a', req_files_n_lines)

    def tearDown(self):
        save_temp_dir = False
        if save_temp_dir:
            print('temp dir:', self.dirname)
        else:
            shutil.rmtree(self.dirname)

    def test_get_requirements_list(self):
        test_lines = '''
git+https://github.com/KarrLab/log.git#egg=log-2016.10.12 # >= 2016.10.12
# avoid a bug in pyexcel_io 0.4.1; see https://github.com/pyexcel/pyexcel/issues/89
pyexcel_io >= 0.4.2
git+https://github.com/KarrLab/wc_lang.git#egg=wc_lang-0.0.1

pip <= 9.0.1
git+https://github.com/KarrLab/wc_utils.git#egg=wc_utils-0.0.1a5 # wc modeling utilities
pyexcel_io\t# comment
matplotlib                                                       # plotting
not line continuation: trailing white space\\  
        '''
        lines = test_lines.split('\n')
        expected_lines = [
            # remember: get_requirements_list() converts to lowercase, and does s/-/_/
            'git+https://github.com/karrlab/log.git#egg=log_2016.10.12',
            'git+https://github.com/karrlab/wc_lang.git#egg=wc_lang_0.0.1',
            'git+https://github.com/karrlab/wc_utils.git#egg=wc_utils_0.0.1a5',
            'matplotlib',
            'not line continuation: trailing white space\\',
            'pip',
            'pyexcel_io',
        ]
        actual_lines = CompileRequirements.get_requirements_list(lines)
        self.assertEqual(expected_lines, actual_lines)
        with self.assertRaises(ValueError):
            CompileRequirements.get_requirements_list(['ok \line', 'line with continuation\\'])

    def make_requirements_file(self, repo_dir, filename, lines):
        # make a requirements file for testing
        pathname = os.path.join(repo_dir, filename)
        os.makedirs(os.path.dirname(pathname), exist_ok=True)
        try:
            req_file = open(pathname, 'w')
            for line in lines:
                print(line, file=req_file)
        except OSError as e:
            print("Error: OSError '{}' while writing {}".format(e, pathname), file=sys.stderr)

    def make_test_repo(self, repo_name, req_files_n_lines):
        # make all the requirements files for a repo
        wc_repo_root = os.path.join(self.test_repos, repo_name)
        os.mkdir(wc_repo_root)
        for req_file,lines in req_files_n_lines.items():
            self.make_requirements_file(wc_repo_root, req_file, lines)
        return wc_repo_root

    def test_get_repos_requirements(self):

        expected_wc_repos = set('log pkg_utils wc_lang wc_kb'.split())
        computed_wc_repos = CompileRequirements.get_repos_requirements(self.wc_repo)
        self.assertEqual(expected_wc_repos, computed_wc_repos)

        computed_wc_repos = CompileRequirements.get_repos_requirements(self.wc_repo, only_wc_repos=False)
        expected_wc_repos = set('capturer cython log pip pkg_utils wc_lang wc_kb'.split())
        self.assertEqual(expected_wc_repos, computed_wc_repos)

    def test_all_requirements(self):
        # create another local test repo
        req_files_n_lines = {}
        req_files_n_lines['requirements.txt'] = ['docker', 'capturer', 'git', 'foo']
        req_files_n_lines['docs/requirements.txt'] = ['sphinx', 'foo', 'bar']
        test_repo_b = self.make_test_repo('test_repo_b', req_files_n_lines)
        test_repos = [self.wc_repo, test_repo_b]
        # todo: finish
        # create a couple of of 'KarrLab' test repos
        # test all_requirements()

    def create_repository(self, name, requirements_files, user, github_api_token, ssh_github_key_file):
        """ Create a Git repository with specified requirements files

        Args:
            name (:obj`str`): package name
            requirements_files (:obj`dict`): some requirements files and their content
            user (:obj`str`): name of the GitHub user
            github_api_token (:obj`str`): GitHub 'Personal access token' for the user
            ssh_github_key_file (:obj`str`): pathname to ssh private key that's registered with the
                user's GitHub account and doe not need a passphrase

        Returns:
            :obj:`tuple`: (directory of the repo created,
                the data returned by the curl command that creates the repo on GitHub)
        """
        # todo: ensure that repo 'name' does not already exist

        # make repo dir with requirements files
        repo_dir = self.make_test_repo(name, requirements_files)
        # make into a git repo
        self.run_subprocess('git init'.split(), cwd=repo_dir)
        # add requirements files
        for file in requirements_files.keys():
            req_file = os.path.join(repo_dir, file)
            self.run_subprocess('git add {}'.format(req_file).split(), cwd=repo_dir)

        # commit
        self.run_subprocess(['git', 'commit', '-m', "'first commit of {}'".format(name)], cwd=repo_dir)

        # create repo on GitHub
        # use curl and a GitHub 'Personal access token'
        # curl --user artgoldberg:PERSONAL_ACCESS_TOKEN https://api.github.com/user/repos --data {"name":"REPO_NAME"}
        cmd = ['curl', '--user', '{}:{}'.format(user, github_api_token),
            'https://api.github.com/user/repos', '--data', "{\"name\":\""  + name + "\"}"]
        curl_rv = self.run_subprocess(cmd, cwd=repo_dir)

        # configure remote
        cmd = "git remote add origin git@github.com:{}/{}.git".format(user, name)
        self.run_subprocess(cmd.split(), cwd=repo_dir)

        # todo: try to use the github_api_token, so this test is easier to configure
        # configure git to use an ssh command that uses the key provided
        # requires git 2.10+; see https://stackoverflow.com/a/38474220/509882
        cmd = ['git', 'config', 'core.sshCommand', "ssh -i {} -F /dev/null".format(
            ssh_github_key_file)]
        self.run_subprocess(cmd, cwd=repo_dir)
        # could also use these ssh options: -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no

        # push the new repo
        self.run_subprocess("git push -u origin master".split(), cwd=repo_dir)

        return (repo_dir, curl_rv)
        ##############
        # TODO
        # method to delete repos
        # respond to GitHub email
        ##############

    def test_create_repository(self):
        # self.create_repository('test_repo_3', dir)
        req_files_n_lines = {}
        req_files_n_lines['requirements.txt'] = ['docker', 'capturer', 'git', 'foo']
        req_files_n_lines['docs/requirements.txt'] = ['sphinx', 'foo', 'bar']
        # todo: get constants from params and config file
        # using 'token for testing wc_env'
        github_api_token_file = os.path.join(os.path.dirname(__file__), '../tokens/github_api_token')
        github_api_token = open(github_api_token_file, 'r').readline().strip()
        ssh_github_key_file = os.path.expanduser('~/.ssh/id_rsa_github')
        username = 'artgoldberg'

        for i in range(1, 5):
            repo_name = 'test_repo_{}'.format(i)
            repo_dir, curl_rv = self.create_repository(repo_name, req_files_n_lines, username,
                github_api_token, ssh_github_key_file)
            print(curl_rv)

    def run_subprocess(self, command, cwd=None):
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.stdout = result.stdout.decode('utf-8')
        result.stderr = result.stderr.decode('utf-8')
        result.check_returncode()
        return result.stdout
