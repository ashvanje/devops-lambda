import boto3
import botocore
import json

APPLICABLE_RESOURCES = ["AWS::EC2::Instance"]

ec2 = boto3.client("ec2")

ALLOWED_PERMISSIONS = [
{
    "IpProtocol" : "tcp",
    "FromPort" : 80,
    "ToPort" : 80,
},
{
    "IpProtocol" : "tcp",
    "FromPort" : 443,
    "ToPort" : 443,
}]

def isProductionSubnet(ip):
    parts = ip.split(".")
    if parts[0] == "172" and parts[1] == "31" and int(parts[2]) >= 192 and int(parts[2]) <= 255:
        return True 
    return False

# Helper function used to validate input
def check_defined(reference, reference_name):
    if not reference:
        raise Exception('Error: ', reference_name, 'is not defined')
    return reference

# normalize_parameters
#
# Normalize all rule parameters so we can handle them consistently.
# All keys are stored in lower case.  Only boolean and numeric keys are stored.
def normalize_parameters(rule_parameters):
    for key, value in rule_parameters.items():
        normalized_key=key.lower()
        normalized_value=value.lower()

        if normalized_value == "true":
            rule_parameters[normalized_key] = True
        elif normalized_value == "false":
            rule_parameters[normalized_key] = False
        elif normalized_value.isdigit():
            rule_parameters[normalized_key] = int(normalized_value)
        else:
            rule_parameters[normalized_key] = True
    return rule_parameters

# evaluate_compliance
#
# This is the main compliance evaluation function.
#
# Arguments:
#
# configuration_item - the configuration item obtained from the AWS Config event
# debug_enabled - debug flag
#
# return values:
#
# compliance_type -
#
#     NOT_APPLICABLE - (1) something other than a security group is being evaluated
#                      (2) the configuration item is being deleted
#     NON_COMPLIANT  - the rules do not match the required rules and we couldn't
#                      fix them
#     COMPLIANT      - the rules match the required rules or we were able to fix
#                      them
#
# annotation         - the annotation message for AWS Config
def evaluate_compliance(configuration_item, debug_enabled):
    print("resourceType:", configuration_item["resourceType"])
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        print("not applicable")
        return {
            "compliance_type" : "NOT_APPLICABLE",
            "annotation" : "The rule doesn't apply to resources of type " +
            configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        print("deleted, so not applicable")
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    instance_id = configuration_item["configuration"]["instanceId"]
    print ("Evaluating EC2: ", instance_id)
    print ("Details: ", configuration_item)
    ip = configuration_item["configuration"]["networkInterfaces"][0]["privateIpAddresses"][0]["privateIpAddress"]
    print ("IP from CI:" , ip)
    if not isProductionSubnet(ip):
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The instance is not in production subnet."
        }


    try:
#        response = client.describe_instances(InstanceIds=[instance_id])
        unencrypted_list = []
        blockdevices = configuration_item["configuration"]["blockDeviceMappings"]
        rootdevice = configuration_item["configuration"]["rootDeviceName"]
        print ("RootDevice Name: ", rootdevice)
        for bd in blockdevices:
            volume_id = bd["ebs"]["volumeId"]
            device_name = bd["deviceName"]
            print ("Block Device: ", volume_id)
            print ("Block Device Volume ID:", device_name)
            if not device_name == rootdevice:
                # only check on data disk
                response2 = ec2.describe_volumes(VolumeIds=[volume_id])
                is_encrypted = response2["Volumes"][0]["Encrypted"]
                print ("Encrypted? ", is_encrypted)
                if not is_encrypted:
                    unencrypted_list.append(volume_id)
        if len(unencrypted_list) > 0:
            v_str = ""
            for v in unencrypted_list:
                v_str = v_str + "[" + v + "]"
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The instance with un-encrypted volume(s) " + v_str
            }
                     
        return {
            "compliance_type": "COMPLIANT",
            "annotation": "The instance is in production subnets."
        }
            
    except botocore.exceptions.ClientError as e:
        print ("botocore exception:", e)
        return {
            "compliance_type" : "NON_COMPLIANT",
            "annotation" : "describe_instances failure on instance " + instance_id
        }
        
    return {
        "compliance_type": "COMPLIANT",
        "annotation": "instance volume check pass on instance " + instance_id
    }

def lambda_handler(event, context):
    check_defined(event, 'event')
    invoking_event = json.loads(event['invokingEvent'])

    check_defined(invoking_event, 'invokingEvent')
    configuration_item = invoking_event["configurationItem"]

    rule_parameters = normalize_parameters(json.loads(event["ruleParameters"]))

    debug_enabled = False

    if "debug" in rule_parameters:
        debug_enabled = rule_parameters["debug"]

    if debug_enabled:
        print("Received event: " + json.dumps(event, indent=2))

    evaluation = evaluate_compliance(configuration_item, debug_enabled)
    print("Eva:", evaluation)

    config = boto3.client('config')

    response = config.put_evaluations(
       Evaluations=[
           {
               'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
               'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
               'ComplianceType': evaluation["compliance_type"],
               "Annotation": evaluation["annotation"],
               'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
           },
       ],
       ResultToken=event['resultToken'])

