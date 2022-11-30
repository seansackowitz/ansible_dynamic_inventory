from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible_collections.cisco.dnac.plugins.plugin_utils.dnac import (
    DNACSDK,
    dnac_argument_spec,
)

DOCUMENTATION = '''
    name: dnac_inventory
    plugin_type: inventory
    short_description: Fakes getting an Ansible inventory from a web server/API
    description: Fakes getting an Ansible inventory from a web server/API
    extends_documentation_fragment:
      - constructed
      - cisco.dnac.module_info
    options:
      keyed_groups:
        description: Add hosts to groups based on the values of a variable.
        required: false
        type: list
        default: []
'''

def _populate_from_api(self, dnac):
    i = 0

    while True:
        results = dnac.exec(
            family="devices",
            function='get_device_list',
            params=dict(
                offset=i*500,
                limit=500,
                family=[
                    "Switches and Hubs",
                    "Routers"
                ]
            ),
        )
        for device in results['dnac_response']['response']:
            hostname = device['hostname']
            self.inventory.add_host(hostname)

            # Add variables to host
            for k, v in device.items():
                k = self._sanitize_group_name(k)
                self.inventory.set_variable(hostname, k, v)
            
            self._set_composite_vars(self.get_option("compose"), device, hostname, strict=False)
            # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
            self._add_host_to_composed_groups(self.get_option("groups"), device, hostname, strict=False)

            # Add host to groups from keys, and create group if needed
            self._add_host_to_keyed_groups(self.get_option("keyed_groups"), device, hostname, strict=False)
        if len(results['dnac_response']['response']) == 0:
            break

class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = 'rtlocal.custom_collection.dnac_inventory'

    def verify_file(self, path):
        # return true/false if this is possibly a valid file for this plugin to consume
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('dnac_inventory.yaml', 'dnac_inventory.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        # Return dynamic inventory from source
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        config = self._read_config_data(path)
        self._consume_options(config)

        args = {}

        args['dnac_host'] = self.get_option('dnac_host')
        args['dnac_port'] = self.get_option('dnac_port')
        args['dnac_username'] = self.get_option('dnac_username')
        args['dnac_password'] = self.get_option('dnac_password')
        args['dnac_verify'] = self.get_option('dnac_verify')
        args['dnac_version'] = self.get_option('dnac_version')
        args['dnac_debug'] = self.get_option('dnac_debug')
        args['validate_response_schema'] = self.get_option('validate_response_schema')

        dnac = DNACSDK(params=args)

        results = _populate_from_api(self, dnac)