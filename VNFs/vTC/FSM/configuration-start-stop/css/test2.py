import sys
import logging
from ssh import Client

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("fsm-start-stop-configure-test")
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging-test").setLevel(logging.INFO)


if __name__ == "__main__":
    
    host_ip='10.100.32.231'
    user='ubuntu'
    pw='randompassword'
    

    
    ssh_client = Client(host_ip,user,pw,LOG)
    ssh_client.sendCommand("sudo sed -i '1515s/.*/\tip_hdr->daddr = 3592446989;/' /root/gowork/src/pfring_web_api/vtc/PF_RING/userland/examples/pfbridge.c")
    ssh_client.close()
