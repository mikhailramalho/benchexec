# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2019  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import tempfile
import unittest
from unittest.mock import patch
import yaml

from benchexec.model import Benchmark
import benchexec.result
import benchexec.util as util

DummyConfig = collections.namedtuple(
    "DummyConfig",
    [
        "name",
        "output_path",
        "container",
        "timelimit",
        "walltimelimit",
        "memorylimit",
        "corelimit",
        "num_of_threads",
        "selected_run_definitions",
        "selected_sourcefile_sets",
        "description_file",
    ],
)(None, "test", False, None, None, None, None, None, None, None, None)

ALL_TEST_TASKS = {
    "false_other_sub_task.yml": "other_subproperty",
    "false_sub_task.yml": "sub",
    "false_sub2_task.yml": "sub2",
    "false_task.yml": "expected_verdict: false",
    "true_task.yml": "expected_verdict: true",
    "unknown_task.yml": "",
}


def mock_expand_filename_pattern(pattern, base_dir):
    if pattern == "*.yml":
        return list(ALL_TEST_TASKS.keys()) + ["other_task.yml"]
    return [pattern]


def mock_load_task_def_file(f):
    if f in ["false_other_sub_task.yml", "false_sub_task.yml", "false_sub2_task.yml"]:
        content = """
            input_files: {}.c
            properties:
                - property_file: test.prp
                  expected_verdict: false
                  subproperty: {}
                - property_file: other.prp
                  expected_verdict: false
            """.format(
            f, ALL_TEST_TASKS[f]
        )
    elif f in ALL_TEST_TASKS:
        content = """
            input_files: {}.c
            properties:
                - property_file: test.prp
                  {}
                - property_file: other.prp
                  expected_verdict: false
            """.format(
            f, ALL_TEST_TASKS[f]
        )
    elif f == "other_task.yml":
        content = """
            input_files: d.yml.c
            properties:
                - property_file: other.prp
                  expected_verdict: false
            """

    return yaml.safe_load(content)


def mock_property_create(property_file, allow_unknown):
    assert property_file == "test.prp"
    assert allow_unknown
    return benchexec.result.Property("test.prp", False, False, "test", None)


class TestBenchmarkDefinition(unittest.TestCase):
    """
    Unit tests for reading benchmark definitions,
    testing mostly the classes from benchexec.model.
    """

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

    @patch("benchexec.model.load_task_definition_file", new=mock_load_task_def_file)
    @patch("benchexec.result.Property.create", new=mock_property_create)
    @patch("benchexec.util.expand_filename_pattern", new=mock_expand_filename_pattern)
    @patch("os.path.samefile", new=lambda a, b: a == b)
    def parse_benchmark_definition(self, content):
        with tempfile.NamedTemporaryFile(
            prefix="BenchExec_test_benchmark_definition_", suffix=".xml", mode="w+"
        ) as temp:
            temp.write(content)
            temp.flush()

            # Because we mocked everything that accesses the file system,
            # we can parse the benchmark definition although task files do not exist.
            return Benchmark(temp.name, DummyConfig, util.read_local_time())

    def check_task_filter(self, filter_attr, expected):
        # The following three benchmark definitions are equivalent, we check each.
        benchmark_definitions = [
            """
            <benchmark tool="dummy">
              <propertyfile {}>test.prp</propertyfile>
              <tasks><include>*.yml</include></tasks>
              <rundefinition/>
            </benchmark>
            """,
            """
            <benchmark tool="dummy">
              <tasks>
                <propertyfile {}>test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <rundefinition/>
            </benchmark>
            """,
            """
            <benchmark tool="dummy">
              <tasks>
                <include>*.yml</include>
              </tasks>
              <rundefinition>
                <propertyfile {}>test.prp</propertyfile>
              </rundefinition>
            </benchmark>
            """,
        ]

        for bench_def in benchmark_definitions:
            benchmark = self.parse_benchmark_definition(bench_def.format(filter_attr))
            run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
            self.assertListEqual(run_ids, sorted(expected))

    def test_expected_verdict_no_filter(self):
        self.check_task_filter("", ALL_TEST_TASKS.keys())

    def test_expected_verdict_true_filter(self):
        self.check_task_filter('expectedverdict="true"', ["true_task.yml"])

    def test_expected_verdict_false_filter(self):
        false_tasks = [f for f in ALL_TEST_TASKS.keys() if f.startswith("false")]
        self.check_task_filter('expectedverdict="false"', false_tasks)

    def test_expected_verdict_false_subproperty_filter(self):
        self.check_task_filter('expectedverdict="false(sub)"', ["false_sub_task.yml"])

    def test_expected_verdict_unknown_filter(self):
        self.check_task_filter('expectedverdict="unknown"', ["unknown_task.yml"])

    def test_expected_verdict_false_subproperties_filter(self):
        benchmark_definition = """
            <benchmark tool="dummy">
              <tasks>
                <propertyfile expectedverdict="false(sub)">test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <tasks>
                <propertyfile expectedverdict="false(sub2)">test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <rundefinition/>
            </benchmark>
            """
        benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["false_sub_task.yml", "false_sub2_task.yml"])
