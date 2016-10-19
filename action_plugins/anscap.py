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


    def _check_source_ok(self):
        ''' source must be a tarball and tar must be able to read it '''
        source = self._task.args['src']
        if not os.path.exists(source):
            msg = "local source file {} does not exist".format(to_native(source))
            raise self.AnsCapError(msg)


    def run(self, tmp=None, task_vars=None):
        ''' handler for anscap operations '''
        #if task_vars is None:
        #    task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        source = self._task.args.get('src', None)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        self._task.args['timestamp'] = timestamp)

        if (source is None):
            result['failed'] = True
            result['msg'] = "src is required"
            return result

        changed = False

        try:
            # YELLOW might be worth checking to see if it's already there/md5
            self._check_source_ok()
            self._transfer_file(source, '/tmp/{}'.format(os.path.basename(source)))
        except self.AnsCapError as e:
            result['failed'] = True
            result['msg'] = e.msg
            return result
        
        module_return = self._execute_module(module_name='anscap',
                module_args=self._task.args, task_vars=task_vars,
                tmp=tmp)

        result.update(module_return)
        result['changed'] = result['changed'] and changed
        return result
