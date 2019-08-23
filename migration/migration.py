#!/usr/bin/python3

"""
Optional params:

--repos-config - Path to file with repos config (defailt is 'repos-config.yaml' in script's dir)
--workspace - path to workspace where cloned repos will be placed (default is 'workspace' in script's dir)
--user - user for git ssh access. This parameter is mandatory for some operations

Mandatory params:

operation - Operation to execute
src - Source project from Juniper's organization

tool have next operations:

clean - removes all content in workspace/src directory. (TODO: abandon reviews if they are present)

clone - clones all projects to workspace. If project's dir already exists and 'git status' works well
       then tool will just pull latest changes and chekout HEAD. Overwise it will re-clone it.

commit - copies source's content to destination project and commits changes for each specified branch.

review - pushes committed changes to gerrit.

"""

#TODO: handle moved projects

import argparse
import os
import shutil
import subprocess
import sys
import yaml


SRC_ORGANIZATION = 'Juniper'
GERRIT_URL = 'review.opencontrail.org'
COPY_COMMIT_MESSAGE = "Add content from Juniper"


def log(message, level='INFO'):
    print(level + ' ' + message)


class Migration():

    valid_operations = []
    # list of projects in format: 'old-org/old-name': 'new-org/new-name'
    projects = dict()

    def __init__(self):
        self.path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.valid_operations = list()
        for func in dir(self):
            if callable(getattr(self, func)) and func.startswith('_op_'):
                self.valid_operations.append(func[4:])

        self._parse_args()
        self._load_repos_config()
        self.src_key = '{}/{}'.format(SRC_ORGANIZATION, self.args.src)
        if self.src_key not in self.projects:
            log("Project {} could not be found in repos config".format(self.args.src))
            raise SystemExit()
        project = self.projects[self.src_key]
        self.dst_key = project['dst_key']

        self.work_dir = os.path.normpath(os.path.join(self.path, self.args.workspace, self.args.src))
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir, exist_ok=True)

    def _parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--repos-config', default="./repos-config.yaml", help='Path to file with repos config')
        parser.add_argument('--workspace', default="./workspace", help="path to workspace where cloned repos will be placed")
        parser.add_argument('--user', help="user for git ssh access")
        #TODO: add creds for opencontrail's gerrit
        parser.add_argument('operation', choices=self.valid_operations, help="Operation to execute.")
        parser.add_argument('src', help="Source project from Juniper's organization")
        self.args = parser.parse_args()

    def _load_repos_config(self):
        config = os.path.normpath(os.path.join(self.path, self.args.repos_config))
        log("Reading project's config from {}".format(config))
        with open(config) as fh:
            data = yaml.load(fh, Loader=yaml.FullLoader)
            default_branches = data['default_branches']
            for project in data['projects']:
                src_key = '{}/{}'.format(SRC_ORGANIZATION, project['src'])
                self.projects[src_key] = {
                    "src": project['src'],
                    "dst": project['dst'],
                    "dst_key": '{}/{}'.format(project['dst_org'], project['dst']),
                    "branches": project["branches"] if "branches" in project else default_branches
                }

    def execute(self):
        log("Execute operation {} on project {}".format(self.args.operation, self.args.src))
        log("   New place is {}".format(self.projects[self.src_key]['dst_key']))
        # call operation
        op = getattr(self, '_op_' + self.args.operation)
        op()

    # Operations section

    def _op_clean(self):
        log("Clean everything in {}".format(self.work_dir))
        # remove ${workspace}/${src}/
        shutil.rmtree(self.work_dir)
        #TODO: think about canceling reviews

    def _op_clone(self):
        if not self.args.user:
            log("user must be set for this operation. Please see help for the tool.", level="ERROR")
            raise SystemExit()
        for pkey in self.projects:
            if self._is_git_repo_present(pkey):
                log("Update project {}".format(pkey))
                self._git_pull(pkey)
            else:
                log("Clone project {}".format(pkey))
                self._run_task(self._git_clone, pkey)
        # destination project must be pre-created for now
        self._git_clone(self.dst_key, clone_dir=self.dst_key)

    def _op_commit(self):
        project = self.projects[self.src_key]

        # put destination project into separate directory to avoid naming conflict
        excluded_objects = ['.git']
        src_dir = os.path.join(self.work_dir, project['src'])
        dst_dir = os.path.join(self.work_dir, project['dst_key'])
        # copy src to dest, commit push to review, get Commit-Id
        for branch in project['branches']:
            if self._git_log_grep(dst_dir, COPY_COMMIT_MESSAGE):
                log("Branch {} has been already patched".format(branch))
                continue

            log("Copying src to dst for branch {}".format(branch))
            self._git_checkout(branch, src_dir)
            #TODO: implement branch creation in destination
            self._git_checkout(branch, dst_dir)

            # remove all in dest dir except .git
            for item in os.listdir(dst_dir):
                if item not in excluded_objects:
                    item_path = os.path.join(dst_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

            # copy
            for item in os.listdir(src_dir):
                if item in excluded_objects:
                    continue
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                if item == '.gitreview':
                    self._patch_file(src_path, self.src_key, self.dst_key)
            # we don't fix src_name tp dst_name cause it requires more intelligent work

            log("Patching destination")
            self._patch_dir(dst_dir, self.src_key, self.dst_key)
            self._git_commit(dst_dir, COPY_COMMIT_MESSAGE)

        # find links to src in all projects, change them, commit with Depends-On, push to review
        for pkey in self.projects:
            if pkey == self.src_key:
                continue
            log("Patching {}".format(pkey))
            dst_dir = os.path.join(self.work_dir, self.projects[pkey]['src'])
            self._patch_dir(dst_dir, self.src_key, self.dst_key)
            if self._git_diff_stat(dst_dir):
                log("    Committing...")
                self._git_commit(dst_dir, "Change links from {} to {}".format(self.src_key, self.dst_key))
            else:
                log("    Patch is empty. Skipping...")

        # handle contrail-vnc
        log("Patching contrail-vnc as a special case")
        dst_dir = os.path.join(self.work_dir, "contrail-vnc")
        self._patch_dir(dst_dir,
                        'name="{}" remote="github"'.format(project['src']),
                        'name="{}" remote="githubtf"'.format(project['dst']))
        if self._git_diff_stat(dst_dir):
            log("    Committing...")
            self._git_commit(dst_dir, "Change links from {} to {}".format(self.src_key, self.dst_key))
        else:
            log("    Patch is empty. Skipping...")

    def _op_review(self):
        project = self.projects[self.src_key]

    # private helpers' functions

    def _is_git_repo_present(self, pkey):
        repo_name = pkey.split('/')[1]
        repo_dir = os.path.join(self.work_dir, repo_name)
        if not os.path.exists(repo_dir):
            return False
        result = subprocess.call(['git', 'status'], cwd=repo_dir,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False if result else True

    def _git_pull(self, pkey):
        #TODO: implement
        pass

    def _git_clone(self, pkey, clone_dir=None):
        if not clone_dir:
            clone_dir = pkey.split('/')[1]
        path = os.path.join(self.work_dir, clone_dir)
        if os.path.exists(path):
            shutil.rmtree(path)
        url = 'ssh://{}@{}:29418/{}.git'.format(self.args.user, GERRIT_URL, pkey)
        subprocess.check_call(['git', 'clone', '-q', url, clone_dir], cwd=self.work_dir)

    def _git_checkout(self, branch, repo_dir):
        #TODO: think about absent branch for destination
        subprocess.check_call(['git', 'checkout', branch], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_log_grep(self, repo_dir, message):
        res = subprocess.call('git log --oneline | grep "{}"'.format(message), shell=True, cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False if res else True

    def _git_commit(self, repo_dir, comment):
        subprocess.check_call(['git', 'add', '.'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['git', 'commit', '-m', comment], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_diff_stat(self, repo_dir):
        return subprocess.check_output(['git', 'diff', '--stat'], cwd=repo_dir)

    def _run_task(self, method, *args, **kwargs):
        #TODO: implement threading
        method(*args, **kwargs)

    def _patch_file(self, file, src, dst):
        subprocess.check_call('sed -i -e "s|{}|{}|g" {}'.format(src.replace('"', '\\"'), dst.replace('"', '\\"'), file),
                              shell=True, cwd=self.work_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _patch_dir(self, repo_dir, src, dst):
        cmd = ('find . -not -path "*/.git*" -type f -print0'
               ' | xargs -0 -r sed -i -e "s|{}|{}|g"'.format(src.replace('"', '\\"'), dst.replace('"', '\\"')))
        subprocess.check_output(cmd, shell=True, cwd=repo_dir)


def main():
    migration = Migration()
    migration.execute()


if __name__ == "__main__":
    sys.exit(main())
