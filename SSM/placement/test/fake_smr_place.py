"""
Copyright (c) 2015 SONATA-NFV
ALL RIGHTS RESERVED.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
Neither the name of the SONATA-NFV [, ANY ADDITIONAL AFFILIATION]
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission.
This work has been performed in the framework of the SONATA project,
funded by the European Commission under Grant number 671517 through
the Horizon 2020 and 5G-PPP programmes. The authors would like to
acknowledge the contributions of their colleagues of the SONATA
partner consortium (www.sonata-nfv.eu).
"""

import logging
import yaml
import time
from sonmanobase import messaging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("son-mano-fakesmr")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class fakesmr(object):

    def __init__(self):

        self.name = 'fake-smr'
        self.version = '0.1-dev'
        self.description = 'description'

        LOG.info("Start SMR:...")

        # create and initialize broker connection
        self.manoconn = messaging.ManoBrokerRequestResponseConnection(self.name)

        #elf.end = False

        #self.publish_nsd()

        self.declare_subscriptions()

    def declare_subscriptions(self):
        """
        Declare topics to which we want to listen and define callback methods.
        """
        self.manoconn.register_async_endpoint(self.on_register_receive, 'specific.manager.registry.ssm.registration')

    def on_register_receive(self,ch, method, properties, payload):

        # go into infinity loop
        message = yaml.load(payload)

        response = {
            "status": "registered",
            "specific_manager_type": message['specific_manager_type'],
            "service_name": message['service_name'],
            "function_name": message['function_name'],
            "specific_manager_id": message['specific_manager_id'],
            "version": message['version'],
            "description": message['description'],
            "uuid": '23345',
            "sfuuid": None,
            "error": None
        }

        return yaml.dump(response)


def main():
    fakesmr()


if __name__ == '__main__':
    main()