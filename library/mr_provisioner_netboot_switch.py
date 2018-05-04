#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import time
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: mr-provisioner-netboot-switch
short_description: Manage the netboot_enabled switch in Mr Provisioner
description:
    Implemented:
        - Switch the netboot flag off after a certain timeout
    Not Implemented:
        - Switch it on (as there is no use case aside from provisioning)
options:
    name:
        description:
            - Name of the machine whose flag needs to be turned off
        required: true
    timeout:
        description:
            - Timeout before turning the netboot flag off
        required: false
    path:
        description: Local file path to preseed file.
        required: true
    url:
        description: url to provisioner instance in the form of http://192.168.0.3:5000/
        required: true
    token:
        description: Mr. Provisioner auth token
        required: true
author:
    - Baptiste Gerondeau <baptiste.gerondeau@linaro.org>
'''

EXAMPLES = '''
# Turns off test's netboot flag after 600 seconds
- name: 'test'
  timeout: '600'
  url: http://192.168.0.3:5000
  token: "{{ fancy_token }}"
'''

RETURN = '''
Machine json data with netboot_enabled set to False
'''

from ansible.module_utils.basic import AnsibleModule

class ProvisionerError(Exception):
    def __init__(self, message):
        super(ProvisionerError, self).__init__(message)

class NetbootSwitcher(object):
    """This class handles the logic behind switching the netboot flag on and
    off. This is especially useful for devices such as qdc, moonshot and VMs
    which have a tendancy to be stuck on PXE boot mode : without the netboot
    flag enabled, they just boot locally."""
    def __init__(self, mrp_url, mrp_token, machine_name):
        self.url = mrp_url
        self.auth = {'Authorization': mrp_token}
        self.machine_json = self.get_machine_by_name(machine_name)

    def switch_netboot_flag(self):
        """ enables netboot on the machine and pxe boots it """
        url = urljoin(self.url, "/api/v1/machine/{}".format(self.machine_json['id']))
        self.machine_json['netboot_enabled'] = False
        r = requests.put(url, headers=self.auth,
                         data=json.dumps(self.machine_json))

        if r.status_code not in [200, 202]:
            raise ProvisionerError('Error PUTing {}, HTTP {} {}'.format(url,
                         r.status_code, r.reason))
        return r.json()

    def do_timeout(self, timeout_string):
        timeout_int = int(timeout_string)
        time.sleep(timeout_int)

    def get_machine_by_name(self, machine_name):
        """ Look up machine by name """
        q = '(= name "{}")'.format(quote(machine_name))
        url = urljoin(self.url, "/api/v1/machine?q={}&show_all=false".format(q))
        r = requests.get(url, headers=self.auth)
        if r.status_code != 200:
            raise ProvisionerError('Error fetching {}, HTTP {} {}'.format(url,
                         r.status_code, r.reason))
        if len(r.json()) == 0:
            raise ProvisionerError('Error no assigned machine found with name "{}"'.
                format(machine_name))
        if len(r.json()) > 1:
            raise ProvisionerError('Error more than one machine found with name "{}", {}'.
                format(machine_name, r.json()))
        return r.json()[0]

def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        url=dict(type='str', required=True),
        token=dict(type='str', required=True),
        timeout=dict(type='str', required=False, default="300"),
    )

    result = dict(
        changed=False,
        debug={},
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    if module.check_mode:
        return result

    netbooter = NetbootSwitcher(module.params['url'],
    module.params['token'], module.params['name'])

    try:
        netbooter = NetbootSwitcher(module.params['url'],
        module.params['token'], module.params['name'])
        netbooter.do_timeout(module.params['timeout'])
        res = netbooter.switch_netboot_flag()
    except ProvisionerError as e:
        module.fail_json(msg=str(e), **result)

    if 'error' in res:
        module.fail_json(msg=res['error'], **result)

    result['json'] = res
    result['changed'] = True

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
