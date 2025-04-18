# -*- coding: utf-8 -*-
#
# Copyright: (c) 2018, F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import pytest
import sys

if sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip("F5 Ansible modules require Python >= 2.7")

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.f5networks.f5_modules.plugins.modules.bigip_profile_server_ssl import (
    ApiParameters, ModuleParameters, ModuleManager, ArgumentSpec
)
from ansible_collections.f5networks.f5_modules.tests.unit.compat import unittest
from ansible_collections.f5networks.f5_modules.tests.unit.compat.mock import Mock, patch
from ansible_collections.f5networks.f5_modules.tests.unit.modules.utils import set_module_args


fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures')
fixture_data = {}


def load_fixture(name):
    path = os.path.join(fixture_path, name)

    if path in fixture_data:
        return fixture_data[path]

    with open(path) as f:
        data = f.read()

    try:
        data = json.loads(data)
    except Exception:
        pass

    fixture_data[path] = data
    return data


class TestParameters(unittest.TestCase):
    def test_module_parameters(self):
        args = dict(
            name='foo',
            server_name='foo.bar.com',
            secure_renegotiation='require',
            passphrase="F5site02"
        )

        p = ModuleParameters(params=args)
        assert p.name == 'foo'
        assert p.server_name == 'foo.bar.com'
        assert p.secure_renegotiation == 'require'
        assert p.passphrase == 'F5site02'

    def test_module_parameters_parent_none(self):
        args = dict(
            name='foo',
            server_name='foo.bar.com',
            secure_renegotiation='require',
            passphrase="F5site02",
            parent=None
        )

        p = ModuleParameters(params=args)
        assert p.name == 'foo'
        assert p.server_name == 'foo.bar.com'
        assert p.secure_renegotiation == 'require'
        assert p.passphrase == 'F5site02'
        assert p.parent is None

    def test_module_parameters_parent_none_str(self):
        args = dict(
            name='foo',
            server_name='foo.bar.com',
            secure_renegotiation='require',
            passphrase="F5site02",
            parent="None"
        )

        p = ModuleParameters(params=args)
        assert p.name == 'foo'
        assert p.server_name == 'foo.bar.com'
        assert p.secure_renegotiation == 'require'
        assert p.passphrase == 'F5site02'
        assert p.parent == "None"

    def test_module_parameters_parent_none_str(self):
        args = dict(
            name='foo',
            server_name='foo.bar.com',
            secure_renegotiation='require',
            passphrase="F5site02",
            parent="foo"
        )

        p = ModuleParameters(params=args)
        assert p.name == 'foo'
        assert p.server_name == 'foo.bar.com'
        assert p.secure_renegotiation == 'require'
        assert p.passphrase == 'F5site02'
        assert p.parent == '/Common/foo'

    def test_api_parameters(self):
        args = load_fixture('load_ltm_profile_serverssl_1.json')
        p = ApiParameters(params=args)
        assert p.name == 'asda'
        assert p.server_name is None


class TestManager(unittest.TestCase):
    def setUp(self):
        self.spec = ArgumentSpec()
        self.p2 = patch('ansible_collections.f5networks.f5_modules.plugins.modules.bigip_profile_server_ssl.tmos_version')
        self.p3 = patch('ansible_collections.f5networks.f5_modules.plugins.modules.bigip_profile_server_ssl.send_teem')
        self.m2 = self.p2.start()
        self.m2.return_value = '14.1.0'
        self.m3 = self.p3.start()
        self.m3.return_value = True

    def tearDown(self):
        self.p2.stop()
        self.p3.stop()

    def test_create(self, *args):
        # Configure the arguments that would be sent to the Ansible module
        set_module_args(dict(
            name='foo',
            server_name='foo.bar.com',
            provider=dict(
                server='localhost',
                password='password',
                user='admin'
            )
        ))

        module = AnsibleModule(
            argument_spec=self.spec.argument_spec,
            supports_check_mode=self.spec.supports_check_mode,
            required_together=self.spec.required_together
        )
        mm = ModuleManager(module=module)

        # Override methods to force specific logic in the module to happen
        mm.exists = Mock(return_value=False)
        mm.create_on_device = Mock(return_value=True)

        results = mm.exec_module()

        assert results['changed'] is True
