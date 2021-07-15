import boto3
import botocore
import json

APPLICABLE_RESOURCES = ["AWS::EC2::SecurityGroup"]

UNALLOWED_PERMISSIONS = [
{
    "IpProtocol" : "tcp",
    "FromPort" : 3389,
    "ToPort" : 3389,
},
{
    "IpProtocol" : "tcp",
    "FromPort" : 22,
    "ToPort" : 22,
}]

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
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type" : "NOT_APPLICABLE",
            "annotation" : "The rule doesn't apply to resources of type " +
            configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    group_id = configuration_item["configuration"]["groupId"]
    client = boto3.client("ec2");

    print ("evaluating CI: ", configuration_item)
    print ("Evaluating security group: ", group_id)

    try:
        response = client.describe_security_groups(GroupIds=[group_id])
    except botocore.exceptions.ClientError as e:
        print("e:", e)
        return {
            "compliance_type" : "NON_COMPLIANT",
            "annotation" : "describe_security_groups failure on group " + group_id
        }
    print ("Security Group Details: ", response)

    if debug_enabled:
        print("security group definition: ", json.dumps(response, indent=2))

    ip_permissions = response["SecurityGroups"][0]["IpPermissions"]
    
    for item in ip_permissions:
        if len(item["IpRanges"]) > 0:
            for x in item["IpRanges"]:
                ip_ranges = x["CidrIp"]
                print("ip_ranges: ", ip_ranges)
                if ip_ranges == "0.0.0.0/0" and not item["IpProtocol"] == "icmp":
                    print("source ip is any:", group_id)
                    try:
                        source = {"IpProtocol" : item["IpProtocol"], "FromPort" : item["FromPort"], "ToPort" : item["ToPort"]}
                        print("source detail:", source)
                        if source in UNALLOWED_PERMISSIONS:
                            return {
                                "compliance_type" : "NON_COMPLIANT",
                                "annotation" : "security_groups_check failure on group " + group_id
                            }
                    except botocore.exceptions.ClientError as e:
                        print("e:", e)

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "security_groups_check pass on group " + group_id
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
