#import pathlib
from pathlib import Path

import pytest

from trunner.config import TestConfigParser, TestConfig, ParserError, ALL_TARGETS, DEFAULT_TARGETS

PATH = '/path/to/test'

# Pytest tries to collect come classes as tests, mark them as not testable
TestConfigParser.__test__ = False
TestConfig.__test__ = False

#@pytest.fixture
#def parser(config, targets):
#    path = pathlib.Path(f'trunner/test/yamls/{config}')
#    return YAMLParser(path, targets)

class TestParser:
    @pytest.fixture
    def parser(self, tmp_path):
        return TestConfigParser(tmp_path)

    def test_harness_keyword(self, parser):
        # Lack of 'harness' keyword
        test = TestConfig({})
        parser.parse_harness(test)
        assert not test 

        # Proper use of 'harness' keyword
        harness = Path('harness.py')
        path = parser.path / harness
        path.touch()
        test = TestConfig({'harness': harness})
        parser.parse_harness(test)
        assert test['harness'] == path 
        assert test['type'] == 'harness'

    def test_harness_keyword_exception(self, parser):
        # Bad extension
        harness = Path('harness.pl')
        path = parser.path / harness
        path.touch()
        test = TestConfig({'harness': harness})
        with pytest.raises(ParserError):
            parser.parse_harness(test)

        # Lack of harness file
        test = TestConfig({'harness': 'this_doesnt_exist.py'})
        with pytest.raises(ParserError):
            parser.parse_harness(test)

    @pytest.mark.parametrize('input, expected', [
        {'', ''}
    ])
    def test_type_keyword(self, parser):
        test = TestConfig({})
        parser.parse_type(test)
        assert test['type'] == 'unit'

        test = TestConfig({'type': 'some_type'})
        parser.parse_type(test)
        assert test['type'] == 'some_type'

    def test_ignore_keyword(self, parser):
        test = TestConfig({})
        parser.parse_type(test)
        assert test[''] == 'unit'
        pass

    def test_ignore_keyword_exception(self, parser):
        pass




#    @pytest.mark.parametrize('input,expected', [
#        (
#            TestConfig({}),
#            TestConfig({})
#        ),
#        (
#            TestConfig({'harness': 'harness.py'}),
#            TestConfig({'harness': f'{PATH}/harness.py', 'type': 'harness'})
#        ),
#    ])
#    def test_harness_keyword_exc(self):
#        pass
#
#    def test_is_array(self):
#        pass
#
#    def test_parse_target_keyword(self):
#        pass
#
#
#
#class TestTarget:
#    @pytest.fixture
#    def targets(self):
#        return ALL_TARGETS
#
#    @pytest.mark.parametrize('config, expect_target', [
#        (
#            'target-test-0.yaml',
#            [
#                ['host-pc']
#            ]
#        ),
#        (
#            'target-test-1.yaml',
#            [
#                ['host-pc'],
#                ['host-pc', 'ia32-generic'],
#                ['ia32-generic']
#            ]
#        ),
#        (
#            'target-test-2.yaml',
#            [
#                ['ia32-generic'],
#                ['host-pc'],
#                ['host-pc']
#            ]
#        ),
#    ])
#    def test_target_keyword(self, parser, expect_target):
#        tests = parser.parse_test_config()
#
#        # Group test targets by name
#        test_targets = {test['name']: list() for test in tests}
#        for test in tests:
#            test_targets[test['name']].append(test['target'])
#
#        for idx, target in enumerate(expect_target):
#            name = f'trunner.test.yamls.test_{idx}'
#            assert sorted(test_targets[name]) == sorted(target)
#
#    @pytest.mark.parametrize('config', [
#        'empty-target-test-0.yaml'
#    ])
#    def test_empty_target(self, parser):
#        tests = parser.parse_test_config()
#        assert not tests
#
#    @pytest.mark.parametrize('targets, expected_targets', [
#        (
#            {},
#            DEFAULT_TARGETS
#        ),
#        (
#            {'include': ['host-pc']},
#            DEFAULT_TARGETS + ['host-pc'],
#        ),
#        (
#            {'exclude': ['ia32-generic']},
#            [target for target in DEFAULT_TARGETS if target != 'ia32-generic']
#        ),
#        (
#            {'value': ['host-pc']},
#            ['host-pc']
#        ),
#        (
#            {'value': ['ia32-generic'],
#             'exclude': ['ia32-generic']},
#            []
#        ),
#        (
#            {'value': ['ia32-generic'],
#             'include': ['ia32-generic'],
#             'exclude': ['ia32-generic']},
#            []
#        ),
#    ])
#    def test_parse_target(self, target, expect_target):
#        # Create minimal test config that can be parsed
#        test = {'targets': targets}
#        YAMLParser().parse_target(test)
#        assert sorted(test['targets']['value']) == sorted(expect_target)
#
#    @pytest.mark.parametrize('target', [
#        {'value': ['turing-machine']},
#        {'value': ['register-machine']},
#    ])
#    def test_parse_target_exc(self, target):
#        # Create minimal test config that can be parsed
#        test = {'targets': target}
#        with pytest.raises(YAMLParserError):
#            YAMLParser().parse_target(test)
