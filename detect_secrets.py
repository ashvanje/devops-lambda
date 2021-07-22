
from detect_secrets import plugins
from detect_secrets.plugins.common.util import import_plugins
import json
import os

hex_limit = float(os.environ["HEX_LIMIT"])
base64_limit = float(os.environ["BASE64_LIMIT"])

def stringParser(data):
    splitedString = data.split('=')
    return splitedString[0]

def maskString(data,maskChar='*', maskIndex=5):
    output = ""

    for word in data.split(' '):
        
        if(len(word) < maskIndex):
            output += word
            output += ' '
        else:
            output += word[:maskIndex] + maskChar*(len(word)-maskIndex)
            output += ' '

    if(output[(len(output)-1):] == ' '):
        output = output[:(len(output)-1)]
    
    return output

def scan_secrets_counts(data=None, plugins=None):
    secrets = []

    for line in data.splitlines():

        secretContent = {}
        secretContent["Name"] = stringParser(line)
        secretContent["Counts"] = 0
        # secrets["Line " + str(lineNum)] = {}
        # secrets["Line " + str(lineNum)]["Content"] = maskString(line)
        # secrets["Line " + str(lineNum)]["Result"] = []
        

        for plugin in plugins:
            if (plugin._is_excluded_line(line)):

                continue
            
            if "True" in plugin.adhoc_scan(line):
                secretContent["Counts"] += 1

                # secret = {}
                # secret["Secret Detector Type"] = plugin.__class__.__name__
                # secret["Result"] = plugin.adhoc_scan(line)
                # secrets["Line " + str(lineNum)]["Result"].append(secret)
        secrets.append(secretContent)
    


    
    return secrets

def scan_secrets(data=None, plugins=None):
    secrets = {}

    lineNum = 0
    for line in data.splitlines():
        secrets["Line " + str(lineNum)] = {}
        secrets["Line " + str(lineNum)]["Content"] = maskString(line)
        secrets["Line " + str(lineNum)]["Result"] = []
        

        for plugin in plugins:
            if (plugin._is_excluded_line(line)):

                continue
            
            if "True" in plugin.adhoc_scan(line):

                secret = {}
                secret["Secret Detector Type"] = plugin.__class__.__name__
                secret["Result"] = plugin.adhoc_scan(line)
                secrets["Line " + str(lineNum)]["Result"].append(secret)
    
        lineNum += 1

    
    return json.dumps(secrets)


def initialize_plugins(hex_limit, base64_limit,exclude_lines_regex=None):
    plugins = []
    for pluginClass in import_plugins(()).values():
        plugins.append(pluginClass(base64_limit=base64_limit,hex_limit=hex_limit, exclude_lines_regex=exclude_lines_regex))

    return tuple(plugins)
    
def lambda_handler(event, context):
    # TODO implement
    
    try:
        data = event["data"]

    except KeyError as e:
        errorMsg = "Error(s): Attribute " + str(e) + " is missing in input data"
        return {
            'result': errorMsg
        }

        
    #initialise plugins
    try:
        exclude_lines_regex = None
        
        if("exclude_lines_regex" in event):
            exclude_lines_regex=event["exclude_lines_regex"]
        
        
        if("base64_limit" in event and "hex_limit" in event):
            plugins = initialize_plugins(hex_limit=event["hex_limit"],base64_limit=event["base64_limit"],exclude_lines_regex=exclude_lines_regex)
        elif("base64_limit" in event):
            plugins = initialize_plugins(base64_limit=event["base64_limit"],hex_limit=hex_limit,exclude_lines_regex=exclude_lines_regex)
        elif("hex_limit" in event):
            plugins = initialize_plugins(hex_limit=event["hex_limit"],base64_limit=base64_limit,exclude_lines_regex=exclude_lines_regex)
        else:
            plugins = initialize_plugins(base64_limit=base64_limit,hex_limit=hex_limit, exclude_lines_regex=exclude_lines_regex)
        
    except ValueError as e:
        return {
            'result': "Error(s): invalid hex_limt/base64_limit" 
        }
    except TypeError as e:
        return {
            'result': "Error(s): " + str(e)
        }
        
    if("mode" in event):
        if(event['mode'] == 'debug'):
            result = scan_secrets(data,plugins)
            return {
                'result' : result
            }

    result = scan_secrets_counts(data,plugins)
        
    return {
        'result': result
       
    }



# if __name__ == "__main__":
#     event = {
#   "data": "AWSsecret = AKIA1212121212121212\nsecret = AYje346w846mgvitmon2amz02awa8bjg3g",
#   "hex_limit": 1,
#  "base64_limit": 1,
#  "exclude_lines_regex" : "AKIA"
# }

#     x = lambda_handler(event,"")
#     print(x)

#     # print(x)
#     # plugins = initialize_plugins(1,1, "12")
#     # x = 'AWSsecret = AKIA1212121212121212\nsecret = AYje346w846mgvitmon2amz02awa8bjg3g'
#     # result = scan_screts(x, plugins)
#     # print(result)
    
