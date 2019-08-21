#!/usr/bin/python3

import argparse
import os
import sys


OLD_ORGANIZATION = 'Juniper'


def log(message, level='INFO'):
    print(level + ' ' + message)


class Migration():

    valid_operations = ['prepare']
    # list of projects in format: 'old-org/old-name': 'new-org/new-name'
    projects = dict()

    def __init__(self):
        self._parse_args()
        self._load_repos_config()
        self.src = '{}/{}'.format(OLD_ORGANIZATION, self.args.src)
        if self.src not in self.projects:
            log("Project {} could not be found in repos config".format(self.args.src))
            raise SystemExit()


    def _parse_args(self):
        parser = argparse.ArgumentParser(description='Process some integers.')
        parser.add_argument('--repos-config', default="./repos.config", help='Path to file with repos config')
        parser.add_argument('--workspace', default="./workspace", help="path to workspace where cloned repos will be placed")
        #TODO: add creds for opencontrail's gerrit
        parser.add_argument('operation', choices=self.valid_operations, help="Operation to execute.")
        parser.add_argument('src', help="Source project from Juniper's organization")
        self.args = parser.parse_args()

    def _load_repos_config(self):
        config = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), self.args.repos_config))
        log("Reading project's config from {}".format(config))
        with open(config) as fh:
            for line in fh:
                if not line or line.startswith('#'):
                    continue
                line = line.strip('\n')
                items = line.split()
                if len(items) == 0:
                    continue
                if len(items) != 4:
                    log('Line with incorrect format has been found in repos config: "{}"'.format(str(items)), level='ERROR')
                    raise SystemExit()
                if items[0] != OLD_ORGANIZATION:
                    log('Old organization "{}" is not supported. Only "{}" is supported'.format(items[0], OLD_ORGANIZATION), level='ERROR')
                    raise SystemExit()
                self.projects['{}/{}'.format(items[0], items[1])] = '{}/{}'.format(items[2], items[3])

    def execute(self):
        log("Execute operation {} on project {}".format(self.args.operation, self.args.src))
        log("   New place is {}".format(self.projects[self.src]))

        # clone all repos to ${workspace}/${src}/

        # copy src to dest, commit push to review, get Commit-Id

        # find links to src in all projects, change them, commit with Depends-On, push to review


def main():
    migration = Migration()
    migration.execute()


if __name__ == "__main__":
    sys.exit(main())
