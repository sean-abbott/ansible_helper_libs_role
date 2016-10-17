# batteries included
import os
import subprocess
import time

# ansible
from ansible import utils
from ansible.module_utils._text import to_native
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    class AnsCapError(Exception):
        def __init__(self, msg):
            self.msg = msg


    def _get_git_facts(self):
        get_git_args = {'path': self._task.args['src']}
        return self._execute_module(module_name='get_git_data',
                module_args=get_git_args)


    def _check_source_ok(self):
        ''' source must be a tarball and tar must be able to read it '''
        source = self._task.args['src']
        if not os.path.exists(source):
            msg = "local source file {} does not exist".format(to_native(source))
            raise self.AnsCapError(msg)


    def run(self, tmp=None, task_vars=None):
        ''' handler for anscap operations '''
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        source = self._task.args.get('src', None)

        if (source is None):
            result['failed'] = True
            result['msg'] = "src is required"
            return result

        try:
            self._check_source_ok()
        except self.AnsCapError as e:
            result['failed'] = True
            result['msg'] = e.msg
            return result
        
        module_return = self._execute_module(module_name='anscap',
                module_args=self._task.args, task_vars=task_vars,
                tmp=tmp)

        result.update(module_return)
        return result
