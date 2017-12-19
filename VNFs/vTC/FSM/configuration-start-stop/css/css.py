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
import requests
import time
import configparser
from sonsmbase.smbase import sonSMbase
from .ssh import Client
import netaddr


def reverse(ip):
        if len(ip) <= 1:
                return ip
        l = ip.split('.')
        return '.'.join(l[::-1])

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("fsm-start-stop-configure")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class CssFSM(sonSMbase):
    
    hostIp = 'none'
    def __init__(self):

        """
        :param specific_manager_type: specifies the type of specific manager
        that could be either fsm or ssm.
        :param service_name: the name of the service that this specific manager
        belongs to.
        :param function_name: the name of the function that this specific
        manager belongs to, will be null in SSM case
        :param specific_manager_name: the actual name of specific manager
        (e.g., scaling, placement)
        :param id_number: the specific manager id number which is used to
        distinguish between multiple SSM/FSM that are created for the same
        objective (e.g., scaling with algorithm 1 and 2)
        :param version: version
        :param description: description
        """

        self.specific_manager_type = 'fsm'
        self.service_name = 'vcdn'
        self.function_name = 'vtc'
        self.specific_manager_name = 'css'
        self.id_number = '1'
        self.version = 'v0.1'
        self.description = "An FSM that subscribes to start, stop and configuration topic"

        super(self.__class__, self).__init__(specific_manager_type=self.specific_manager_type,
                                             service_name=self.service_name,
                                             function_name=self.function_name,
                                             specific_manager_name=self.specific_manager_name,
                                             id_number=self.id_number,
                                             version=self.version,
                                             description=self.description)

    def on_registration_ok(self):

        # The fsm registration was successful
        LOG.debug("Received registration ok event.")

        # send the status to the SMR
        status = 'Subscribed, waiting for alert message'
        message = {'name': self.specific_manager_id,
                   'status': status}
        self.manoconn.publish(topic='specific.manager.registry.ssm.status',
                              message=yaml.dump(message))

        # Subscribing to the topics that the fsm needs to listen on
        topic = "generic.fsm." + str(self.sfuuid)
        self.manoconn.subscribe(self.message_received, topic)
        LOG.info("Subscribed to " + topic + " topic.")

    def message_received(self, ch, method, props, payload):
        """
        This method handles received messages
        """

        # Decode the content of the message
        request = yaml.load(payload)

        # Don't trigger on non-request messages
        if "fsm_type" not in request.keys():
            LOG.info("Received a non-request message, ignoring...")
            return

        # Create the response
        response = None

        # the 'fsm_type' field in the content indicates for which type of
        # fsm this message is intended. In this case, this FSM functions as
        # start, stop and configure FSM
        if str(request["fsm_type"]) == "start":
            LOG.info("Start event received: " + str(request["content"]))
            response = self.start_event(request["content"])

        if str(request["fsm_type"]) == "stop":
            LOG.info("Stop event received: " + str(request["content"]))
            response = self.stop_event(request["content"])

        if str(request["fsm_type"]) == "configure":
            LOG.info("Config event received: " + str(request["content"]))
            response = self.configure_event(request["content"])

        if str(request["fsm_type"]) == "scale":
            LOG.info("Scale event received: " + str(request["content"]))
            response = self.scale_event(request["content"])

        # If a response message was generated, send it back to the FLM
        if response is not None:
            # Generated response for the FLM
            LOG.info("Response to request generated:" + str(response))
            topic = "generic.fsm." + str(self.sfuuid)
            corr_id = props.correlation_id
            self.manoconn.notify(topic,
                                 yaml.dump(response),
                                 correlation_id=corr_id)
            return

        # If response is None:
        LOG.info("Request received for other type of FSM, ignoring...")

    def start_event(self, content):
        """
        This method handles a start event.
        """
        LOG.info("Performing life cycle start event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the start logic. The content is a dictionary that contains
        # the required data
        # TODO = check vm_image if correct
        vm_image = "vtc-vnf"
        vnfr = content["vnfr"]
        if (content['vnfd']['name']) == vm_image:
            mgmt_ip = content['vnfr']['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']

        
        if not mgmt_ip:
            LOG.error("Couldn't obtain IP address from VNFR")
            return
        self.hostIp = mgmt_ip
        
        # Post request
        url = "http://"+mgmt_ip+":8080/startPFbridge"
        querystring = {"jsonIn":"{\"netIN\":\"eth1\",\"netOUT\":\"eth2\"}"}

        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'accept': "application/json",
            }

        number_of_retries = 20
        for i in range(number_of_retries):
            LOG.info("Attempting new post request: attempt " + str(i + 1))
            try:
                response = requests.request("POST", url, headers=headers, params=querystring, timeout=5.0)
                LOG.info("Response on post request: " + str(response.text))
                LOG.info("Status code of response " + str(response.status_code))
                break
            except:
                LOG.info("Request timed out, retrying")
                time.sleep(15)

        #Configure montoring probe
        #if sp_ip:
        ssh_client = Client(mgmt_ip,'ubuntu','randompassword',LOG)
        sp_ip = ssh_client.sendCommand("echo $SSH_CLIENT | awk '{ print $1}'")
        if not self.validIP(sp_ip):
            LOG.error("Couldn't obtain SP IP address from ssh_client. Monitoring configuration aborted")
            sp_ip = '10.30.0.112' 
        LOG.info('Mon Config: Create new conf file')
        self.createConf(sp_ip, 4, 'vtc-vnf')
        ssh_client.sendFile('node.conf')
        ssh_client.sendCommand('ls /tmp/')
        ssh_client.sendCommand('sudo mv /tmp/node.conf /opt/Monitoring/node.conf')
        ssh_client.sendCommand('sudo service mon-probe restart')
        LOG.info('Mon Config: Completed')
        LOG.info("Configuring vTC pfbridge and datasources")
        ssh_client.sendCommand('sudo /root/gowork/src/pfring_web_api/vtc/PF_RING/userland/examples/pfbridge -a eth1 -b eth2 -d http://'+mgmt_ip+':8086 &')
        LOG.info("Started pfbridge (if it was not)")
        ssh_client.sendCommand("sed -i 's/10.100.32.231/'"+mgmt_ip+"'/g' /root/gowork/src/vtc_dashboard/static/json/grafana_init_datasources.json")
        LOG.info("Updating datasource")
        ssh_client.sendCommand("sudo curl -X PUT --connect-timeout 60 --data-binary @/root/gowork/src/vtc_dashboard/static/json/grafana_init_datasources.json -H 'Content-Type:application/json' -H 'Accept: application/json' http://admin:admin@"+mgmt_ip+":3000/api/datasources/15")
        ssh_client.close()
        LOG.info('Configurations completed')

        #else:
         #   LOG.error("Couldn't obtain SP IP address. Monitoring configuration aborted")


        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def stop_event(self, content):
        """
        This method handles a stop event.
        """
        LOG.info("Performing life cycle stop event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the stop logic. The content is a dictionary that contains
        # the required data
        # TODO = check vm_image if correct
        vm_image = "vtc-vnf"
        vnfr = content["vnfr"]
        if (content['vnfd']['name']) == vm_image:
            mgmt_ip = content['vnfr']['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']
        if not mgmt_ip:
            LOG.error("Couldn't obtain IP address from VNFR")
            return
        
        url = "http://"+mgmt_ip+":8080/stopPFbridge"

        headers = {
            'accept': "application/json",
            }
        response = requests.request("POST", url, headers=headers)
        LOG.info(response.text)

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def configure_event(self, content):
        """
        This method handles a configure event.
        """
        LOG.info("Performing life cycle configure event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the configure logic. The content is a dictionary that
        # contains the required data

        nsr = content['nsr']
        vnfrs = content['vnfrs']
        for vnfr in vnfrs:
            if (vnfr['virtual_deployment_units'][0]['vm_image']) == 'http://files.sonata-nfv.eu/son-vcdn-pilot/vtu-vnf/sonata-vtu.qcow2':
                mgmt_ip = vnfr['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['address']
                mac = vnfr['virtual_deployment_units'][0]['vnfc_instance'] [0]['connection_points'][0]['interface']['hardware_address']
                LOG.info("vTU's management IP retrieved: "+mgmt_ip+" and the mac:"+mac)

        try:
            iprev = reverse(mgmt_ip)
            LOG.info("Got the reverse IP to be turned to integer: "+iprev)
            ipInt = int(netaddr.IPAddress(iprev))
            LOG.info("Got the Integer from the IP: "+str(ipInt))
        except Exception as err: 
            LOG.error("Got an exception: "+str(err))
            return

        LOG.info("Sending ssh command to alter line in vTC with vTU IP as integer")    
        ssh_client = Client(self.hostIp,'ubuntu','randompassword',LOG)
        ssh_client.sendCommand("sudo sed -i '1515s/.*/\tip_hdr->daddr = %s;/' /root/gowork/src/pfring_web_api/vtc/PF_RING/userland/examples/pfbridge.c" %ipInt)
        ssh_client.sendCommand("sudo make -C /root/gowork/src/pfring_web_api/vtc/PF_RING/userland/examples")
        ssh_client.close()
        
        #Stopping PFBRidge
        url = "http://"+self.hostIp+":8080/stopPFbridge"
        headers = {
            'accept': "application/json",
            }
        response = requests.request("POST", url, headers=headers)
        LOG.info("Response on post request: " + str(response.text))
        LOG.info("Status code of response " + str(response.status_code))
        
        #Starting PFBridge agan
        url = "http://"+self.hostIp+":8080/startPFbridge"
        querystring = {"jsonIn":"{\"netIN\":\"eth1\",\"netOUT\":\"eth2\"}"}
        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'accept': "application/json",
            }

        response = requests.request("POST", url, headers=headers, params=querystring, timeout=5.0)
        LOG.info("Response on post request: " + str(response.text))
        LOG.info("Status code of response " + str(response.status_code))

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'
    
        # TODO: complete the response

        return response

    def scale_event(self, content):
        """
        This method handles a scale event.
        """
        LOG.info("Performing life cycle scale event")
        LOG.info("content: " + str(content.keys()))
        # TODO: Add the configure logic. The content is a dictionary that
        # contains the required data

        # Create a response for the FLM
        response = {}
        response['status'] = 'COMPLETED'

        # TODO: complete the response

        return response

    def createConf(self, pw_ip, interval, name):

        config = configparser.RawConfigParser()
        config.add_section('vm_node')
        config.add_section('Prometheus')
        config.set('vm_node', 'node_name', name)
        config.set('vm_node', 'post_freq', interval)
        config.set('Prometheus', 'server_url', 'http://'+pw_ip+':9091/metrics')
    
    
        with open('node.conf', 'w') as configfile:    # save
            config.write(configfile)
    
        f = open('node.conf', 'r')
        LOG.debug('Mon Config-> '+"\n"+f.read())
        f.close()

    def validIP(self, address):
        parts = str(address).split(".")
        if len(parts) != 4:
            return False
        for item in parts:
            try:
                if not 0 <= int(item) <= 255:
                    return False
            except (ValueError) as  exception:
                return False
        return True

def main():
    CssFSM()

if __name__ == '__main__':
    main()
