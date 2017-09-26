import sys
import configparser
import logging
from ssh import Client

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("fsm-start-stop-configure-test")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging-test").setLevel(logging.INFO)

def createConf(pw_ip, interval, name):

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


if __name__ == "__main__":
    
    host_ip='10.100.32.231'
    user='ubuntu'
    pw='randompassword'
    
    
    LOG.info('Mon Config: Create new conf file')
    createConf('sp.int3.sonata-nfv.eu', 4, 'vtc-nfv')
    
    ssh_client = Client(host_ip,user,pw,LOG)
    ssh_client.sendFile('node.conf')
    ssh_client.sendCommand('ls /tmp/')
    ssh_client.sendCommand('sudo mv /tmp/node.conf /opt/Monitoring/node.conf')
    ssh_client.sendCommand('sudo service mon-probe restart')
    ssh_client.close()
