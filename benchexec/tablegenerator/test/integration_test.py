"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import benchexec.util as util
sys.dont_write_bytecode = True # prevent creation of .pyc files

here = os.path.dirname(__file__)
base_dir = os.path.join(here, '..', '..', '..')
bin_dir = os.path.join(base_dir, 'bin')
tablegenerator = os.path.join(bin_dir, 'table-generator')

class TableGeneratorIntegrationTests(unittest.TestCase):

    # Tests compare the generated CSV files and ignore the HTML files
    # because we assume the HTML files change more often on purpose.

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="BenchExec.tablegenerator.integration_test")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cmd(self, *args):
        print(subprocess.check_output(args=args).decode())

    def generate_tables_and_compare_csv(self, args, table_prefix, result_prefix=None, diff_prefix=None):
        self.run_cmd(*[tablegenerator] + list(args) + ['--outputpath', self.tmp])
        generated_files = set(map(lambda x : os.path.join(self.tmp, x), os.listdir(self.tmp)))

        csv_file = os.path.join(self.tmp, table_prefix + '.csv')
        html_file = os.path.join(self.tmp, table_prefix + '.html')
        expected_files = {csv_file, html_file}
        if diff_prefix:
            csv_diff_file = os.path.join(self.tmp, diff_prefix + '.csv')
            html_diff_file = os.path.join(self.tmp, diff_prefix + '.html')
            expected_files |= {csv_diff_file, html_diff_file}

        self.assertSetEqual(generated_files, expected_files, 'Set of generated files differs from set of expected files')

        generated = util.read_file(csv_file)
        expected = util.read_file(here, 'expected', (result_prefix or table_prefix) + '.csv')
        self.assertMultiLineEqual(generated, expected)

        if diff_prefix:
            generated_diff = util.read_file(csv_diff_file)
            expected_diff = util.read_file(here, 'expected', diff_prefix + '.csv')
            self.assertMultiLineEqual(generated_diff, expected_diff)

    def test_simple_table(self):
        self.generate_tables_and_compare_csv(
            [os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_correct_only(self):
        self.generate_tables_and_compare_csv(
            ['--correct-only', os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.correct-only',
            )

    def test_simple_table_all_columns(self):
        self.generate_tables_and_compare_csv(
            ['--all-columns', os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml')],
            'test.2015-03-03_1613.results.predicateAnalysis',
            'test.2015-03-03_1613.results.predicateAnalysis.all-columns',
            )

    def test_simple_table_xml(self):
        self.generate_tables_and_compare_csv(
            ['-x', os.path.join(here, 'simple-table.xml')],
            'simple-table.table',
            'test.2015-03-03_1613.results.predicateAnalysis',
            )

    def test_simple_table_xml_with_columns(self):
        self.generate_tables_and_compare_csv(
            ['-x', os.path.join(here, 'simple-table-with-columns.xml')],
            'simple-table-with-columns.table',
            )

    def test_multi_table(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'predicateAnalysis',
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1815.results.predicateAnalysis.xml'),
            ],
            table_prefix='predicateAnalysis.table',
            )

    def test_multi_table_reverse(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'predicateAnalysis-reverse',
             os.path.join(here, 'results', 'test.2015-03-03_1815.results.predicateAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='predicateAnalysis-reverse.table',
            )

    def test_multi_table_no_diff(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'test.2015-03-03_1613', '--no-diff',
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.table',
            )

    def test_multi_table_differing_files(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'test.2015-03-03_1613',
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613.table',
            diff_prefix='test.2015-03-03_1613.diff',
            )

    def test_multi_table_differing_files_reverse(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'test.2015-03-03_1613-reverse',
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.valueAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-reverse.table',
            diff_prefix='test.2015-03-03_1613-reverse.diff',
            )

    def test_multi_table_differing_files_correct_only(self):
        self.generate_tables_and_compare_csv(
            ['--name', 'test.2015-03-03_1613-correct-only', '--correct-only',
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.predicateAnalysis.xml'),
             os.path.join(here, 'results', 'test.2015-03-03_1613.results.valueAnalysis.xml'),
            ],
            table_prefix='test.2015-03-03_1613-correct-only.table',
            diff_prefix='test.2015-03-03_1613-correct-only.diff',
            )