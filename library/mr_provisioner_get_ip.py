#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: pressed_upload_module

short_description: This is a simple module based on the PreseedUploader Class,
that uploads/modifies a preseed to MrP from a file.

version_added: "1.0"

description:
    - "This module has been designed to compliment the provisioning role,
    making it able to upload a preseed to MrP, making use of the available API
    for it. It should be noted that MrP does support Jinja2 templating on the
    preseed."

options:
    name:
        description:
            - This is the message to send to the sample module
        required: true
    new:
        description:
            - Control to demo if the result of this module is changed or not
        required: false

author:
    - Baptiste Gerondeau (baptiste.gerondeau@linaro.org)
'''

EXAMPLES = '''
# Pass in a message
- name: Test with a message
  my_new_test_module:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_new_test_module:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_new_test_module:
    name: fail me
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the sample module generates
'''

import requests
import json
try:
    from urllib.parse import urlparse
except ImportError:
     from urlparse import urlparse
try:
        from urllib import quote  # Python 2.X
except ImportError:
        from urllib.parse import quote  # Python 3+

from datetime import date, timedelta
from urlparse import urljoin
from ansible.module_utils.basic import AnsibleModule

class ProvisionerError(Exception):
    def __init__(self, message):
        super(ProvisionerError, self).__init__(message)

class IPGetter(object):
    def __init__(self, mrpurl, mrptoken, machine_id, interface_name =
                 'eth1'):
        self.mrp_url = mrpurl
        self.mrp_token = mrptoken
        self.interface = interface_name
        self.machine_id = machine_id
        self.machine_ip = ''

    def get_interfaces(self):
        headers = {'Authorization': self.mrp_token}
        url = urljoin(self.mrp_url,
                      "/api/v1/machine/{}/interface".format(self.machine_id))
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            raise ProvisionerError('Error fetching {}, HTTP {} {}'.format(self.mrp_url, r.status_code,
                                                         r.reason))
        if len(r.json()) == 0:
            raise ProvisionerError('Error no machine with id "{}"'.format(self.machine_id))

        return r.json()

    def get_ip(self):
        try:
            interfaces = self.get_interfaces()
        except ProvisionerError as e:
            print('Could not fetch interface for machine : "{}"'.format(e))
            return 'FAILURE'

        for i in interfaces:
            if str(i['identifier']) == self.interface:
                if str(i['config_type_v4']) == 'dynamic-reserved' and str(i['configured_ipv4']):
                    return i['configured_ipv4']
                else:
                    return i['lease_ipv4']

def get_machine_by_name(mrp_token, mrp_url, machine_name):
    """ Look up machine by name """
    headers = {'Authorization': mrp_token}
    q = '(= name "{}")'.format(quote(machine_name))
    url = urljoin(mrp_url, "/api/v1/machine?q={}&show_all=false".format(q))
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise ProvisionerError('Error fetching {}, HTTP {} {}'.format(mrp_url,
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
        mrp_url = dict(type='str', required=True),
        mrp_token = dict(type='str', required=True),
        machine_name = dict(type='str', required=True),
        interface_name = dict(type='str', required=False),
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

    machine_id = get_machine_by_name(module.params['mrp_token'],
                                     module.params['mrp_url'],
                                     module.params['machine_name'])['id']

    if module.params['interface_name']:
        ipgetter = IPGetter(module.params['mrp_url'], module.params['mrp_token'],
                            machine_id,
                            module.params['interface_name'])
    else:
        ipgetter = IPGetter(module.params['mrp_url'], module.params['mrp_token'],
                            machine_id)
    try:
        machine_ip = str(ipgetter.get_ip())
    except ProvisionerError as e:
        print('Could not get IP error : "{}"'.format(e))

    if machine_ip:
        result['ip'] = machine_ip
        result['json'] = { 'status': 'ok' }
        result['changed'] = True
    else:
        module.fail_json(msg='Failure to fetch IP from MrP', **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()

