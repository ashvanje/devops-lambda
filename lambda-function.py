import socket
import json
import boto3
import os

hostname = os.environ["HOSTNAME"]
targetGroupArn = os.environ["TARGET_GROUP_ARN"]

def getIpv4IpsByhostname(hostname):
    return socket.gethostbyname_ex(hostname)[2]

def getCurrentTargets(elbClient, targetGroupArn):
    res = elbClient.describe_target_health(TargetGroupArn=targetGroupArn)
    resultTargets = []
    [resultTargets.append(target["Target"]["Id"]) for target in res["TargetHealthDescriptions"]]
    
    return resultTargets


def addTargets(elbClient, targetGroupArn, newTargets):
    targets = []
    for ip in newTargets:
        target = {}
        target['Id'] = ip
        targets.append(target)

    res = elbClient.register_targets(TargetGroupArn=targetGroupArn,Targets=targets)

    return res


def removeTargets(elbClient, targetGroupArn, oldTargets):
    targets = []
    for ip in oldTargets:
        target = {}
        target['Id'] = ip
        targets.append(target)

    res = elbClient.deregister_targets(TargetGroupArn=targetGroupArn,Targets=targets)
    return res
 
def updateTargets(elbClient, targetGroupArn,currentTargets, newTargets):
    addTargetsList = list(set(newTargets)-set(currentTargets))
    removeTargetsList = list(set(currentTargets)-set(newTargets))

    if(len(addTargetsList)==0 and len(removeTargetsList)==0):
        print("No changes in IPs of the elasticsearch service ")
    else:
        if(len(removeTargetsList)!=0):
            resReoveTargets = removeTargets(elbClient,targetGroupArn,removeTargetsList)
            print("IP(s): {} is/are removed.".format(removeTargetsList))
        
        if(len(addTargetsList)!=0):
            resAddTargets = addTargets(elbClient, targetGroupArn, addTargetsList)
            print("IP(s): {} is/are added.".format(addTargetsList))
    
        
    return True



def lambda_handler(event, context):
    #Initialize ELBv2 Client

    elbClient = boto3.client("elbv2")

    newIps = getIpv4IpsByhostname(hostname)
    print("IPs by looking up the hostname {} : {}".format(hostname,newIps))
    
    currentTargets = getCurrentTargets(elbClient,targetGroupArn)
    print("Existing Targets of Target group {} : {}".format(targetGroupArn,currentTargets))

    updateTargets(elbClient, targetGroupArn,currentTargets,newIps)
    



    


