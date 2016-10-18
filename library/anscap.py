#!/usr/bin/env python

# batteries included
import os
import subprocess

# ansible
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pycompat24 import get_exception


DOCUMENTATION = '''
---
module: anscap
short_description: Capistrano style deploy.
description:
    - (this does not actually create the tarball because methodology is different)
    - Transfer a given tarball to the target machine
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
    app_name:
        description:
          - name of the application being capstyle deployed
        required: true
        default: null
    deploy_dir:
        description:
          - The base directory that you capstyle deploy to
        required: true
        default: null
    src:
        description:
          - The local path to a tarball you want to transfer
        required: true
        default: null
'''

def ensure_deploy_dir(app_dir):
    ''' make sure deploy dir exists and is writable 
    
        Returns
        -------
        tuple
            bool
                failed (whether we failed)
            bool
                changed (whether we changed)
            str
                message - error on failure or directory when changed
    '''
    changed = False
    created_dir = ''
    deploy_dir = os.path.dirname(app_dir)
    if os.path.exists(app_dir):
        if os.path.islink(app_dir):
            app_dir = os.path.realpath(app_dir)
    if os.path.exists(deploy_dir):
        if os.path.islink(deploy_dir):
            deploy_dir = os.path.realpath(deploy_dir)

    if not os.path.exists(app_dir):
        try:
            os.stat(os.path.dirname(deploy_dir))
            os.makedirs(app_dir)
            changed = True
            created_dir = app_dir
        except OSError:
            e = get_exception()
            if "permission denied" in to_native(e).lower():
		msg="Destination parent directory {} is not accessible".format(os.path.dirname(ddeploy_dir))
		return (True, False, msg)
            if not "file exists" in to_native(e).lower():
                raise e
    if not os.path.isdir(app_dir):
        return (True, False, 'app_dir is not a directory')
    if not os.access(app_dir, os.W_OK):
	msg="Destination {} not writable".format(os.path.dirname(app_dir))
        return (True, False, msg)

    return (False, changed, created_dir)


def get_current_working_dir(app_dir):
    ''' get the current working directory for the app

        Returns
        -------
        tuple
            bool
                failed (whether we failed)
            bool
                changed (always False)
            str
                message - existing current diretory, or '' if new deploy
    '''
    current_dir = os.path.join(app_dir, 'current')
    if not os.path.exists(current_dir):
        return (False, False, '')

    if os.path.islink(current_dir):
        return (False, False, os.path.realpath(current_dir))
    else:
        return (True, False, '"current" directory in {} is not a link.'.format(app_dir))

def untar_tarball_in_place():
    #''' untar the tarball into the correctly timestamped directory '''
    pass


def update_current_links():
    pass


def restart_application():
    pass


def rollback():
    pass


def main():

    fields = {
        'app_name': {'required': True, 'type': 'str'},
        'deploy_dir': {'required': True, 'type': 'path'},
        'src': {'required': True, 'type': 'path'},
    }
    module = AnsibleModule(
        argument_spec=fields,
        add_file_common_args=True,
    )
    result = dict(changed=False)
    app_dir = os.path.join(module.params['deploy_dir'], module.params['app_name'])
    step_function_dict_list = [
            {
                'func': ensure_deploy_dir,
                'input': app_dir,
                'result_key': 'created_deploy_dir'
            },
            {
                'func': get_current_working_dir,
                'input': app_dir,
                'result_key': 'current_app_working_dir'
            },
        ]
    for step in step_function_dict_list:
        failed, changed, msg = step['func'](step['input'])
        if failed:
            module.fail_json(msg=msg)
        if changed:
            result['changed'] = True
            result[step['result_key']] = msg
    module.exit_json(**result)


if __name__ == '__main__':  
    main()
