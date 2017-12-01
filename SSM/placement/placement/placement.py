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
from sonsmbase.smbase import sonSMbase

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("vCDN-ssm-placement")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class PlacementSSM(sonSMbase):

    def __init__(self):

        """
        :param specific_manager_type: specifies the type of specific manager that could be either fsm or ssm.
        :param service_name: the name of the service that this specific manager belongs to.
        :param function_name: the name of the function that this specific manager belongs to, will be null in SSM case
        :param specific_manager_name: the actual name of specific manager (e.g., scaling, placement)
        :param id_number: the specific manager id number which is used to distinguish between multiple SSM/FSM
        that are created for the same objective (e.g., scaling with algorithm 1 and 2)
        :param version: version
        :param description: description
        """
        self.specific_manager_type = 'ssm'
        self.service_name = 'vcdn'
        self.specific_manager_name = 'placement'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = "Placement SSM"

        super(self.__class__, self).__init__(specific_manager_type= self.specific_manager_type,
                                             service_name= self.service_name,
                                             specific_manager_name = self.specific_manager_name,
                                             id_number = self.id_number,
                                             version = self.version,
                                             description = self.description)


    def on_registration_ok(self):

        LOG.debug("Received registration ok event.")

        # For testing, here we set the service uuid.
        # In the actual scenario this should be set by SLM and SMR during the SSM instantiation.
        # if self.sfuuid == None:
        #self.sfuuid = '1234'

        # Register to placement topic.
        topic = 'placement.ssm.' + self.sfuuid

        self.manoconn.register_async_endpoint(self.on_place,topic= topic)

        LOG.info("Subscribed to {0}".format(topic))

    def on_place(self, ch, method, properties, payload):
        """
        This method organises the placement calculation, and
        provides the response for the SLM.
        """

        LOG.info("Placement started")
        message = yaml.load(payload)
        LOG.info('payload content => {0}'.format(message))
        topology = message['topology']
        nsd = message['nsd']
        functions = message['vnfds']
        nap = message['nap']

        mapping = self.placement_alg(nsd, functions, topology, nap)

        if mapping is None:
            LOG.info("The mapping calculation has failed.")
            message = {}
            message['error'] = 'Unable to perform placement.'
            message['status'] = 'ERROR'

        else:
            LOG.info("The mapping calculation has succeeded.")
            message = {}
            message['error'] = None
            message['status'] = "COMPLETED"
            message['mapping'] = mapping

        is_dict = isinstance(message, dict)
        LOG.info("Type Dict: " + str(is_dict))

        payload = yaml.dump(message)
        self.manoconn.notify('placement.ssm.' + self.sfuuid,
                             payload,
                             correlation_id=properties.correlation_id)

        return

    def placement_alg(self, nsd, functions, topology, nap):
        """
        This is the default placement algorithm that is used if the SLM
        is responsible to perform the placement
        """
        LOG.info("Mapping algorithm started.")
        mapping = {}


        if nap != {}:
            if 'ingresses' in nap.keys():
                ingress = nap['ingresses'][0]['location']
                ingress_ip_segments = nap['ingresses'][0]['nap'].split('.')

            if 'egresses' in nap.keys():
                egress = nap['egresses'][0]['location']
                egress_ip_segments = nap['egresses'][0]['nap'].split('.')


        # Find the sum of demands of vCC and vTC
        vtc_vcc_total_core = 0
        vtc_vcc_total_memory = 0



        for vnfd in functions:
            if vnfd['name'] == 'vtc-vnf' or vnfd['name'] == 'vcc-vnf':
                vtc_vcc_total_core += vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu']['vcpus']
                vtc_vcc_total_memory += vnfd['virtual_deployment_units'][0]['resource_requirements']['memory']['size']

        # Find the sum of demands of vCC and vTC

        vtu_total_core = 0
        vtu_total_memory = 0
        for vnfd in functions:
            if vnfd['name'] == 'vtu-vnf':
                vtu_total_core = vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu']['vcpus']
                vtu_total_memory = vnfd['virtual_deployment_units'][0]['resource_requirements']['memory']['size']

        if bool(nap):
            # Place vTC and vCC on the Egress PoP close to users and
            # place vTU on Ingress PoP close to the server
            for vnfd in functions:
                if 'ingresses' in nap.keys():
                    if vnfd['name'] == 'vtc-vnf' or vnfd['name'] == 'vcc-vnf':
                        LOG.info("Addressing ingress VNF.")
                        for vim in topology:
                            vim_ip_segments = vim['vim_endpoint'].split('.')
                            if vim_ip_segments[:-1] == ingress_ip_segments[:-1]:
                                LOG.info("Ingress requirements fulfilled, calculating resource capabilities.")
                                cpu_req = vtc_vcc_total_core <= (vim['core_total'] - vim['core_used'])
                                mem_req = vtc_vcc_total_memory <= (vim['memory_total'] - vim['memory_used'])
                                if cpu_req and mem_req:
                                    LOG.debug('VNF ' + vnfd['instance_uuid'] + ' mapped on VIM ' + vim['vim_uuid'])
                                    mapping[vnfd['instance_uuid']] = {}
                                    mapping[vnfd['instance_uuid']]['vim'] = vim['vim_uuid']
                                    vim['core_used'] = vim['core_used'] + \
                                                       vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu'][
                                                           'vcpus']
                                    vim['memory_used'] = vim['memory_used'] + \
                                                         vnfd['virtual_deployment_units'][0]['resource_requirements']['memory'][
                                                             'size']
                                    break

                if 'egresses' in nap.keys():
                    if vnfd['name'] == 'vtu-vnf':
                        LOG.info("Addressing egress VNF.")
                        for vim in topology:
                            vim_ip_segments = vim['vim_endpoint'].split('.')
                            LOG.info("vim segments: " + str(vim_ip_segments))
                            LOG.info("egress segments: " + str(egress_ip_segments))
                            LOG.info("Third egress segment: " + str(egress_ip_segments[2]))
                            if (vim_ip_segments[:-2] == egress_ip_segments[:-2]) and (egress_ip_segments[2] in ['0', '16']):
                                LOG.info("Egress requirements fulfilled, calculating resource capabilities.")
                                cpu_req = vtu_total_core <= (vim['core_total'] - vim['core_used'])
                                mem_req = vtu_total_memory <= (vim['memory_total'] - vim['memory_used'])

                                if cpu_req and mem_req:
                                    LOG.debug('VNF ' + vnfd['instance_uuid'] + ' mapped on VIM ' + vim['vim_uuid'])
                                    mapping[vnfd['instance_uuid']] = {}
                                    mapping[vnfd['instance_uuid']]['vim'] = vim['vim_uuid']
                                    vim['core_used'] = vim['core_used'] + \
                                                       vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu'][
                                                           'vcpus']
                                    vim['memory_used'] = vim['memory_used'] + \
                                                         vnfd['virtual_deployment_units'][0]['resource_requirements']['memory'][
                                                             'size']
                                    break

        if len(mapping) is not len(functions):

            for vnfd in functions:
                if vnfd['instance_uuid'] not in mapping.keys():
                    if vnfd['name'] == 'vtc-vnf' or vnfd['name'] == 'vcc-vnf':
                        for vim in topology:
                            cpu_req = vtc_vcc_total_core <= (vim['core_total'] - vim['core_used'])
                            mem_req = vtc_vcc_total_memory <= (vim['memory_total'] - vim['memory_used'])
                            if cpu_req and mem_req:
                                LOG.debug('VNF ' + vnfd['instance_uuid'] + ' mapped on VIM ' + vim['vim_uuid'])
                                mapping[vnfd['instance_uuid']] = {}
                                mapping[vnfd['instance_uuid']]['vim'] = vim['vim_uuid']
                                vim['core_used'] = vim['core_used'] + \
                                                   vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu'][
                                                       'vcpus']
                                vim['memory_used'] = vim['memory_used'] + \
                                                     vnfd['virtual_deployment_units'][0]['resource_requirements'][
                                                         'memory'][
                                                         'size']
                                break

                    if vnfd['name'] == 'vtu-vnf':
                        for vim in topology:
                            cpu_req = vtu_total_core <= (vim['core_total'] - vim['core_used'])
                            mem_req = vtu_total_memory <= (vim['memory_total'] - vim['memory_used'])

                            if cpu_req and mem_req:
                                LOG.debug('VNF ' + vnfd['instance_uuid'] + ' mapped on VIM ' + vim['vim_uuid'])
                                mapping[vnfd['instance_uuid']] = {}
                                mapping[vnfd['instance_uuid']]['vim'] = vim['vim_uuid']
                                vim['core_used'] = vim['core_used'] + \
                                                   vnfd['virtual_deployment_units'][0]['resource_requirements']['cpu'][
                                                       'vcpus']
                                vim['memory_used'] = vim['memory_used'] + \
                                                     vnfd['virtual_deployment_units'][0]['resource_requirements'][
                                                         'memory'][
                                                         'size']
                                break


        # Check if all VNFs have been mapped
        if len(mapping.keys()) == len(functions):
            LOG.info("Mapping succeeded: " + str(mapping))
            return mapping
        else:
            return None


def main():
    PlacementSSM()

if __name__ == '__main__':
    main()
