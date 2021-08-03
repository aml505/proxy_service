import concurrent
import os
import json
from concurrent.futures import ThreadPoolExecutor
from paramiko import SSHClient, AutoAddPolicy
from config.config import Config
from query.query import Query
from parser.parser import Parser
import collections
import requests

cfg = Config()
client = SSHClient()
parser = Parser()
deviceList = []
query_dictionary = {}
outputDict = {}
jsonDict = {}
n = 0

# list of commands that will be run for each node on network
commandList = ['show arp', 'show ip route', 'show acl table', 'show acl rule', 'show lldp table', 'show vlan config',
               'vtysh -c "show interface"', 'show ip bgp neighbors']
headerList = ['arp', 'ipRoute', 'aclTable', 'aclRule', 'lldp', 'vlan', 'interface', 'bgp']

# load host ssh keys
client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))

# known_hosts policy
client.set_missing_host_key_policy(AutoAddPolicy())

# read config file and foreach host create connection
for device in json.loads(cfg.conf_file_contents['TARGETS']['devices']):
    client.connect(
        device,
        username=cfg.conf_file_contents['AUTH']['username'],
        password=cfg.conf_file_contents['AUTH']['password'])
    deviceList.append(device)
    for i in commandList:
        current_query = Query(device, i)
        current_query.send_query(client)
        query_dictionary[current_query.device + '.' + current_query.cmd] = current_query
client.close()

for i in query_dictionary:
    result = parser.parse_query_result(query_dictionary[i])
    outputDict[headerList[n % len(headerList)]] = result
    if ((n+1) % len(headerList)) == 0:
        jsonDict[deviceList[int(n / len(headerList))]] = outputDict
        outputDict = {}
    n += 1
json_network = json.dumps(jsonDict)

# saving json output to a json file
jsonFile = open("data.json", "w+")
jsonFile.write(json_network)


# sending the json file to emulated controller
url = "https://127.0.0.1:5000/upload"

files = {'file': open('data.json', 'rb')}

response = requests.post(url, files=files)
jsonFile.close()
#test
