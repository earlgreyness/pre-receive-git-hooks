#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

ZERO_COMMIT = '0' * 40
MERGE_COMMIT_SUBJECT_RE = r"^Merge .+ into [-a-z0-9/.']+$"


def log(*messages):
    print(*messages, file=sys.stderr, flush=True)


def is_ascii(text):
    return all(ord(x) < 128 for x in text)


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


def is_imperative(word):
    if word == 'Refactor':
        return True
    return run('wordpos -vb get {}'.format(word)).strip() == word


def get_revisions(commit_hash):
    assert is_sha1(commit_hash)
    return run(
        'git rev-list {} --reverse --not --all'.format(commit_hash)
    ).splitlines()


def check_branch_name(branch_name):
    branch_name = branch_name.split('refs/heads/', 1)[-1]

    if not is_ascii(branch_name):
        raise Error(
            'Bad branch name ({}): Use only ascii characters'
            .format(branch_name)
        )

    branch_name_re = r'^[a-z]{1}[-a-z0-9/.]+[a-z0-9]{1}$'
    if not re.match(branch_name_re, branch_name):
        raise Error(
            'Bad branch name ({}): Match the regex {!r}'
            .format(branch_name, branch_name_re)
        )


def check_commit_message(commit_hash):
    commit_message = run('git show -s --format=%B {}'.format(commit_hash))

    RULE_1 = 'Separate subject from body with a blank line'
    RULE_2 = 'Limit the subject line to 70 characters'
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
            raise Error('Bad commit message ({}): {}'.format(
                commit_hash[:8], message))

    check(is_ascii(commit_message), 'Use only ascii characters')

    lines = [x for x in commit_message.splitlines() if not x.startswith('#')]

    for line in lines[1:]:
        check(len(line) <= 72, RULE_6)
        check(line.rstrip() == line, RULE_8)

    subject_line = lines[0]
    is_merge_commit = subject_line.startswith('Merge branch ') \
        or subject_line.startswith('Merge commit ')

    check(subject_line, RULE_9)

    if not is_merge_commit:
        check(len(subject_line) <= 70, RULE_2)
        check(subject_line[-1].isalnum(), RULE_4)
    else:
        check(
            re.match(MERGE_COMMIT_SUBJECT_RE, subject_line),
            'Subject line for merge commits must match regex {!r}'
            .format(MERGE_COMMIT_SUBJECT_RE)
        )

    words = subject_line.split()
    check(words[0].isalpha() and words[0].capitalize() == words[0], RULE_3)
    check(is_imperative(words[0]), RULE_5)
    check(len(words) > 1, RULE_10)

    if len(lines) > 2:
        check(not lines[1].strip(), RULE_1)
        if not all(x == '' for x in lines[1:]):
            check(lines[2].strip(), RULE_1)


def is_flake8_enabled(directory):
    return '.flake8' in os.listdir(directory)


def check_push(lines):
    for oldrev, newrev, refname in lines:
        if newrev == ZERO_COMMIT:
            # Deleting branch.
            continue
        # Other possibilities: "refs/tags/" and "refs/notes/".
        if refname.startswith('refs/heads/'):
            check_branch_name(refname)
            for commit_hash in get_revisions(newrev):
                check_commit_message(commit_hash)
                with TemporaryDirectory() as tmpdir:
                    run(
                        'GIT_WORK_TREE={1} git archive {0} | tar -x -C {1}'
                        .format(commit_hash, tmpdir)
                    )
                    if is_flake8_enabled(tmpdir):
                        run_flake8(tmpdir)


def run_flake8(directory):
    log('Running flake8...')
    try:
        run(f'flake8 {directory}')
    except subprocess.CalledProcessError as err:
        log(err.output)
        raise Error('Python linter flake8 found errors')


def main():
    lines = [tuple(x.split()) for x in sys.stdin]

    log('=' * 80)
    log('CHECKING CODE QUALITY')
    log('-' * 80)
    code = 0
    try:
        check_push(lines)
    except Error as err:
        log(err)
        code = 1
    else:
        log('OK')
    log('=' * 80)
    return code


if __name__ == '__main__':
    sys.exit(main())
