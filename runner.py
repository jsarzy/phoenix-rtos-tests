#!/usr/bin/env python3

import argparse
import logging
import pathlib
import sys

import trunner.config as config

from trunner.test_runner import TestsRunner
from trunner.config import ConfigParser
from trunner.tools.color import Color


def set_logger(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.terminator = ''
    formatter = logging.Formatter('%(message)s')
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)


def args_file(arg):
    path = pathlib.Path(arg)
    if not path.exists():
        print(f"Path {path} does not exist")
        sys.exit(1)

    path = path.resolve()
    return path


def parse_args():
    logging_level = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR
    }

    parser = argparse.ArgumentParser()

    parser.add_argument("-T", "--target",
                        action='append', choices=config.ALL_TARGETS,
                        help="Filter targets on which test will be built and run. "
                             "By default runs tests on all available targets. "
                             "Flag can be used multiple times.")

    parser.add_argument("-t", "--test",
                        default=[], action='append', type=args_file,
                        help="Specify directory in which test will be searched. "
                             "If flag is not used then runner searches for tests in "
                             "phoenix-rtos-tests directory. Flag can be used multiple times.")

    parser.add_argument("--build",
                        default=False, action='store_true',
                        help="Runner will build all tests.")

    parser.add_argument("-l", "--log-level",
                        default='info',
                        choices=logging_level,
                        help="Specify verbosity level. By default uses level info.")

    parser.add_argument("-s", "--serial",
                        default=config.DEVICE_SERIAL,
                        help="Specify serial to communicate with device board. "
                             "By default uses %(default)s.")

    parser.add_argument("--no-flash",
                        default=False, action='store_true',
                        help="Board will not be flashed by runner.")

    args = parser.parse_args()

    args.log_level = logging_level[args.log_level]

    if not args.test:
        args.test = [config.PHRTOS_TEST_DIR]

    if not args.target:
        # Run on all available targets
        args.target = config.ALL_TARGETS

    config.DEVICE_SERIAL = args.serial

    return args


def resolve_dir_by_target(targets, paths):
    runner = TestsRunner(targets=targets,
                         test_paths=paths,
                         build=False,
                         flash=False)

    runner.search_for_tests()
    good_paths = set() 

    for path in runner.test_paths:
        config_parser = ConfigParser(path, targets)
        config = config_parser.load()
        main_config, tests = config_parser.extract_components(config)
        config_parser.set_main_config(main_config)
        config_parser.parser.parse_targets(main_config)
        for test in tests:
            config_parser.parser.parse_targets(test)
            test.join_targets(main_config)
            config_parser.parser.setdefault_targets(test)
            test.resolve_targets(targets)
            if test['targets']['value']:
                good_paths.add(path)

    return list(good_paths)


def main():
    args = parse_args()
    set_logger(args.log_level)
    paths = resolve_dir_by_target(args.target, args.test)
    print('\n'.join(map(str, paths)))
    return


    runner = TestsRunner(targets=args.target,
                         test_paths=args.test,
                         build=args.build,
                         flash=not args.no_flash)

    passed, failed, skipped = runner.run()

    total = passed + failed + skipped
    summary = f'TESTS: {total}'
    summary += f' {Color.colorify("PASSED", Color.OK)}: {passed}'
    summary += f' {Color.colorify("FAILED", Color.FAIL)}: {failed}'
    summary += f' {Color.colorify("SKIPPED", Color.SKIP)}: {skipped}\n'
    logging.info(summary)

    if failed == 0:
        print("Succeeded!")
        sys.exit(0)
    else:
        print("Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
