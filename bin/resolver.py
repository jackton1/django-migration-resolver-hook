# Generated by Django 2.0.2 on 2019-12-17 10:38
import argparse
import inspect
import os
import pathlib
import re
import shlex
import subprocess
from importlib import import_module
from itertools import count


def run_command(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output.decode('utf8') == '' and not process.poll():
            break
        if output:
            print(output.decode('utf8').strip())
    rc = process.poll()
    return rc

class Resolver(object):
    def __init__(self, app_name, last, conflict, auto_detect=False, commit=False):
        self.app_name = app_name
        self.app_module = import_module(app_name)
        self.migration_module = import_module('%s.%s' % (app_name, 'migrations'))
        self.last = last # 0539_auto_20200117_2109.py
        self.conflict = conflict  # 0537_auto_20200115_1632.py
        self.auto_detect = auto_detect
        self.commit = commit

        BASE_DIR  = os.path.dirname(os.path.dirname(inspect.getfile(self.app_module)))
        MIGRATION_DIR  = os.path.dirname(inspect.getfile(self.migration_module))

        self.base_path = pathlib.Path(os.path.join(BASE_DIR))
        self.migration_path = pathlib.Path(os.path.join(MIGRATION_DIR))
        self.replace_regex = re.compile(
            """\('{app_name}',\s'(?P<conflict_migration>.*)'\)""".format(app_name=app_name),
            re.I | re.M,
        )

        self.replacement = (
            "('{app_name}', '{prev_migration}')"
            .format(app_name=app_name, prev_migration=last)
        )

        seed = self.last.split('_')[0]

        if str(seed).isdigit():
            next_ = next(count(int(seed) + 1))
            if not str(next_).startswith('0'):
                next_ = '0{next_}'.format(next_=next_)

        else:
            raise NotImplementedError

        self.last_path = list(
            self.migration_path.glob('*{last}*'.format(last=self.last))
        )[0]
        self.conflict_path = list(
            self.migration_path.glob('*{conflict}*'.format(conflict=self.conflict))
        )[0]

        # Calculate the new name
        conflict_parts = self.conflict_path.name.split('_')

        conflict_parts[0] = next_

        new_conflict_name = '_'.join(conflict_parts)

        self.conflict_new_path = self.conflict_path.with_name(new_conflict_name)


    def fix(self):
        if self.auto_detect:
            raise NotImplementedError

        if self.conflict_path.is_file():
            pwd = os.getcwd()
            os.chdir(self.base_path)
            print('Fixing migrations...')

            # Rename the file
            output = re.sub(
                self.replace_regex,
                self.replacement,
                self.conflict_path.read_text(),
            )
            # Write to the conflict file.
            self.conflict_path.write_text(output)

            # Calculate the new name
            self.conflict_path.rename(self.conflict_new_path)


            if self.commit:
                msg = (
                    'Resolved migration conflicts for {} → {}'.format(
                        os.path.basename(str(self.conflict_path)),
                        os.path.basename(str(self.conflict_new_path)),
                    )
                )
                run_command('git add .')
                run_command('git commit -m "{}"'.format(msg))
            os.chdir(pwd)

def parse_args(args=None):
    parser = argparse.ArgumentParser(description='Fix vcs errors with duplicate migration nodes.')
    parser.add_argument(
        '--auto-detect',
        help='Auto-detect and fix migration errors. (Not supported)',
        action='store_true'
    )
    parser.add_argument(
        '--app-name',
        type=str,
        help='App Name',
        required=True,
    )
    parser.add_argument(
        '--last',
        type=str,
        required=True,  # TODO: Required for now.
        help='The glob/full name of the final migration file.'
    )

    parser.add_argument(
        '--conflict',
        type=str,
        required=True, # TODO: Required for now.
        help='The glob/full name of the final migration file with the conflict.'
    )

    parser.add_argument(
        '--commit',
        action='store_true',
        help='Commit the changes made.'
    )

    return parser.parse_args()


def main(args=None):
    args = parse_args(args=args)
    resolver = Resolver(
        app_name=args.app_name,
        auto_detect=args.auto_detect,
        last=args.last,
        conflict=args.conflict,
        commit=args.commit,
    )
    resolver.fix()

if __name__ == '__main__':
    main()


