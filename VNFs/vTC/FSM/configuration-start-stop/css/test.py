import paramiko, sys
import ConfigParser

def createConf(pw_ip, interval, name):

    config = ConfigParser.RawConfigParser()
    config.add_section('vm_node')
    config.add_section('Prometheus')
    config.set('vm_node', 'node_name', name)
    config.set('vm_node', 'post_freq', interval)
    config.set('Prometheus', 'server_url', 'http://'+pw_ip+':9091/metrics')
    
    with open('node.conf', 'w') as configfile:    # save
        config.write(configfile)


if __name__ == "__main__":
    
    host_ip='10.100.32.231'
    user='ubuntu'
    pw='randompassword'
    
    
    createConf('sp.int3.sonata-nfv.eu', 4, 'vtc-nfv')
    
    ssh = paramiko.SSHClient()
    #ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host_ip, username=user, password=pw)
    sftp = ssh.open_sftp()
    sftp.put('node.conf', '/tmp/node.conf')
    sftp.close()
    ssh.exec_command("sudo mv /tmp/node.conf /opt/Monitoring/node.conf")
    ssh.exec_command("sudo service mon-probe restart")
    #out=stdout.readlines()
    #print(stdin.readlines())
    #print(stdout.readlines())
    #print(stderr.readlines())
    ssh.close()
