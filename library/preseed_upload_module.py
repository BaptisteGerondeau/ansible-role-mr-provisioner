#!/usr/bin/env python3

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

from ansible.module_utils.basic import AnsibleModule
from mr_provisioner_machine_provision import ProvisionerError
from preseedupload import PreseedUploader


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
    module.params['pressed_desc'], module.params['preseed_knowngood'],
    module.params['preseed_bpublic'])

    try:
        uploader.upload_preseed()
    except ProvisionerError as e:
        module.fail_json(msg=str(e), **result)

