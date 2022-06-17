import os
import argparse
import json
import time
from config.config import Config
from query.query import Query
from parser.parser import Parser
from request.request import Request
from threading import Thread
from paramiko import SSHClient, AutoAddPolicy



authentication_periode = 3600 #one hour = 3600 seconds

TOKEN = ''

client = SSHClient()
vm = SSHClient()
parser = Parser()
deviceList = []
query_dictionary = {}
jsonDict = {}
# list of commands that will be run for each node on network
commandList = ['show runningconfiguration all | grep -A 11 -i metadata', 'show arp', 'show ip route', 'show acl table', 'show acl rule', 'show lldp table', 'show vlan config',
               'vtysh -c "show interface"', 'show ip bgp neighbors']
headerList = ['metadata', 'arp', 'ipRoute', 'aclTable', 'aclRule', 'lldp', 'vlan', 'interface', 'bgp']
def loadSSH():
    # load host ssh keys
    client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
    # known_hosts policy
    client.set_missing_host_key_policy(AutoAddPolicy())

def collectData():
    if script_config['simulation']:#if we will use simulation
        # read config file and foreach host create connection
        
        vm.set_missing_host_key_policy(AutoAddPolicy())
        try:
            vm.connect(hostname = cfg.conf_file_contents['SIMULATION']['hostname'],
                port = int(cfg.conf_file_contents['SIMULATION']['port']),
                username = cfg.conf_file_contents['SIMULATION']['username'],
                password=cfg.conf_file_contents['SIMULATION']['password'],
                key_filename=cfg.conf_file_contents['SIMULATION']['key_filename'])
          
        except:
            print("Connection Error to simulator")
            return 0
            
        #
        
    else:
        vmchannel = None

    for device in json.loads(cfg.conf_file_contents['TARGETS']['devices']):
        vmtransport = vm.get_transport()
        dest_addr = (device, 22) #edited#
        local_addr = ('localhost', 22) #edited#
        vmchannel = vmtransport.open_channel("direct-tcpip", dest_addr, local_addr)
        try:
            client.connect(
                device,
                username=cfg.conf_file_contents['AUTH']['username'],
                password=cfg.conf_file_contents['AUTH']['password'],
                sock=vmchannel)
        
        except:
            print("Error in connection to device", device)
            break;
        
        deviceList.append(device)
        for i in commandList:
            current_query = Query(device, i)
            current_query.send_query(client)
            query_dictionary[current_query.device + '.' + current_query.cmd] = current_query
        print("Done for device: ", device)
    client.close()
    vm.close()

def configNetwork():
    jsonConfigFile = open('jsonConfigFile.json', 'r')
    jsonConfigData = json.load(jsonConfigFile)
    jsonConfigFile.close()
    for device in json.loads(cfg.conf_file_contents['TARGETS']['devices']):
        if (device in jsonConfigData):
            #connecting to the device with ssh
            print("connecting to ",device,"...")
            client.connect(
                device,
                username=cfg.conf_file_contents['AUTH']['username'],
                password=cfg.conf_file_contents['AUTH']['password']
            )
            print("ssh client connected to ",device)
            #open sftp session to get and put files from and to the remote device
            ftp_client=client.open_sftp()
            with open('config.json', 'w') as outfile:
                json.dump(jsonConfigData[device], outfile,indent=4)
            outfile.close()
            ftp_client.put('config.json','config.json')
            #create back-up config
            cmd = "sudo cp /etc/sonic/config_db.json /etc/sonic/config_db.json.bk"
            exe_cmd(client,cmd)
            status = 0
            cmd = "sonic-cfggen -j config.json"
            if exe_cmd(client,cmd)!=0:
                status =1
                print("Error in json format ")
            cmd = "sudo config load config.json -y"
            if exe_cmd(client,cmd)!=0:
                status = 1
                print("Error in loading config from file ")
            cmd = "sudo config save -y"
            if exe_cmd(client,cmd)!=0:
                status = 1
                print("Error in saving config ")
            if status == 0:
                print(device," Configured successfully")
            else:
                print(device," Configuration not successful ... backup of the old configuration")
                cmd = "sudo cp /etc/sonic/config_db.json.bk /etc/sonic/config_db.json"
                exe_cmd(client,cmd)
                cmd = "sudo config reload -y"
                exe_cmd(client,cmd)
            client.close()

def jsonParse():
    outputDict = {}
    n = 0
    # parsing data into JSON
    for i in query_dictionary:
        result = parser.parse_query_result(query_dictionary[i])
        outputDict[headerList[n % len(headerList)]] = result
        if ((n+1) % len(headerList)) == 0:
            jsonDict[deviceList[int(n / len(headerList))]] = outputDict
            outputDict = {}
        n += 1
    json_network = json.dumps(jsonDict)
    # saving JSON output to a JSON file
    jsonFile = open("data.json", "w+")
    jsonFile.write(json_network)
    jsonFile.close()
def jsonSend(token):
    filename = 'data.json'
    print("uploading JSON file to controller")
    current_request = Request()
    url = cfg.controller_url + "/api/dt/running/state"
    try:
        response = current_request.postRequest(url, filename, token)
        return response
    except:
        print("An exception during posting config file to the controller")
        return ""

    

def controllerAuthentication(authentication_periode):
    global TOKEN
    while True:
        #update TOKEN EVERY PERIODE
        current_request = Request()
        data = {
            'username': cfg.conf_file_contents['CONTROLLER_AUTH']['username'],
            'password': cfg.conf_file_contents['CONTROLLER_AUTH']['password']
        }
        url = cfg.controller_url + "/api/login/user"
        try:
            response = current_request.postRequestJson(url,data)
            print(response.json())
            TOKEN = response.json()['token']
        except:    
            print("An exception  during Authentification")
        
        time.sleep(authentication_periode)

def sendConfig(repeat_timer):
    print("token is",TOKEN)
    if(repeat_timer == None):
        collectData()
        jsonParse()
        jsonSend(TOKEN)
    else:
        while(True):
            collectData()
            jsonParse()
            print(jsonSend(TOKEN))
            time.sleep(int(repeat_timer))

def exe_cmd(client,cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    output = ''
    status = 0
    for line in stdout.readlines():
        output += line
    for line in stderr.readlines():
        status=1
        output += line
    return status



if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(description= "proxy service to collect datad fro network and configuring the network",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter )
    args_parser.add_argument("-s", "--simulation", action="store_true", help="Simulation mode")
    args = args_parser.parse_args()
    script_config = vars(args)
    cfg = Config()
    loadSSH()
    print(cfg.conf_file_contents['AUTH']['username'])
    #thread to do authentification and update token every periode = authentication_periode
    Thread(target=controllerAuthentication, args=(authentication_periode,)).start()
    #thread to send current conf to the controller every periode = cfg.repeat_timer, if none send once
    time.sleep(2)
    print("the tokan is :", TOKEN)
    Thread(target=sendConfig, args=(cfg.repeat_timer,)).start()
    #load ssh keys and set up known_hosts
    

            