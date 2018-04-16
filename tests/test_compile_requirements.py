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

from wc_env.compile_requirements import CompileRequirements


class TestCompileRequirements(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.test_repos = os.path.join(self.dirname, 'test_repos')
        os.mkdir(self.test_repos)

    def tearDown(self):
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
        wc_repo = self.make_test_repo('test_repo_a', req_files_n_lines)
        expected_wc_repos = set('log pkg_utils wc_lang wc_kb'.split())
        computed_wc_repos = CompileRequirements.get_repos_requirements(wc_repo)
        self.assertEqual(expected_wc_repos, computed_wc_repos)
        computed_wc_repos = CompileRequirements.get_repos_requirements(wc_repo, only_wc_repos=False)
        expected_wc_repos = set('capturer cython log pip pkg_utils wc_lang wc_kb'.split())
        self.assertEqual(expected_wc_repos, computed_wc_repos)

    def test_all_requirements(self):
        # create a couple of local test repos
        # create a couple of of 'KarrLab' test repos
        # test all_requirements()
        pass
