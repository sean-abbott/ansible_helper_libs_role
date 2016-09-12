#!/usr/bin/env python

# batteries included
import os
import subprocess

# ansible
from ansible.module_utils.basic import *


DOCUMENTATION = '''
---
module: get_git_data
short_description: get short hash, branch, and dirty from git
'''

def get_branch_name():
    """ At the current working directory get the branch name. """
    git_get_branch_command = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
    try:
        git_branch = subprocess.check_output(git_get_branch_command).strip()
    except subprocess.CalledProcessError:
        git_branch = ''
    return git_branch

def get_short_hash():
    """ At the current working directory get the short hash. """
    git_get_hash_command = ['git', 'rev-parse', '--short', 'HEAD']
    try:
        git_branch = subprocess.check_output(git_get_hash_command).strip()
    except subprocess.CalledProcessError:
        git_branch = ''
    return git_branch

def get_dirty():
    git_dirty_command = ['git', 'status', '--porcelain']
    try:
        git_mod_list = [x for x in subprocess.check_output(git_dirty_command).split('\n') if x]
        if len(git_mod_list) > 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        return ''

def main():

    fields = {
        'path': {'required': True, 'type': 'str'}
    }
    module = AnsibleModule(argument_spec=fields)
    os.chdir(module.params['path'])
    result = {}
    result['branch'] = get_branch_name()
    result['git_hash'] = get_short_hash()
    result['dirty'] = get_dirty()
    for i in result.keys():
        if result[i] == '':
            module.fail_json(msg="Could not get {}. Check your path.")
    module.exit_json(changed=False, branch=result['branch'], git_hash=result['git_hash'], dirty=result['dirty'])


if __name__ == '__main__':  
    main()
