import datetime
import json
import os
import subprocess
import sys


SSH_CMD = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
SSH_DEST = '-p 29418 zuul-tf@review.opencontrail.org'
GERRIT_CMD = 'gerrit query --comments --format=JSON branch:master limit:{}'
EXCLUDED_PROJECTS = [
    'Juniper/contrail-zuul-jobs',
    'Juniper/contrail-project-config',
    'Juniper/contrail-dev-env',
]

tf_fails = 0
juniper_fails = 0


def check_review(data):
    global tf_fails, juniper_fails
    output = []
    output.append("Review {}, created = {}, updated = {}, URL = {}".format(
        data['number'], datetime.datetime.fromtimestamp(data['createdOn']),
        datetime.datetime.fromtimestamp(data['lastUpdated']), data['url']))
    if data['project'] in EXCLUDED_PROJECTS:
        return output
    patches = dict()
    reviewers = set()
    for comment in data['comments']:
        if "(check pipeline)" not in comment['message'] or 'zuul' not in comment['reviewer']['username']:
            continue
        lines = comment['message'].splitlines()
        num = lines[0].split()[2].split(':')[0]
        status = [line for line in lines if "(check pipeline)" in line][0].split()[1]
        time = str(datetime.datetime.fromtimestamp(comment['timestamp']))
        patches.setdefault(num, list()).append((comment['reviewer']['username'], status, time))
        reviewers.add(comment['reviewer']['username'])

    if len(reviewers) == 1 and next(iter(reviewers)) == 'zuulv3':
        output.append("    ERROR: reviewed just by {}. project {}".format(next(iter(reviewers)), data['project']))

    # check only last patchset
    if not patches:
        return output
    num = max(list(patches.keys()))
    pdata = patches[num]
    statuses = set([item[1] for item in pdata])
    if len(statuses) < 2:
        return output
    statuses_zuul = set([item[1] for item in pdata if item[0] == 'zuulv3'])
    statuses_zuul_tf = set([item[1] for item in pdata if item[0] == 'zuul-tf'])

    if len(statuses_zuul_tf) == 1 and next(iter(statuses_zuul_tf)) == 'succeeded':
        #output.append("    {}: GOOD: TF is better.".format(num))
        juniper_fails += 1
        return output
    if len(statuses_zuul) == 1 and next(iter(statuses_zuul)) == 'succeeded':
        output.append("    {}: BAD: Juniper is better.".format(num))
        tf_fails += 1
        return output

    for item in pdata:
        output.append("    {}: {}\t{}\t{}".format(num, item[0], item[2], item[1]))

    return output


def main():
    limit = "30"
    if len(sys.argv) > 1:
        limit = sys.argv[1]
    cmd = "{} {} {}".format(SSH_CMD, SSH_DEST, GERRIT_CMD)
    cmd = cmd.format(limit)
    output = subprocess.check_output(cmd, shell=True)
    for line in output.splitlines():
        data = json.loads(line)
        if 'id' not in data or data['status'] == 'ABANDONED':
            # looks like it's a summary
            continue
        output = check_review(data)
        if len(output) > 1:
            print('\n'.join(output))
    print("Juniper fails: {}".format(juniper_fails))
    print("TF      fails: {}".format(tf_fails))


if __name__ == "__main__":
    main()
