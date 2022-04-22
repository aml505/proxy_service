import os
import json
import time
from config.config import Config
from query.query import Query
from parser.parser import Parser
from request.request import Request

def loadSSH():
    print("ssh keys LOAD")
def collectData():
    print("I collected data from devices")
def jsonParse():
    print("I parsed the json file")
def jsonSend(token):
    """filename = 'data.json'
    print("uploading JSON file to controller")
    current_request = Request()
    url = cfg.controller_url + "/api/dt/running/state"
    response = current_request.postRequestFile(url, token, filename)
    return response"""
def configNetwork():
    print("configNetwork done")
def controllerAuthentication():
    current_request = Request()
    data = {
        'username': cfg.conf_file_contents['CONTROLLER_AUTH']['username'],
        'password': cfg.conf_file_contents['CONTROLLER_AUTH']['password']
    }
    url = cfg.controller_url + "/api/login/user"
    response = current_request.postRequestJson(url,data)
    return response['token']



if __name__ == '__main__':
    cfg = Config()
    token = controllerAuthentication()
    print(token)
    #load ssh keys and set up known_hosts
    loadSSH()
    configNetwork()
    if(cfg.repeat_timer == None):
        collectData()
        jsonParse()
        jsonSend(token)
    else:
        while(True):
            collectData()
            jsonParse()
            print(jsonSend(token))
            time.sleep(int(cfg.repeat_timer))
            