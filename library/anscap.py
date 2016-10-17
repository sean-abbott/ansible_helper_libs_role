#!/usr/bin/env python

# batteries included
import os
import subprocess

# ansible
from ansible.module_utils.basic import *


DOCUMENTATION = '''
---
module: anscap
short_description: Capistrano style deploy.
description:
    - Tar up a directory locally
    - Transfer the the resulting tarball to the remote machine
    - Note the previous good version (i.e., if this has been deployed before successfully, the currently running deploy
    - untar the tarball into a new directory
    - set "current" directories to point to the new directory
    - restart the application and verify that it's running
    - Roll back to the previous good version if it fails to start
version_added: "2.1"
author: "Sean Abbott, @sean-abbott"
notes:
    - This is pretty...not complete
requirements:
    - tar installed locally and on the path
    - tar installed remotely and on the path
options:
    src:
        description:
            - the local path to directory you want to transfer
        required: true
        default: null
'''

def get_current_working_version():
    pass

def tar_local_directory():
    pass

def copy_tarball_to_host():
    pass

def untar_tarball_in_place():
    pass

def update_current_links():
    pass

def restart_application():
    pass

def rollback():
    pass

def main():

    fields = {
        'src': {'required': True, 'type': 'str'}
    }
    module = AnsibleModule(argument_spec=fields)
    result = {}
    result['tar_success'] = True
    module.exit_json(changed=False, tar_success=result['tar_success'])


if __name__ == '__main__':  
    main()
