from pathlib import Path

import pytest

import trunner.config
from trunner.config import ConfigParser, TestConfigParser, TestConfig, ParserError, \
    copy_per_target, array_value, ALL_TARGETS, DEFAULT_TARGETS

# Pytest tries to collect come classes as tests, mark them as not testable
TestConfigParser.__test__ = False
TestConfig.__test__ = False


def test_copy_per_target():
    targets_value = ['target1', 'target2']
    name = 'test'
    exec_bin = 'some_binary'

    test = TestConfig({
        'name': name,
        'exec': exec_bin,
        'targets': {'value': targets_value}
    })

    answers = []
    for target in targets_value:
        answers.append(TestConfig({
            'name': name,
            'exec': exec_bin,
            'target': target
        }))

    tests = copy_per_target(test)

    for test in tests:
        assert test in answers


@pytest.mark.parametrize('case, ans', [
    ({'value': [1, 2, 3], 'include': [1, 4], 'exclude': [2]},
     [1, 3, 4]),
    ({'value': [], 'include': [1], 'exclude': [1]},
     []),
    ({'value': [1], 'include': [0], 'exclude': [1]},
     [0]),
    ({},
     []),
    ({'value': []},
     []),
])
def test_array_value(case, ans):
    assert array_value(case) == ans


class Test_TestConfigParser:
    @pytest.fixture
    def parser(self):
        return TestConfigParser()

    def test_keywords_exc(self, parser):
        test = TestConfig({'not known keyword': 'for real'})
        with pytest.raises(ParserError):
            parser.parse_keywords(test)

    def test_harness_keyword(self, parser, tmp_path):
        # Lack of 'harness' keyword
        test = TestConfig({})
        parser.parse_harness(test, tmp_path)
        assert 'harness' not in test

        # Proper use of 'harness' keyword
        harness = Path('harness.py')
        path = tmp_path / harness
        path.touch()
        test = TestConfig({'harness': harness})
        parser.parse_harness(test, tmp_path)
        assert test['harness'] == path
        assert test['type'] == 'harness'

    def test_harness_keyword_exc(self, parser, tmp_path):
        # Bad extension
        harness = Path('harness.pl')
        path = tmp_path / harness
        path.touch()
        test = TestConfig({'harness': harness})
        with pytest.raises(ParserError):
            parser.parse_harness(test, tmp_path)

        # Lack of harness file
        test = TestConfig({'harness': 'this_doesnt_exist.py'})
        with pytest.raises(ParserError):
            parser.parse_harness(test, tmp_path)

    @pytest.fixture
    def fixed_path(self):
        saved_path = trunner.config.PHRTOS_PROJECT_DIR
        trunner.config.PHRTOS_PROJECT_DIR = Path('/home/user/phoenix-rtos-project')
        yield
        trunner.config.PHRTOS_PROJECT_DIR = saved_path

    @pytest.mark.parametrize('path, case, ans', [
        ('/home/user/phoenix-rtos-project/phoenix-rtos-tests/example',
         {'name': 'name1'},
         'phoenix-rtos-tests.example.name1'),
        ('path/to/test',
         {'name': 'name2'},
         'path.to.test.name2'),
        ('path',
         {},
         None),
    ])
    @pytest.mark.usefixtures('fixed_path')
    def test_name_keyword(self, parser, path, case, ans):
        test = TestConfig(case)
        parser.parse_name(test, path)
        assert test.get('name') == ans

    @pytest.mark.parametrize('case, ans', [
        ({'type': type}, type) for type in TestConfigParser.TEST_TYPES] + [({}, None)]
    )
    def test_type_keyword(self, parser, case, ans):
        test = TestConfig(case)
        parser.parse_type(test)
        assert test.get('type') == ans

    @pytest.mark.parametrize('case', [
        {'type': 'type_that_do_not_exist'},
    ])
    def test_type_keyword_exc(self, parser, case):
        test = TestConfig(case)
        with pytest.raises(ParserError):
            parser.parse_type(test)

    @pytest.mark.parametrize('case, ans', [
        ({}, None),
        ({'ignore': True}, True),
    ])
    def test_ignore_keyword(self, parser, case, ans):
        test = TestConfig(case)
        parser.parse_ignore(test)
        assert test.get('ignore') == ans

    @pytest.mark.parametrize('case', [
        {'ignore': 'false'},
        {'ignore': 1},
        {'ignore': 'yes'},
    ])
    def test_ignore_keyword_exc(self, parser, case):
        test = TestConfig(case)
        with pytest.raises(ParserError):
            parser.parse_ignore(test)

    @pytest.mark.parametrize('case, ans', [
        ({}, None),
        ({'timeout': 1}, 1),
        ({'timeout': '10'}, 10),
        ({'timeout': 0}, 0),
    ])
    def test_timeout_keyword(self, parser, case, ans):
        test = TestConfig(case)
        parser.parse_timeout(test)
        assert test.get('timeout') == ans

    @pytest.mark.parametrize('case', [
        {'timeout': '0x10'},
        {'timeout': 'ten seconds'},
    ])
    def test_timeout_keyword_exc(self, parser, case):
        test = TestConfig(case)
        with pytest.raises(ParserError):
            parser.parse_timeout(test)

    @pytest.mark.parametrize('case', [
        {'value': [], 'include': [], 'exclude': []},
        {'include': [], 'exclude': []},
        {'value': []},
    ])
    def test_is_array(self, parser, case):
        assert TestConfigParser.is_array(case)

    @pytest.mark.parametrize('case', [
        {'value': [], 'include': [], 'exclude': [], 'maybe_also_this': []},
        {'not_array_keyword': []},
    ])
    def test_is_array_exc(self, parser, case):
        with pytest.raises(ParserError):
            TestConfigParser.is_array(case)

    @pytest.mark.parametrize('case, ans', [
        ({}, None),
        ({'targets': {'value': ['ia32-generic']}},
         {'value': ['ia32-generic']}),
    ])
    def test_targets_keyword(self, parser, case, ans):
        test = TestConfig(case)
        parser.parse_targets(test)
        assert test.get('targets') == ans

    @pytest.mark.parametrize('case', [
        {'targets': {'value': ['invalid-target']}},
        {'targets': 'ia32-generic'},
    ])
    def test_targets_keyword_exc(self, parser, case):
        test = TestConfig(case)
        with pytest.raises(ParserError):
            parser.parse_targets(test)

    @pytest.mark.parametrize('case, ans', [
        ({}, {'targets': {'value': DEFAULT_TARGETS}}),
        ({'targets': {}}, {'targets': {'value': DEFAULT_TARGETS}}),
        ({'targets': {'value': ['my-target']}}, {'targets': {'value': ['my-target']}}),
    ])
    def test_setdefault_targets(self, parser, case, ans):
        test = TestConfig(case)
        parser.setdefault_targets(test)
        assert test == ans


class Test_TestConfig:
    @staticmethod
    def sort_targets(config):
        targets = config.get('targets')
        if not targets:
            return

        for value in targets.values():
            value.sort()

    def test_is_dict(self):
        # Test if the TestConfig inherit from dict
        # Most of the code is based on this inheritance
        test = TestConfig(dict())
        assert isinstance(test, dict)

    @pytest.mark.parametrize('main, minor, ans', [
        (
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
            {},
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
        ),
        (
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
            {'targets': {
                'value': ['target4'],
            }},
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
        ),
        (
            {},
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
            {'targets': {
                'value': ['target1'],
                'include': ['target2'],
                'exclude': ['target3']
            }},
        ),
        (
            {'targets': {
                'include': ['target2']
            }},
            {'targets': {
                'include': ['target1'],
            }},
            {'targets': {
                'value': list(ALL_TARGETS) + ['target1'],
                'include': ['target2']
            }}
        ),
    ])
    def test_join_targets(self, main, minor, ans):
        main, minor = TestConfig(main), TestConfig(minor)
        main.join_targets(minor)

        # Sort values to assure equality
        for config in main, ans:
            self.sort_targets(config)

        assert main == ans

    @pytest.mark.parametrize('main, minor, ans', [
        (
            {'key1': 'value1'},
            {'key2': 'value2'},
            {'key1': 'value1', 'key2': 'value2'}
        ),
        (
            {'key1': 'value1'},
            {'key1': 'value2'},
            {'key1': 'value1'}
        ),
    ])
    def test_join(self, main, minor, ans):
        main, minor = TestConfig(main), TestConfig(minor)
        main.join(minor)
        assert main == ans

    @pytest.mark.parametrize('case, targets, ans', [
        (
            {'targets': {
                'value': ['target0', 'target1', 'target2', 'target3'],
                'include': ['target4'],
                'exclude': ['target1']
            }},
            ['target0', 'target2', 'target5'],
            {'targets': {
                'value': ['target0', 'target2']
            }}
        ),
        (
            {'targets': {
                'value': ['target1']
            }},
            ['target2'],
            {'targets': {
                'value': []
            }}
        ),
    ])
    def test_resolve_targets(self, case, targets, ans):
        test = TestConfig(case)
        test.resolve_targets(targets)

        for config in test, ans:
            self.sort_targets(config)

        assert test == ans


class Test_ConfigParser:
    @pytest.fixture
    def config_parser(self):
        return ConfigParser(path=Path('/fake/path'), targets=['fake_target'])

    def test_pop_keyword(self, config_parser):
        value = ['some', 'value']
        config = TestConfig({'key': value})
        assert config_parser.pop_keyword(config, 'key') is value
        with pytest.raises(ParserError):
            config_parser.pop_keyword(config, 'key')

    def test_extract_components(self, config_parser):
        tests = [{'name': 'test1'}, {'name': 'test2'}]
        config = {
            'test': {
                'here is': 'main config',
                'tests': tests
            }
        }

        extracted_main, extracted_tests = config_parser.extract_components(config)
        assert extracted_main == {'here is': 'main config'}
        assert extracted_tests == tests
