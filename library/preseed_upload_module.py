#!/usr/bin/env python3
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
from urllib.parse import urljoin
from ansible.module_utils.basic import AnsibleModule

class ProvisionerError(Exception):
    def __init__(self, message):
        super(ProvisionerError, self).__init__(message)

class PreseedUploader(object):
    """ This class handles the job of uploading a preseed file to MrP.
        It shall only be called if there is a file to be uploaded, else you can
        fetch the thing via the regular call in the Ansible role"""
    def __init__(self, mrp_url, mrp_token, preseed_file, preseed_name,
                 preseed_type, preseed_desc = '', preseed_knowngood = False,
                 preseed_public = False):
        self.url = mrp_url
        self.authhead = { 'Authorization': mrp_token }
        self.file = preseed_file
        self.name = preseed_name
        self.type = preseed_type
        self.id = -1
        self.desc = preseed_desc
        self.knowngood = preseed_knowngood
        self.public = preseed_public

    def _check_for_existence(self):
        url = urljoin(self.url, '/api/v1/preseed?show_all=true')
        r = requests.get(url, headers=self.authhead)
        if r.status_code != 200:
            raise ProvisionerError('Error fetching {}, HTTP {} {}'.format(url,
r.status_code, r.reason))

        for preseed in r.json():
            if preseed['name'] == self.name:
                self.id = preseed['id']
                return True

        return False

    def _get_preseed_from_file(self):
        json_preseed = {}

        f = open(self.file, 'r')
        contents = ''
        for line in f:
            contents += line
        json_preseed['content'] = contents
        json_preseed['name'] = self.name
        json_preseed['type'] = self.type
        json_preseed['public'] = self.public
        json_preseed['known_good'] = self.knowngood
        if (self.desc != ''):
            json_preseed['description'] = self.desc

        return json_preseed

    def upload_preseed(self):
        """Uploads preseed. Should check first that preseed doesn't exist, else
        it modifies preseed (separate function ?). Post to upload, Put to
        modify (+ id). Maybe implement a jinja2 syntax check ? But that should
        be done on mrp's side"""
        try:
            self._check_for_existence()
        except ProvisionerError as err:
            print(str(err))

        if(self.id != -1):
            self._modify_preseed()
        else:
            preseed = self._get_preseed_from_file()
            url = urljoin(self.url, '/api/v1/preseed')
            r = requests.post(url,
                              headers=self.authhead,data=json.dumps(preseed))
            if r.status_code != 201:
                raise ProvisionerError('Error posting preseed {}, HTTP {} {}'.format(self.name, r.status_code, r.reason))

    def _modify_preseed(self):
        if(self.id == -1):
            raise ProvisionerError('preseed ID is undefined, please use upload_preseed')
        url_id = '/api/v1/preseed/' + str(self.id)
        url = urljoin(self.url, url_id)
        preseed = self._get_preseed_from_file()
        r = requests.put(url, headers=self.authhead, data=json.dumps(preseed))
        if r.status_code != 200:
            raise ProvisionerError('Error putting preseed {} at ID {}, HTTP {} {}'.format(self.name, self.id, r.status_code, r.reason))

def run_module():
    module_args = dict(
        preseed_name = dict(type='str', required=True),
        preseed_file = dict(type='str', required=True),
        preseed_type = dict(type='str', required=True),
        preseed_description = dict(type='str', required=False),
        preseed_bknowngood = dict(type='bool', required=False),
        preseed_bpublic = dict(type='bool', required=False),
        mrp_url = dict(type='str', required=True),
        mrp_token = dict(type='str', required=True),
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

    uploader = PreseedUploader(module.params['mrp_url'],
    module.params['mrp_token'], module.params['preseed_file'],
    module.params['preseed_name'], module.params['preseed_type'],
    module.params['preseed_description'], module.params['preseed_bknowngood'],
    module.params['preseed_bpublic'])

    try:
        uploader.upload_preseed()
    except ProvisionerError as e:
        module.fail_json(msg=str(e), **result)

    result['json'] = { 'status': 'ok' }
    result['changed'] = True

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()

