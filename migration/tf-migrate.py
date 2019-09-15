#!/usr/bin/python3

"""
Optional params:

--repos-config - Path to file with repos config (defailt is 'repos-config.yaml' in script's dir)
--workspace - path to workspace where cloned repos will be placed (default is 'workspace' in script's dir)
--user - user for git ssh access. This parameter is mandatory for some operations
--force - flag to indicate that operation has to be forced

Mandatory params:

operation - Operation to execute
src - Source project from Juniper's organization

tool have next operations:

clean - removes all content in workspace/src directory. (TODO: abandon reviews if they are present)

clone - clones all projects to workspace. If project's dir already exists and 'git status' works well
       then tool will just pull latest changes and chekout HEAD. Overwise it will re-clone it.

commit - copies source's content to destination project and commits changes for each specified branch.

review - pushes committed changes to gerrit.

merge - checks all pushed review and adds 'Approved +1' for all if 'Code Review +2' and 'Verified +1' are present for all.
        If some review doesn't have these labels then ERROR will be printed and merge will not be applied,
        or if flag 'force' is present then Approved will be set just for part of review with two labels set.

notify - adds notification message to all open reviews for moved project

"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import yaml


SRC_ORGANIZATION = 'Juniper'
GERRIT_URL = 'review.opencontrail.org'
GERRIT_PORT = '29418'
COMMIT_MESSAGE_TAG='Migration'
COPY_COMMIT_MESSAGE = '[{}] Add content from Juniper\n\nAutomated change\n'.format(COMMIT_MESSAGE_TAG)
TEST_DIR = 'test'
NOTIFICATION_MESSAGE = 'Please note that this project will be moved to TF soon.\nPlease create new review after moving is completed'


def log(message, level='INFO'):
    print(level + ' ' + message)


class Migration():

    valid_operations = []
    projects = dict()

    def __init__(self):
        self.path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.valid_operations = list()
        for func in dir(self):
            if callable(getattr(self, func)) and func.startswith('_op_'):
                self.valid_operations.append(func[4:])

        self._parse_args()
        self._load_repos_config()
        # moving project always use 'Juniper' as organization
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
        parser.add_argument('--force', help="Force operation if it's possible", action='store_true', default=False)
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
                src_org = project.get('src_org', SRC_ORGANIZATION)
                src_key = '{}/{}'.format(src_org, project['src'])
                self.projects[src_key] = {
                    "src": project['src'],
                    "src_key": src_key,
                    "dst": project['dst'],
                    "dst_key": '{}/{}'.format(project['dst_org'], project['dst']),
                    "branches": project.get('branches', default_branches),
                    "excludes": project.get('excludes')
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
        #TODO: think about abandon reviews

    def _op_clone(self):
        def _clone(pkey, clone_dir=None):
            if self._is_git_repo_present(pkey, clone_dir=clone_dir):
                log("Update project {}".format(pkey))
                self._git_pull(pkey, clone_dir=clone_dir)
            else:
                log("Clone project {}".format(pkey))
                self._run_task(self._git_clone, pkey, clone_dir=clone_dir)

        if not self.args.user:
            log("user must be set for this operation. Please see help for the tool.", level="ERROR")
            raise SystemExit()
        for pkey in self.projects:
            _clone(pkey)
            # clone controller one more time to separate directory to create test review
            if self.projects[pkey]['src'] in ('contrail-controller', 'controller'):
                _clone(pkey, clone_dir=TEST_DIR)
        # destination project must be pre-created for now in gerrit/github
        _clone(self.dst_key, clone_dir=self.dst_key)

    def _op_commit(self):
        if not self.args.user:
            log("user must be set for this operation. Please see help for the tool.", level="ERROR")
            raise SystemExit()
        project = self.projects[self.src_key]

        # put destination project into separate directory to avoid naming conflict
        excluded_names = ['.git']
        src_dir = os.path.join(self.work_dir, project['src'])
        dst_dir = os.path.join(self.work_dir, project['dst_key'])
        # moved project branch -> change id
        moved_ids = dict()
        # copy src to dest, commit push to review, get Commit-Id
        for branch in project['branches']:
            log("Copying src to dst for branch {}".format(branch))
            self._git_checkout(branch, src_dir)
            #NOTE: branch must be pre-created in destination
            self._git_reset(dst_dir)
            self._git_checkout(branch, dst_dir)

            if self._git_log_grep(dst_dir, COPY_COMMIT_MESSAGE):
                log("Branch {} has been already patched".format(branch))
            else:
                # remove all in dest dir except .git
                self._clean_dir(dst_dir, excluded_names)
                # copy
                self._copy_dir(src_dir, dst_dir, excluded_names)
                # we don't fix src_name to dst_name cause it requires more intelligent work
                log("Patching destination")
                self._patch_dir(dst_dir, self.src_key, self.dst_key, excludes=project.get('excludes'))
                self._git_commit(dst_dir, COPY_COMMIT_MESSAGE)
            _, change_id = self._git_get_last_commit_details(dst_dir, check_msg_tag=COMMIT_MESSAGE_TAG.splitlines()[0])
            moved_ids[branch] = change_id

        # find links to src in all projects, change them, commit with Depends-On, push to review
        commit_msg_tag = "[{}/{}]".format(COMMIT_MESSAGE_TAG, self.src_key)
        changed_ids = dict()
        controller_project = None
        for pkey in self.projects:
            if self.projects[pkey]['src'] in ('contrail-controller', 'controller'):
                controller_project = self.projects[pkey]
            if pkey == self.src_key:
                continue
            dst_dir = os.path.join(self.work_dir, self.projects[pkey]['src'])
            for branch in self.projects[pkey]['branches']:
                log("Patching project {} / branch {}".format(pkey, branch))
                self._git_reset(dst_dir)
                self._git_checkout(branch, dst_dir)

                # specific patches first to prevent these findings in common patch
                if self.projects[pkey]['src'] in ('contrail-vnc', 'vnc'):
                    # contrail-vnc has specific file with name only
                    self._patch_dir_no_check(dst_dir,
                        'name="{}" remote="github"'.format(project['src']),
                        'name="{}" remote="githubtf"'.format(project['dst']))
                # common patch
                self._patch_dir(dst_dir, self.src_key, self.dst_key, excludes=self.projects[pkey].get('excludes'))

                # check and commit
                change_id = None
                if self._git_diff_stat(dst_dir):
                    log("    Committing...")
                    depends_on = moved_ids.get(branch, moved_ids.get('master', list(moved_ids.values())[0]))
                    msg = ("{} Change links from to {}\n\nAutomated change\nDepends-On: {}\n"
                           "".format(commit_msg_tag, self.dst_key, depends_on))
                    self._git_commit(dst_dir, msg)
                    _, change_id = self._git_get_last_commit_details(dst_dir)
                elif self._git_log_grep(dst_dir, commit_msg_tag):
                    log("    Patch is in place. Skipping...")
                    _, change_id = self._git_get_last_commit_details(dst_dir, check_msg_tag=commit_msg_tag)
                else:
                    log("    Patch is empty. Skipping...")
                if change_id:
                    changed_ids.setdefault(pkey, dict())[branch] = change_id

        # create fake commit for contrail-controller
        dst_dir = os.path.join(self.work_dir, TEST_DIR)
        for branch in controller_project['branches']:
            log("Creating test commit for contrail-controller / branch {}".format(branch))
            self._git_reset(dst_dir)
            self._git_checkout(branch, dst_dir)
            self._create_file(dst_dir, 'test', 'do not merge')
            depends = list()
            for pkey in changed_ids:
                if branch in changed_ids[pkey]:
                    depends.append(changed_ids[pkey][branch])
                elif 'master' in changed_ids[pkey]:
                    # if branch is not in changed_ids[pkey]:
                    # - ocata/queens/... not in [master, R1909] then take master
                    depends.append(changed_ids[pkey]['master'])
                else:
                    # - master/R1909 not in [ocata, queens, ...] then take latest by alphabet order
                    branches = changed_ids[pkey].keys()
                    branches.sort()
                    depends.append(changed_ids[pkey][branches[-1]])
            depends.sort()
            msg = ("{} Test review {}\n\nAutomated change\n\n"
                   "".format(commit_msg_tag, self.dst_key))
            for dep in depends:
                msg += "Depends-On: {}\n".format(dep)
            if self._git_log_grep(dst_dir, commit_msg_tag):
                self._git_commit_amend(dst_dir, msg)
            else:
                self._git_commit(dst_dir, msg)

    def _op_review(self):
        if not self.args.user:
            log("user must be set for this operation. Please see help for the tool.", level="ERROR")
            raise SystemExit()
        # moved project
        project = self.projects[self.src_key]
        dst_dir = os.path.join(self.work_dir, project['dst_key'])
        for branch in project['branches']:
            log("Push to review moved project {} / branch {}".format(self.src_key, branch))
            self._git_checkout(branch, dst_dir)
            self._git_review(dst_dir)

        # dependent projects
        controller_project = None
        for pkey in self.projects:
            if self.projects[pkey]['src'] in ('contrail-controller', 'controller'):
                # save contrail-controller project info for next step
                controller_project = self.projects[pkey]
            dst_dir = os.path.join(self.work_dir, self.projects[pkey]['src'])
            for branch in self.projects[pkey]['branches']:
                self._git_checkout(branch, dst_dir)
                if self._git_log_grep(dst_dir, "[{}/{}]".format(COMMIT_MESSAGE_TAG, self.src_key)):
                    log("Push to review project {} / branch {}".format(pkey, branch))
                    self._git_review(dst_dir)

        # test review
        # this code creates test review in contrail-controller project
        # to run all tests and to ensure that all changes are in place,
        # CI takes all these changes and passes successfully.
        # at merge stage this review will be abandoned
        dst_dir = os.path.join(self.work_dir, TEST_DIR)
        for branch in controller_project['branches']:
            self._git_checkout(branch, dst_dir)
            log("Push test to review for branch {}".format(branch))
            change_id = self._git_review(dst_dir)
            self._gerrit_post_comment(change_id, 'check experimental')

    def _op_merge(self):
        if not self.args.user:
            log("user must be set for this operation. Please see help for the tool.", level="ERROR")
            raise SystemExit()
        project = self.projects[self.src_key]
        dst_dir = os.path.join(self.work_dir, project['dst_key'])
        reviews = dict()
        passed = True
        for branch in project['branches']:
            log("Get status of review for moved project {} / branch {}".format(self.src_key, branch))
            _, change_id = self._git_get_last_commit_details(dst_dir)
            reviews[change_id] = self._gerrit_get_reviewed_approved_status(change_id)
            if not reviews[change_id]['reviewed'] or not reviews['verified']:
                passed = False;

        for pkey in self.projects:
            dst_dir = os.path.join(self.work_dir, self.projects[pkey]['src'])
            for branch in self.projects[pkey]['branches']:
                self._git_checkout(branch, dst_dir)
                if not self._git_log_grep(dst_dir, "[{}/{}]".format(COMMIT_MESSAGE_TAG, self.src_key)):
                    continue
                log("Get status of review for dependent project {} / branch {}".format(pkey, branch))
                _, change_id = self._git_get_last_commit_details(dst_dir)
                reviews[change_id] = self._gerrit_get_reviewed_approved_status(change_id)
                if not reviews[change_id]['reviewed'] or not reviews['verified']:
                    passed = False;

        if not passed and not self.args.force:
            log("Not all reviews have 'Code-Review +2' and 'Verified +1' labels. Do nothing.", level='ERROR')
            raise SystemExit()
        for change_id in reviews:
            log('Approving change {}'.format(change_id))
            if reviews[change_id]['reviewed'] and reviews[change_id]['verified']:
                self._gerrit_approve(change_id)
        
    def _op_notify(self):
        reviews = self._gerrit_cmd(['query', '--format', 'JSON', 'project:{}'.format(self.src_key), 'status:open']).splitlines()
        for review in reviews:
            data = json.loads(review)
            if 'id' not in data:
                # last line is stats
                continue
            # TODO: should script set -2 to Code-Review to prevent merges while moving is going?
            self._gerrit_post_comment(data['id'], NOTIFICATION_MESSAGE)

    # private helpers' functions

    def _is_git_repo_present(self, pkey, clone_dir=None):
        # clone_dir substitutes pkey[1]
        if not clone_dir:
            clone_dir = pkey.split('/')[1]
        path = os.path.join(self.work_dir, clone_dir)
        if not os.path.exists(path):
            return False
        result = subprocess.call(['git', 'status'], cwd=path,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False if result else True

    def _git_pull(self, pkey, clone_dir=None):
        #TODO: implement
        pass

    def _git_clone(self, pkey, clone_dir=None):
        if not clone_dir:
            clone_dir = pkey.split('/')[1]
        path = os.path.join(self.work_dir, clone_dir)
        if os.path.exists(path):
            shutil.rmtree(path)
        url = 'ssh://{}@{}:{}/{}.git'.format(self.args.user, GERRIT_URL, GERRIT_PORT, pkey)
        subprocess.check_call(['git', 'clone', '-q', url, clone_dir], cwd=self.work_dir)
        self._git_add_commit_hook(path)

    def _git_add_commit_hook(self, dst_dir):
        subprocess.check_call(['scp', '-p', '-P', GERRIT_PORT,
                               '{}@{}:hooks/commit-msg'.format(self.args.user, GERRIT_URL),
                               '{}/.git/hooks/'.format(dst_dir)], cwd=self.work_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_checkout(self, branch, repo_dir):
        subprocess.check_call(['git', 'checkout', branch], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_reset(self, repo_dir):
        subprocess.check_call(['git', 'reset', '--hard'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['git', 'clean', '-fd'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_log_grep(self, repo_dir, message):
        """Returns True if message is in log and False overwise."""
        msg = message.replace('[', '\\[').replace(']', '\\]')
        res = subprocess.call('git log --oneline | grep "{}"'.format(msg.splitlines()[0]), shell=True, cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return not res

    def _git_commit(self, repo_dir, comment):
        subprocess.check_call(['git', 'add', '.'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['git', 'commit', '-m', comment], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_commit_amend(self, repo_dir, comment):
        subprocess.check_call(['git', 'commit', '--amend', '--no-edit', '-m', comment], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _git_get_last_commit_details(self, repo_dir, check_msg_tag=None):
        git_log = subprocess.check_output(['git', 'log', '-1'], cwd=repo_dir).decode()
        if check_msg_tag and check_msg_tag not in git_log:
            log("Latest commit is not correct", level=ERROR)
            raise SystemExit()
        commit_sha = None
        change_id = None
        for line in git_log.splitlines():
            if line.startswith('commit '):
                commit_sha = line.split()[1]
            if 'Change-Id:' in line:
                change_id = line.split(':')[1].strip()
        return commit_sha, change_id

    def _git_review(self, repo_dir):
        status = subprocess.check_output(['git', 'branch', '-v'], cwd=repo_dir).decode()
        if 'ahead' not in status:
            log('Nothing to commit for {}'.format(repo_dir), level='ERROR')
            raise SystemExit()
        commit_sha, change_id = self._git_get_last_commit_details(repo_dir)
        if not commit_sha or not change_id:
            log('Commit SHA ({}) or Change-Id ({}) could not be defined'.format(commit_sha, change_id), level='ERROR')
            raise SystemExit()
        data = self._gerrit_get_current_patch_set(change_id)
        if data and data.get('revision') == commit_sha:
            log('Review already raised for {}'.format(repo_dir))
            return change_id
        subprocess.check_call(['git', 'review', '-y'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return change_id

    def _git_diff_stat(self, repo_dir):
        # we must to flush all caches.
        subprocess.check_call(['git', 'status'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['git', 'diff'], cwd=repo_dir,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # and finally check
        return subprocess.check_output(['git', 'diff', '--stat'], cwd=repo_dir)

    def _gerrit_get_reviewed_approved_status(self, change_id):
        result = {'reviewed': False, 'approved': False, 'verified': False}
        data = self._gerrit_get_current_patch_set(change_id)
        if not data:
            log("Review {} is not present in gerrit".format(change_id), level='ERROR')
            raise SystemExit()
        for approval in data.get('approvals', list()):
            if approval.get('type') == 'Code-Review' and approval.get('value') == '2':
                result['reviewed'] = True
            if approval.get('type') == 'Approved' and approval.get('value') == '1':
                result['approved'] = True
            if approval.get('type') == 'Verified' and approval.get('value') in ['1', '2']:
                result['verified'] = True
        return result

    def _gerrit_post_comment(self, change_id, comment):
        data = self._gerrit_get_current_patch_set(change_id)
        self._gerrit_cmd(['review', '--message', '"{}"'.format(comment), data['revision']])

    def _gerrit_approve(self, change_id):
        data = self._gerrit_get_current_patch_set(change_id)
        self._gerrit_cmd(['review', '--approved', '1', data['revision']])

    def _gerrit_get_current_patch_set(self, change_id):
        # use only commit info. drop stats
        data = self._gerrit_cmd(['query', '--current-patch-set', '--format', 'JSON', change_id]).splitlines()
        data = [json.loads(item) for item in data]
        if 'type' in data[0] and data[0]['type'] == 'stats':
            # there is no such change_id in gerrit
            return None
        return data[0].get('currentPatchSet')

    def _gerrit_cmd(self, params):
        gerrit_cmd = ['ssh', '-p', GERRIT_PORT, 'ssh://{}@{}'.format(self.args.user, GERRIT_URL), 'gerrit']
        gerrit_cmd.extend(params)
        return subprocess.check_output(gerrit_cmd, cwd=self.work_dir).decode()

    def _run_task(self, method, *args, **kwargs):
        #TODO: implement threading
        method(*args, **kwargs)

    def _patch_file(self, file, src_key, dst_key):
        src_org, src = src_key.split('/')
        dst_org, dst = dst_key.split('/')

        # check file, change something, print warnings
        # tool have to change 'src_org/src_project' to 'dst_org/dst_project'
        #   - except link to github.com/**/wiki
        #   - except links to github.com with commit SHA
        # tool have to find all 'project'
        #   - skip all like 'src/project'
        #   - skip occurrences in files *requirements.txt, ci_unittests.json
        #   - print warnings for rest

        link_prefix = 'https://github.com/'
        wiki_link = '{}{}/wiki'.format(link_prefix, src_key)
        commit_link = '{}{}/blob'.format(link_prefix, src_key)

        # max file is 1mb so just read it
        patched = False
        warnings = []
        try:
            with open(file) as fh:
                lines = fh.readlines()
        except UnicodeDecodeError:
            log("File {} has invalid characters that can be decoded by utf-8".format(file), level='ERROR')
            return

        line_num = 0
        new_lines = []
        for line in lines:
            line_num += 1
            index = 0
            while True:
                index = line.find(src_key, index)
                if index == -1:
                    break
                # check link to Wiki
                if line[index-len(link_prefix):].startswith(wiki_link):
                    index += len(src_key)
                    warnings.append("Link to wiki has been found in line {} and it won't be changed.".format(line_num))
                    continue
                # check link to commit
                if line[index-len(link_prefix):].startswith(commit_link):
                    index += len(src_key)
                    warnings.append("Link to commit has been found in line {} and it won't be changed.".format(line_num))
                    # TODO: next element in path after 'blob' can be commit SHA or branch name or something else.
                    # we can analyze is it a branch name and if this branch in the list of moved branches then we can change the link.
                    continue
                # we can use replace with count=1 but here we definetly know what should be done.
                line = line[0:index] + dst_key + line[index+len(src_key):]
                patched = True
                index += len(dst_key)
            index = 0
            while True:
                index = line.find(src, index)
                if index == -1:
                    break
                # exclude src_key as it was parsed previously
                if line[index-len(src_org)-1:index+len(src)] == src_key:
                    index += len(src)
                    continue
                # skip src in *requirements.txt, ci_unittests.json
                if file.endswith('requirements.txt') or file in ['ci_unittests.json']:
                    index += len(src)
                    continue
                # skip all occurences of pointing to sources - they still are placed in old structure
                if line[index-4:index] == 'src/':
                    index += len(src)
                    continue
                # all other treat as warnings for now
                warnings.append("Name '{}' was found in line {} and it won't be changed. Line is:\n{}".format(src, line_num, line))
                index += len(src)
            new_lines.append(line)

        if not patched and not warnings:
            return
        log("Patching file: {}".format(file))
        for item in warnings:
            log("  " + item, level="WARNING")

        with open(file, 'w') as fh:
            fh.writelines(new_lines)

    def _patch_dir(self, repo_dir, src_key, dst_key, excludes=None):
        src = src_key.split('/')[1]
        cmd = ('find . -not -path "*/.git/*" -not -path "*/vendor/github.com/*"'
               ' -not -path "*.zip" -not -path "*.tgz" -not -path "*.tar.gz"'
               ' -type f -exec grep -I -l "{}" {{}} \;'.format(src))
        output = subprocess.check_output(cmd, shell=True, cwd=repo_dir).decode()
        for file in output.splitlines():
            file = os.path.normpath(file)
            if excludes and file in excludes:
                continue
            dst_path = os.path.join(repo_dir, file)
            self._patch_file(dst_path, src_key, dst_key)

    def _patch_dir_no_check(self, repo_dir, src, dst):
        cmd = (' find . -not -path "*/.git/*" -type f -exec grep -l "{}" {{}} \;'.format(src.replace('"', '\\"')))
        output = subprocess.check_output(cmd, shell=True, cwd=repo_dir).decode()
        for file in output.splitlines():
            dst_path = os.path.join(repo_dir, os.path.normpath(file))
            subprocess.check_call(
                'sed -E -i "" "s|{}|{}|g" {}'.format(src.replace('"', '\\"'), dst.replace('"', '\\"'), dst_path),
                shell=True, cwd=self.work_dir,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _clean_dir(self, dst_dir, excluded_names):
        for item in os.listdir(dst_dir):
            if item in excluded_names:
                continue
            item_path = os.path.join(dst_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    def _copy_dir(self, src_dir, dst_dir, excluded_names):
        for item in os.listdir(src_dir):
            if item in excluded_names:
                continue
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(dst_dir, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

    def _create_file(self, fdir, filename, content):
        path = os.path.join(fdir, filename)
        with open(path, 'w') as fh:
            fh.write(content)


def main():
    migration = Migration()
    migration.execute()


if __name__ == "__main__":
    sys.exit(main())
