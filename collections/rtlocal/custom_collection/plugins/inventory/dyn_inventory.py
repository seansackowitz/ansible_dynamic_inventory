import csv, json
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from requests.models import Response

DOCUMENTATION = '''
    name: dyn_inventory
    plugin_type: inventory
    short_description: Fakes getting an Ansible inventory from a web server/API
    description: Fakes getting an Ansible inventory from a web server/API
    extends_documentation_fragment:
      - constructed
    options:
      cc_username:
        description: Username for fake api
        required: true
        env:
          - name: CC_USERNAME
      cc_password:
        description: Password for fake api
        required: true
        env:
          - name: CC_PASSWORD
      cc_host:
        description: api url for fake api
        required: true
        env:
          - name: CC_HOST
      keyed_groups:
        description: Add hosts to groups based on the values of a variable.
        required: false
        type: list
        default: []
'''

def _do_api_request(self):
    '''
    Mock making the api call, by returning a valid requests Response
    You would make a proper api call here following https://pypi.org/project/requests/
    '''
    r = Response()
    r.status_code = 200
    r._content = str.encode('''{
            "devices": [
                {
                    "hostname": "SATL01.mycompany.com",
                    "softwareType": "IOS-XE",
                    "location": "ATL",
                    "mgmtAddress": "10.30.1.1",
                    "deviceType": "switch"
                },
                {
                    "hostname": "RATL01.mycompany.com",
                    "softwareType": "IOS",
                    "location": "ATL",
                    "mgmtAddress": "10.30.2.1",
                    "deviceType": "router"
                },
                {
                    "hostname": "SCLT01.mycompany.com",
                    "softwareType": "IOS-XE",
                    "location": "CLT",
                    "mgmtAddress": "10.32.1.1",
                    "deviceType": "switch"
                },
                {
                    "hostname": "RCLT01.mycompany.com",
                    "softwareType": "IOS",
                    "location": "CLT",
                    "mgmtAddress": "10.32.2.1",
                    "deviceType": "switch"
                },
                {
                    "hostname": "RRDU01.mycompany.com",
                    "softwareType": "NX-OS",
                    "location": "RDU",
                    "mgmtAddress": "10.33.2.1",
                    "deviceType": "router"
                }
            ]
        }
        ''')
    return r

def _populate_from_api(self):
    '''
    Make simulated api request, and parse results
    '''
    results = _do_api_request(self).json()
    print(self.get_option("keyed_groups"))
    for device in results['devices']:
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

class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = 'rtlocal.custom_collection.dyn_inventory'

    def verify_file(self, path):
        # return true/false if this is possibly a valid file for this plugin to consume
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('dyn_inventory.yaml', 'dyn_inventory.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        # Return dynamic inventory from source
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        config = self._read_config_data(path)
        self._consume_options(config)
        cc_username = self.get_option('cc_username')
        cc_password = self.get_option('cc_password')
        cc_host = self.get_option('cc_host')

        results = _populate_from_api(self)
