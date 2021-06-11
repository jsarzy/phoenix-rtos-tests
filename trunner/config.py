import logging
import os
import pathlib

import yaml

from .tools.text import remove_prefix
from typing import Any, Dict, List, Set, Tuple

PHRTOS_PROJECT_DIR = pathlib.Path(os.getcwd())
PHRTOS_TEST_DIR = PHRTOS_PROJECT_DIR / 'phoenix-rtos-tests'

# Default time after pexpect will raise TIEMOUT exception if nothing matches an expected pattern
PYEXPECT_TIMEOUT = 8

# Available targets for test runner.
ALL_TARGETS = ['ia32-generic', 'host-pc', 'armv7m7-imxrt106x']

# Default targets used by parser if 'target' value is absent
DEFAULT_TARGETS = [target for target in ALL_TARGETS
                   if target not in ('host-pc', 'armv7m7-imxrt106x')]

DEVICE_TARGETS = ['armv7m7-imxrt106x']

# Port to communicate with hardware board
DEVICE_SERIAL = "/dev/ttyACM0"


class ParserError(Exception):
    pass


def array_value(array: Dict[str, List[str]]) -> List[str]:
    value = set(array.get('value', []))
    value |= set(array.get('include', []))
    value -= set(array.get('exclude', []))

    return list(value)


class TestConfig(dict):
    def __init__(self, config: Dict[str, Any]) -> None:
        self.update(**config)

    def join_targets(self, config: 'TestConfig') -> None:
        if not config.get('targets'):
            return

        value = array_value(config['targets'])
        if not self.get('targets'):
            self.setdefault('targets', {'value': value})
        else:
            self['targets'].setdefault('value', value)

        #value = array_value(config['targets'])
        #self.setdefault('targets', {})
        #self['targets'].setdefault('value', value)

    def join(self, config: 'TestConfig') -> None:
        self.join_targets(config)
        for key in config:
            if key not in self:
                self[key] = config[key]

    def resolve_targets(self, allowed_targets: List[str]) -> None:
        targets = array_value(self['targets'])
        targets = set(targets) & set(allowed_targets)
        self['targets'] = {'value': list(targets)}

    def resolve_name(self, path: pathlib.Path) -> None:
        name = self.get('name')
        if not name:
            raise ParserError('key "name" not found!')

        # Get path relative to phoenix-rtos-project
        relative_path = remove_prefix(str(path), str(PHRTOS_PROJECT_DIR) + '/')
        name = f'{relative_path}/{name}'
        name = name.replace('/', '.')
        self['name'] = name


def copy_per_target(config: TestConfig) -> List[TestConfig]:
    tests = []
    for target in array_value(config['targets']):
        test = config.copy()
        del test['targets']
        test['target'] = target
        tests.append(test)

    return tests


class TestConfigParser:
    ALLOWED_KEYS: Set[str] = {'exec', 'harness', 'ignore', 'name', 'targets', 'timeout', 'type'}
    REQUIRED_KEYS: Set[str] = {'exec'}

    def __init__(self, path: pathlib.Path) -> None:
        self.path: pathlib.Path = path

    def parse_keywords(self, config: TestConfig, check_required_keys: bool = True) -> None:
        keywords = set(config)
        uknown = keywords - self.ALLOWED_KEYS
        if uknown:
            raise ParserError(f'Uknown keys: {", ".join(map(str, uknown))}')

        if not check_required_keys:
            return

        required = keywords & self.REQUIRED_KEYS ^ self.REQUIRED_KEYS
        if required:
            raise ParserError(f'Missing required keys: {", ".join(required)}')

    def parse_type(self, config: TestConfig) -> None:
        config.setdefault('type', 'unit')

    def parse_harness(self, config: TestConfig) -> None:
        harness = config.get('harness')
        if not harness:
            return

        harness = self.path / harness
        if not harness.exists():
            raise ParserError(f'harness {harness} file not found')

        if not harness.suffix == '.py':
            raise ParserError(f'harness {harness} must be python script (with .py extension)')

        config['type'] = 'harness'
        config['harness'] = harness

    def parse_ignore(self, config: TestConfig) -> None:
        ignore = config.get('ignore', False)

        if not isinstance(ignore, bool):
            raise ParserError(f'ignore must be a boolean value (true/false) not {ignore}')

        config['ignore'] = ignore

    def parse_timeout(self, config: TestConfig) -> None:
        config.setdefault('timeout', PYEXPECT_TIMEOUT)

    @staticmethod
    def is_array(array):
        unknown = array.keys() - {'value', 'include', 'exclude'}
        if unknown:
            raise ParserError(f'array: unknown keys: {", ".join(map(str, unknown))}')

    def parse_targets(self, config: TestConfig) -> None:
        targets = config.get('targets', dict())
        targets.setdefault('value', DEFAULT_TARGETS)
        TestConfigParser.is_array(targets)

        for value in targets.values():
            unknown = set(value) - set(ALL_TARGETS)
            if unknown:
                raise ParserError(f'targets {", ".join(map(str, unknown))} are uknown')

        config['targets'] = targets

    def parse(self, config: TestConfig, check_required_keys=True) -> None:
        self.parse_keywords(config, check_required_keys)
        self.parse_targets(config)
        self.parse_harness(config)
        self.parse_type(config)
        self.parse_timeout(config)
        self.parse_ignore(config)


class ConfigParser:
    def __init__(self, path: pathlib.Path, targets: List[str]) -> None:
        self.path: pathlib.Path = path
        self.targets: List[str] = targets
        self.dir_path = path.parents[0]
        self.parser: TestConfigParser = TestConfigParser(self.dir_path)
        self.config: Dict[str, Any] = None
        self.minor_config: TestConfig = None
        self.tests: List[TestConfig] = []

    def load(self) -> None:
        with open(self.path, 'r') as f_yaml:
            self.config = yaml.safe_load(f_yaml)

        return self.config

    def parse_test(self, test: TestConfig) -> TestConfig:
        test.join(self.minor_config)
        self.parser.parse(test)
        return test

    def resolve_test(self, test: TestConfig) -> None:
        test.resolve_name(self.dir_path)
        test.resolve_targets(self.targets)

    def set_minor_config(self, config: TestConfig) -> None:
        self.minor_config = config

    def parse_minor_config(self, config: TestConfig) -> None:
        self.parser.parse(self.minor_config, check_required_keys=False)

    def pop_keyword(self, config: Dict[str, Any], keyword: str) -> None:
        value = config.pop(keyword)
        if not value:
            raise ParserError(f'{self.path}: keyword "{keyword}" not found in test config')
        return value

    def extract_components(
        self,
        config: Dict[str, Any]
    ) -> Tuple[TestConfig, List[TestConfig]]:
        minor_config = self.pop_keyword(config, 'test')
        tests = self.pop_keyword(minor_config, 'tests')
        return TestConfig(minor_config), map(TestConfig, tests)

    def parse(self, config: Dict[str, Any]) -> List[TestConfig]:
        minor_config, tests = self.extract_components(config)

        self.set_minor_config(minor_config)
        try:
            self.parse_minor_config(minor_config)
            for test in tests:
                test = self.parse_test(test)
                self.resolve_test(test)
                self.tests.append(test)
        except ParserError as exc:
            raise ParserError(f'{self.path}: {exc}') from exc

        # Split TestConfig by target list, so we'll have a single TestConfig per target
        tests = []
        for test in self.tests:
            tests.extend(copy_per_target(test))
        self.tests = tests

        return self.tests
