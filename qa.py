#!/usr/bin/env python3
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ZERO_COMMIT = '0' * 40


def log(message):
    print(message, file=sys.stderr, flush=True)


def run(command):
    return subprocess.check_output(
        command,
        universal_newlines=True,
        shell=True
    )


class Error(Exception):
    pass


def is_sha1(string):
    if len(string) != 40:
        return False
    try:
        int(string, 16)
    except ValueError:
        return False
    return True


def get_revisions(old, new):
    assert is_sha1(old)
    assert is_sha1(new)

    if old == ZERO_COMMIT:
        return run(
            r"git rev-list {0} --not "
            r"$(git for-each-ref refs/heads/ --format='%(refname)' "
            r"| grep -v ^{0}\$)".format(new)
        ).splitlines()
    return run('git rev-list {}..{}'.format(old, new)).splitlines()


def check_branch_name(branch_name):
    branch_name = branch_name.split('refs/heads/', 1)[-1]
    if not re.match(r'^[a-z]{1}[-a-z0-9/]+[a-z0-9]{1}$', branch_name):
        raise Error(
            "Blocking creation of new branch {} because it must only contain "
            "lower-case alpha-numeric characters, '-' or '/', "
            "start with letter and end with letter or digit "
            "and have length of at least 3 characters"
            .format(branch_name)
        )


def check_commit_message(commit_hash):
    commit_message = run('git show -s --format=%B {}'.format(commit_hash))

    RULE_1 = 'Separate subject from body with a blank line'
    RULE_2 = 'Limit the subject line to 50 characters'
    RULE_3 = 'Capitalize the subject line'
    RULE_4 = 'Do not end the subject line with a period'
    RULE_5 = 'Use the imperative mood in the subject line'
    RULE_6 = 'Wrap the body at 72 characters'
    RULE_7 = 'Use the body to explain what and why vs. how'

    RULE_8 = 'Remove trailing whitespace'
    RULE_9 = 'Do not make subject line empty'
    RULE_10 = 'Do not write single worded commits'

    def check(condition, message):
        if not condition:
            raise Error('Bad commit message format for {}: {}'.format(
                commit_hash[:8], message))

    lines = [x for x in commit_message.splitlines() if not x.startswith('#')]

    for line in lines:
        check(len(line) <= 72, RULE_6)
        check(line.rstrip() == line, RULE_8)

    subject_line = lines[0]
    check(subject_line, RULE_9)
    check(len(subject_line) <= 50, RULE_2)
    first_character = subject_line[0]
    check(first_character.isalpha(), RULE_3)
    check(first_character == first_character.upper(), RULE_3)
    check(subject_line[-1].isalnum() or subject_line[-1] == ')', RULE_4)
    check(len(subject_line.split()) > 1, RULE_10)

    if len(lines) > 2:
        check(not lines[1].strip(), RULE_1)
        if not all(x == '' for x in lines[1:]):
            check(lines[2].strip(), RULE_1)


def check_push(lines):
    for oldrev, newrev, refname in lines:
        if newrev == ZERO_COMMIT:
            # Deleting branch.
            continue
        # Other possibilities: "refs/tags/" and "refs/notes/".
        if refname.startswith('refs/heads/'):
            check_branch_name(refname)
            for commit_hash in get_revisions(oldrev, newrev):
                check_commit_message(commit_hash)
                lint_revision_source_code(commit_hash)


def lint_revision_source_code(commit_hash):
    with TemporaryDirectory() as tmpdir:
        run(
            'GIT_WORK_TREE={1} git archive {0} | tar -x -C {1}'
            .format(commit_hash, tmpdir)
        )
        try:
            run('flake8 {}'.format(tmpdir))
        except subprocess.CalledProcessError as err:
            log(err.output)
            raise Error(str(err))


def main():
    lines = [tuple(x.split()) for x in sys.stdin]

    log('=' * 80)
    try:
        check_push(lines)
    except Error as err:
        log(err)
        return 1
    finally:
        log('=' * 80)
    return 0


if __name__ == '__main__':
    sys.exit(main())