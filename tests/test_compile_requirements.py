"""
:Author: Jonathan Karr <jonrkarr@gmail.com>
:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2018-03-31
:Copyright: 2018, Karr Lab
:License: MIT
"""

from wc_env.compile_requirements import CompileRequirements
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class CompileRequirementsTestCase(unittest.TestCase):

    def setUp(self):
        self.debug = True
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
        self.wc_repo = self.make_local_repo_req_files('test_repo_a', req_files_n_lines)

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

    def get_repo_dir(self, repo_name):
        return os.path.join(self.test_repos, repo_name)

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

    def make_local_repo_req_files(self, repo_name, req_files_n_lines):
        # make all the requirements files for a repo
        wc_repo_root = self.get_repo_dir(repo_name)
        os.mkdir(wc_repo_root)
        for req_file, lines in req_files_n_lines.items():
            self.make_requirements_file(wc_repo_root, req_file, lines)
        return wc_repo_root

    def run_subprocess(self, command, cwd=None):
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.stdout = result.stdout.decode('utf-8')
        result.stderr = result.stderr.decode('utf-8')
        if self.debug:
            print()
            print('command:\n', command)
            print('joined command:\n', ' '.join(command))
            print('result.stdout:\n', result.stdout)
        result.check_returncode()
        return result.stdout

    def make_local_git_repo(self, name):
        """ Make a directory into a git repo

        Uses only command line `git` and the Python standard library.

        Args:
            name (:obj`str`): repository name

        Returns:
            :obj:`str`: directory of the repo made
        """
        repo_dir = self.get_repo_dir(name)
        # make a git repo
        self.run_subprocess('git init'.split(), cwd=repo_dir)
        # git add existing files
        self.run_subprocess(['git', 'add', '.'], cwd=repo_dir)

        return repo_dir

    def github_credentials(self, delete_token=False):
        """ Provide GitHub credentials

        Args:
            delete_token (:obj:`bool`, optional): provide token with delete access

        Returns:
            :obj:`set`: set of names of required repos, optionallly filtered to KarrLab repos
        """
        # todo: get constants from params and config file
        username = 'artgoldberg'
        # using 'token for testing wc_env'
        filename = '../tokens/github_api_token'
        if delete_token:
            filename = '../tokens/github_api_delete_token'
        github_api_token_file = os.path.join(os.path.dirname(__file__), filename)
        github_api_token = open(github_api_token_file, 'r').readline().strip()
        ssh_github_key_file = os.path.expanduser('~/.ssh/id_rsa_github')
        return (username, github_api_token, ssh_github_key_file)

    def create_github_repository(self, name, user, github_api_token, ssh_github_key_file):
        """ Create a GitHub repository from a local git repo

        Use only the Python standard library and command line `git` and `curl`.

        Args:
            name (:obj`str`): repository name
            user (:obj`str`): name of the GitHub user
            github_api_token (:obj`str`): GitHub 'Personal access token' for the user
            ssh_github_key_file (:obj`str`): pathname to ssh private key that's registered with the
                user's GitHub account and doe not need a passphrase

        Returns:
            :obj:`tuple`: (directory of the repo created,
                the data returned by the curl command that creates the repo on GitHub)
        """
        # todo: ensure that repo 'name' does not already exist on GitHub

        repo_dir = self.get_repo_dir(name)
        self.make_local_git_repo(name)

        # git commit
        self.run_subprocess(['git', 'commit', '-m', 'first commit of {}'.format(name)], cwd=repo_dir)

        # create repo on GitHub
        # use curl and a GitHub 'Personal access token'
        # explicitly request GitHub API v3 with Accept header
        cmd = ['curl', '--user', '{}:{}'.format(user, github_api_token),
               '--header',  'Accept: application/vnd.github.v3+json',
               '--data', "{\"name\":\"" + name + "\"}",
               'https://api.github.com/user/repos']
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

    def delete_repository(self, name, user, github_api_token):
        """ Delete a GitHub repository

        CAUTION: permanently deletes a repository, with no recourse for recovering it!

        Args:
            name (:obj`str`): repository name
            user (:obj`str`): name of the GitHub user
            github_api_token (:obj`str`): GitHub 'Personal access token' for the user; must have
                delete_repo access for `user`
        """
        cmd = ['curl', '--user', '{}:{}'.format(user, github_api_token),
               '--header', 'Accept: application/vnd.github.v3+json',
               '--request', 'DELETE', 'https://api.github.com/repos/{}/{}'.format(user, name)]
        self.run_subprocess(cmd)
        # todo: raise exception if deletion fails

    def get_repositories(self, username, github_api_token):
        """ Get a user's GitHub repositories

        Args:
            username (:obj`str`): name of the GitHub user
            github_api_token (:obj`str`): GitHub 'Personal access token' for the user
        """
        # List your repositories: List repositories that are accessible to the authenticated user.
        # GET /user/repos
        cmd = ['curl', '--user', '{}:{}'.format(username, github_api_token),
               '--header',  'Accept: application/vnd.github.v3+json',
               'https://api.github.com//user/repos']
        curl_rv = self.run_subprocess(cmd)
        print('List repositories that are accessible to the authenticated user', curl_rv)

        # List user repositories: List public repositories for the specified user.
        # GET /users/:username/repos
        cmd = ['curl',
               '--header',  'Accept: application/vnd.github.v3+json',
               'https://api.github.com//users/{}/repos'.format(username)]
        curl_rv = self.run_subprocess(cmd)
        print('List public repositories for the specified user.', curl_rv)

    def test_get_repositories(self):
        username, github_api_token, _ = self.github_credentials()
        self.get_repositories(username, github_api_token)

    def test_create_github_repository(self):
        repo_name = 'test_repo_a'
        username, github_api_token, ssh_github_key_file = self.github_credentials()
        repo_dir, curl_rv = self.create_github_repository(repo_name, username,
                                                          github_api_token, ssh_github_key_file)
        self.assertIn('"name": "{}"'.format(repo_name), curl_rv)
        self.assertNotIn("Repository creation failed.", curl_rv)
        username, github_api_token, _ = self.github_credentials(delete_token=True)
        # self.delete_repository(repo_name, username, github_api_token)

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
        test_repo_b = self.make_local_repo_req_files('test_repo_b', req_files_n_lines)
        test_repos = [self.wc_repo, test_repo_b]
        # todo: finish
        # create a couple of of 'KarrLab' test repos
        # test all_requirements()
