from flask import request
import os
import json

def env(key, default=None) :
    envvalue = os.getenv(key)
    if envvalue == None :
        envvalue = default
    if envvalue.lower() == "true" :
        envvalue = True
    elif envvalue.lower() == "false" :
        envvalue = False
    return envvalue

def getUrl():
    return request.host

def getModule(url=None):
    if url == None :
        url = request.path
    path_parts = url.split('/')
    return path_parts[1] if len(path_parts) > 1 else ''
    
def getMethod(url=None):
    if url == None :
        url = request.path
    path_parts = url.split('/')
    return path_parts[2] if len(path_parts) > 1 else ''