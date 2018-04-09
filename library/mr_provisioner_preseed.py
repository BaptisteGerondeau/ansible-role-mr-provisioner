#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: mr-provisioner-preseed
short_description: Manage preseed files in Mr. Provisioner
description:
    Implemented:
        - Upload new preseed
        - Discover existing preseeds by a given name.
    Not implemented:
        - modifying existing preseed
        - deleting existing preseed
options:
    name:
        description:
            - Name of the preseed
        required: true
    description:
        description:
            - Description of the preseed
        required: false
    path:
        description: Local file path to preseed file.
        required: true
    url:
        description: url to provisioner instance in the form of http://172.27.80.1:5000/
        required: true
    token:
        description: Mr. Provisioner auth token
        required: true
    known_good:
        description: Mark known good. Default false.
        required: false
    public:
        description: Mark public. Default false.
        required: false
author:
    - Jorge Niedbalski <jorge.niedbalski@linaro.org>
    - Baptiste Gerondeau <baptiste.gerondeau@linaro.org>
'''

EXAMPLES = '''
# Upload a preseed file to a MrProvisioner install.
- name: moonshot-generic-preseed
  path: ./preseeds/moonshot-generic.preseed.txt
  url: http://172.27.80.1:5000/
  token: "{{ provisioner_auth_token }}"

# Uses existing file from MrProvisioner
- name: test_preseed
  path: /dev/null
  url: http://172.0.0.1:5000
  token: "{{ fancy_token }}"
'''

RETURN = '''
  id: auto-assigned preseed id
  description: preseed description
  name: preseed name
  type: user defined type (default: preseed)
  user: User that owns the preseed
  known_good: true/false
  public: true/false
'''

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
        res = {}
        try:
            exists = self._check_for_existence()
        except ProvisionerError as e:
            res['error'] = str(e)
            return res

        if not exists and self.file == '/dev/null':
            res['error'] = 'Preseed does not exist and file not given'
            return res

        if(self.id != -1 and self.file != '/dev/null'):     #Exists and file given
            try:
                res = self._modify_preseed()
            except ProvisionerError as e:
                res['error'] = str(e)
            return res
        elif (self.file != '/dev/null'):        #Doesn't exist and file given
            preseed = self._get_preseed_from_file()
            url = urljoin(self.url, '/api/v1/preseed')
            r = requests.post(url,
                              headers=self.authhead,data=json.dumps(preseed))
            if r.status_code != 201:
                raise ProvisionerError('Error posting preseed {}, \
                                       HTTP {} {}'.format(self.name, r.status_code, r.reason))
            else:
                return r.json()
        else:       #Exists and file not given, is it useful fetching contents?
            return res

    def _modify_preseed(self):
        if(self.id == -1):
            raise ProvisionerError('preseed ID is undefined, please use upload_preseed')
        url_id = '/api/v1/preseed/' + str(self.id)
        url = urljoin(self.url, url_id)
        preseed = self._get_preseed_from_file()
        r = requests.put(url, headers=self.authhead, data=json.dumps(preseed))
        if r.status_code != 200:
            raise ProvisionerError('Error putting preseed {} at ID {}, \
                                   HTTP {} {}'.format(self.name, self.id, r.status_code, r.reason))
        else:
            return r.json()

def run_module():
    module_args = dict(
        description = dict(type='str', required=False, default=''),
        name = dict(type='str', required=True),
        type = dict(type='str', required=False, default='preseed'),
        path = dict(type='str', required=False, default='/dev/null'),
        url = dict(type='str', required=True),
        token = dict(type='str', required=True),
        known_good = dict(type='bool', required=False, default=False),
        public = dict(type='bool', required=False, default=False),
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

    uploader = PreseedUploader(module.params['url'],
    module.params['token'], module.params['path'],
    module.params['name'], module.params['type'],
    module.params['description'], module.params['known_good'],
    module.params['public'])

    try:
        res = uploader.upload_preseed()
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

