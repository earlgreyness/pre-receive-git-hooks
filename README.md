# pre-receive-git-hooks

Git hook for checking commit messages and branch names.

# Usage

Install dependencies:

```bash
curl -sL https://deb.nodesource.com/setup_10.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo apt-get install -y python3-pip python3-venv
/usr/bin/python3 -m venv venv
venv/bin/pip install -r requirements.txt
npm install
```

Create executable file `pre-receive` with the following contents:

```bash
#!/usr/bin/env bash
ROOT=/var/opt/gitlab/qa
PATH=$ROOT/venv/bin:$ROOT/node_modules/.bin:$PATH $ROOT/qa.py
```

Create symbolic links to this `pre-receive` script from all the repositories:

```bash
cd /var/opt/gitlab/git-data/repositories/group/repo.git
mkdir custom_hooks
ln -s /var/opt/gitlab/qa/pre-receive custom_hooks/
chown -R git:root custom_hooks
```
