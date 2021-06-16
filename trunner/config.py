import copy
import os
from pathlib import Path

import yaml

from .tools.text import remove_prefix
from typing import Any, Dict, List, Tuple

PHRTOS_PROJECT_DIR = Path(os.getcwd())
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
        if 'targets' not in config:
            return
        elif 'targets' not in self:
            self['targets'] = config['targets']
            return

        if 'value' in self['targets']:
            # The value field is defined. Do not overwrite it, just return.
            return

        targets = dict(config['targets'])
        targets.setdefault('value', ALL_TARGETS)
        value = array_value(targets)
        self['targets']['value'] = value

    def join(self, config: 'TestConfig') -> None:
        self.join_targets(config)
        for key in config:
            if key not in self:
                self[key] = config[key]

    def resolve_targets(self, allowed_targets: List[str]) -> None:
        targets = array_value(self['targets'])
        targets = set(targets) & set(allowed_targets)
        self['targets'] = {'value': list(targets)}


def copy_per_target(config: TestConfig) -> List[TestConfig]:
    tests = []
    for target in array_value(config['targets']):
        test = copy.deepcopy(config)
        del test['targets']
        test['target'] = target
        tests.append(test)

    return tests


class TestConfigParser:
    KEYWORDS: Tuple[str] = ('exec', 'harness', 'ignore', 'name', 'targets', 'timeout', 'type')
    TEST_TYPES: Tuple[str] = ('unit', 'harness')

    def setdefault_targets(self, config: TestConfig) -> None:
        targets = config.get('targets', dict())
        targets.setdefault('value', DEFAULT_TARGETS)
        config['targets'] = targets

    def setdefault_name(self, config: TestConfig) -> None:
        name = config.get('name')
        if name:
            return

        name = config.get('exec')
        if not name:
            raise ParserError('Cannot resolve the test name')

        config['name'] = name

    def setdefaults(self, config: TestConfig) -> None:
        config.setdefault('ignore', False)
        config.setdefault('type', 'unit')
        config.setdefault('timeout', PYEXPECT_TIMEOUT)
        self.setdefault_name(config)
        self.setdefault_targets(config)

    def parse_keywords(self, config: TestConfig) -> None:
        keywords = set(config)
        uknown = keywords - set(self.KEYWORDS)
        if uknown:
            raise ParserError(f'Uknown keys: {", ".join(map(str, uknown))}')

    def parse_type(self, config: TestConfig) -> None:
        test_type = config.get('type')
        if not test_type:
            return

        if test_type not in self.TEST_TYPES:
            msg = f'wrong test type: {test_type}. Allowed types: {", ".join(self.TEST_TYPES)}'
            raise ParserError(msg)

    def parse_harness(self, config: TestConfig, test_path: Path) -> None:
        harness = config.get('harness')
        if not harness:
            return

        harness = test_path / harness
        if not harness.exists():
            raise ParserError(f'harness {harness} file not found')

        if not harness.suffix == '.py':
            raise ParserError(f'harness {harness} must be python script (with .py extension)')

        config['type'] = 'harness'
        config['harness'] = harness

    def parse_name(self, config: TestConfig, test_path: Path) -> None:
        name = config.get('name')
        if not name:
            return

        # Get a path relative to phoenix-rtos-project
        print(str(PHRTOS_PROJECT_DIR))
        relative_path = remove_prefix(str(test_path), str(PHRTOS_PROJECT_DIR) + '/')
        name = f'{relative_path}/{name}'
        name = name.replace('/', '.')
        config['name'] = name

    def parse_ignore(self, config: TestConfig) -> None:
        ignore = config.get('ignore', False)

        if not isinstance(ignore, bool):
            raise ParserError(f'ignore must be a boolean value (true/false) not {ignore}')

    def parse_timeout(self, config: TestConfig) -> None:
        timeout = config.get('timeout')
        if not timeout:
            return

        if not isinstance(timeout, int):
            try:
                timeout = int(timeout)
            except ValueError:
                raise ParserError(f'wrong timeout: {timeout}. It must be an integer with base 10')

        config['timeout'] = timeout

    @staticmethod
    def is_array(array: Dict[str, List]) -> bool:
        unknown = array.keys() - {'value', 'include', 'exclude'}
        if unknown:
            raise ParserError(f'array: unknown keys: {", ".join(map(str, unknown))}')

        return True

    def parse_targets(self, config: TestConfig) -> None:
        targets = config.get('targets')
        if not targets:
            return

        if not isinstance(targets, dict):
            raise ParserError('"targets" should be a dict with "value", "include", "exclude" keys!')

        TestConfigParser.is_array(targets)
        for value in targets.values():
            unknown = set(value) - set(ALL_TARGETS)
            if unknown:
                raise ParserError(f'targets {", ".join(map(str, unknown))} are uknown')

    def parse(self, config: TestConfig, test_path: Path) -> None:
        self.parse_keywords(config)
        self.parse_targets(config)
        self.parse_harness(config, test_path)
        self.parse_type(config)
        self.parse_timeout(config)
        self.parse_ignore(config)


class ConfigParser:
    def __init__(self, path: Path, targets: List[str]) -> None:
        self.path: Path = path
        self.targets: List[str] = targets
        self.dir_path = path.parents[0]
        self.parser: TestConfigParser = TestConfigParser()
        self.main_config: TestConfig = None

    def load(self) -> Dict[str, Any]:
        with open(self.path, 'r') as f_yaml:
            config = yaml.safe_load(f_yaml)

        return config

    def parse_test(self, test: TestConfig) -> TestConfig:
        self.parser.parse(test, self.dir_path)
        test.join(self.main_config)
        self.parser.setdefaults(test)
        return test

    def resolve_test(self, test: TestConfig) -> None:
        test.resolve_targets(self.targets)

    def set_main_config(self, config: TestConfig) -> None:
        self.main_config = config

    def parse_main_config(self) -> None:
        self.parser.parse(self.main_config, self.dir_path)

    def pop_keyword(self, config: Dict[str, Any], keyword: str) -> Any:
        value = config.pop(keyword, None)
        if not value:
            raise ParserError(f'{self.path}: keyword "{keyword}" not found in the test config')
        return value

    def extract_components(
        self,
        config: Dict[str, Any]
    ) -> Tuple[TestConfig, List[TestConfig]]:
        main_config = self.pop_keyword(config, 'test')
        tests = self.pop_keyword(main_config, 'tests')
        return TestConfig(main_config), list(map(TestConfig, tests))

    def parse(self, config: Dict[str, Any]) -> List[TestConfig]:
        main_config, tests = self.extract_components(config)
        self.set_main_config(main_config)
        parsed_tests = []

        try:
            self.parse_main_config()
            for test in tests:
                test = self.parse_test(test)
                self.resolve_test(test)
                parsed_tests.append(test)
        except ParserError as exc:
            raise ParserError(f'{self.path}: {exc}') from exc

        # Split TestConfig by the target list, so we'll have a single TestConfig per target
        tests = []
        for test in parsed_tests:
            tests.extend(copy_per_target(test))

        return tests
