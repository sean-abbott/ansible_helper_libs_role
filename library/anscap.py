#!/usr/bin/env python

# batteries included
import os
import shutil
import subprocess
import tempfile

from contextlib import contextmanager
from filecmp import dircmp

# ansible
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pycompat24 import get_exception
from ansible.errors import AnsibleError


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
    scm_dirty:
        description:
          - True if the SCM source is currently dirty (i.e., under development)
        required: false
        default: null
    scm_shorthash:
        description:
          - an scm commit hash or other identifier (will be used in the app directory)
        required: false
        default: null
    timestamp:
        description:
          - timestamp for deploy.  provided by the action plugin on the host
        required: true
        default: (provided by action plugin)
    src:
        description:
          - The local path to a tarball you want to transfer
        required: true
        default: null
'''

@contextmanager
def _runatpath(path):
    orig_dir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(orig_dir)

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


def get_current_version_dir(app_dir):
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

def untar_in_place(module):
    ''' untar the tarball into the correctly timestamped directory 
    
        Parameters
        ----------
        tuple
            str
                source (either source filepath, or source filename)
            str
                version directory (this is the time-and-scm-stamp subdirectoy we
                need to create. should be a subdirectory of app_dir)

        Returns
        -------
        tuple
            bool
                failed (whether we failed)
            bool
                changed if we created anything
            str
                message - directory created, error message on fail, or '' on no change
    '''
    source = module.params['src']
    app_dir = module.params['app_dir']
    version_dir = module.params['version_dir']

    source_filepath = os.path.join(tempfile.gettempdir(), os.path.basename(source))

    tar_extract_cmd = ["tar", "xf", source_filepath]

    if not os.path.isabs(version_dir):
            return (True, False, "version directory is not absolute") 

    tmp_extract_dir = tempfile.mkdtemp()

    with _runatpath(tmp_extract_dir):
        rc, out, err = module.run_command(tar_extract_cmd)
        if rc:
            return (True, False, "Failed to extract tarfile. rc: {}, stdout: {}, stderr: {}".format(str(rc), out, err))

    chown_cmd = _get_chown_cmd(module).append(tmp_extract_dir)
    if chown_cmd:
        rc, out, err = module.run_command(chown_cmd)
        if rc:
            return (True, False, "Failed to set permissions. rc: {}, stdout: {}, stderr: {}".format(str(rc), out, err))

    if os.path.exists(version_dir):
        cur_new_comp = dircmp(tmp_extract_dir, version_dir)
        if len(cur_new_comp.diff_files) == 0:
            return (False, False, '')
        
        if module.params['force']:
            shutil.copytree(tmp_extract_dir, version_dir)                
            return (False, True, version_dir)
            
    shutil.copytree(tmp_extract_dir, version_dir)
    return (False, True, version_dir)

def update_current_links(params):
    ''' set the "current" link for app

        Returns
        -------
        tuple
            bool
                failed (whether we failed)
            bool
                changed if we created anything
            str
                message - directory created, error message on fail, or '' on no change
    '''
    current_dir = os.path.join(params['app_dir'], 'current')
    if os.path.exists(current_dir):
        if os.path.realpath(current_dir) == params['version_dir']:
            return (False, False, current_dir)
        if os.path.islink(current_dir):
            os.remove(current_dir)
        else:
            return (True, False, '"current" directory in {} is not a symlink.'.format(
                app_dir))
    os.symlink(params['version_dir'], current_dir)
    return (False, True, current_dir)

def rollback(module):
    ''' rollback any changes '''
    current_dir = os.path.join(params['app_dir'], 'current')
    if os.path.exists(current_dir):
        if os.path.islink(current_dir):
            os.remove(current_dir)
        else:
            msg = "current directory {} is not a symlink!".format(current_dir)
            msg += " Something went horribly wrong."
            raise AnsibleError(msg)
    if 'current_app_working_dir' in module.params:
        if module.params['current_app_working_dir']:
            os.symlink(module.params['current_app_working_dir'], current_dir)

    if 'version_dir' in module.params:
        if os.path.exists(module.params['version_dir']):
            shutil.rmtree(module.params['version_dir'])


def _get_version_stamp(params):
    ''' construct the version stamp '''
    scm_dirty = params.get('scm_dirty', False)
    scm_shorthash = params.get('scm_shorthash', '')
    
    if scm_dirty and not scm_shorthash:
        scm_stamp = ''
    elif scm_dirty:
        scm_stamp = '{}{}'.format(scm_shorthash, '_dirty')
    else:
        scm_stamp = scm_shorthash

    return '{}_{}'.format(params['timestamp'], scm_stamp)


def _get_chown_cmd(module):
    ''' construct cmd for chowning extracted files '''
    if module.params['owner']:
        if module.params['group']:
            cmd = ['chown', '-R', '{}:{}'.format(
                module.params['owner'], module.params['group'])]
        else:
            cmd = ['chown', '-R', module.params['owner']]
    elif module.params['group']:
        cmd = ['chgrp', '-R', module.params['group']]
    else:
        cmd = []

    return cmd

def main():

    fields = {
        'app_name': {'required': True, 'type': 'str'},
        'deploy_dir': {'required': True, 'type': 'path'},
        'scm_dirty': {'required': False, 'type': 'bool'},
        'scm_shorthash': {'required': False, 'type': 'str'},
        'src': {'required': True, 'type': 'path'},
        'timestamp': {'required': True, 'type': 'str'},
    }
    module = AnsibleModule(
        argument_spec=fields,
        add_file_common_args=True,
    )
    result = dict(changed=False)

    if not os.path.abspath(module.params['deploy_dir']):
        module.fail_json(msg="deploy_dir is not absolute path: {}".format(
            module.params['deploy_dir']))

    app_dir = os.path.join(module.params['deploy_dir'], module.params['app_name'])
    module.params['app_dir'] = app_dir

    version_stamp = _get_version_stamp(module.params)
    version_dir = os.path.join(app_dir, version_stamp)
    failed, changed, msg = get_current_version_dir(app_dir)
    if failed:
        result['msg'] = msg
        module.fail_json(**result)
    module.params['version_dir'] = version_dir
    module.params['prev_version_dir'] = msg

    prev_hash = ''
    prev_dirty = False

    if not module.params['scm_dirty'] and module.params['scm_shorthash']:
        if not module.params['prev_version_dir'].endswith('dirty'):
            prev_ver_list = module.params['prev_version_dir'].split('_')
            if len(prev_ver_list) > 1 and prev_ver_list[1] == module.params['scm_shorthash']:
                if not module.params['force']:
                    result['msg'] = 'version has already been deployed. use force to force.'
                    result['changed'] = False
                    module.exit_json(**result)

    step_function_dict_list = [
            {
                'func': ensure_deploy_dir,
                'input': app_dir,
                'result_key': 'created_deploy_dir'
            },
            {
                'func': untar_in_place,
                'input': module,
                'result_key': 'untar_directory'
            },
            {
                'func': update_current_links,
                'input': module.params,
                'result_key': 'current_dir'
            },
        ]
    for step in step_function_dict_list:
        failed, changed, msg = step['func'](step['input'])
        if failed:
            result.update(rollback(module))
            result['msg'] = msg
            module.fail_json(**result)
        if changed:
            result['changed'] = True
            if 'result_key' in step:
                result[step['result_key']] = msg
    module.exit_json(**result)


if __name__ == '__main__':  
    main()
