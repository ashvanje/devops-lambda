import boto3
import botocore
import json

APPLICABLE_RESOURCES = ["AWS::RDS::DBInstance"]

RDS_REQUIRED_TAGS = [
{
    "TagName" : "Environment",
    "TagValues" : []
},
{
    "TagName" : "DataClass",
    "TagValues" : ["Public", "Internal", "Sensitive", "Highly Sensitive"]
}
]


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

    instance_id = configuration_item["configuration"]["dBInstanceIdentifier"]
    print ("Evaluating RDS [ " + instance_id +  "] against CPA security guideline described in https://cathaypacific-prod.atlassian.net/wiki/spaces/CPD/pages/389612524/Security+Guideline+for+your+AWS+account")
    print ("CI Details:", configuration_item["configuration"])

    is_encrypted = configuration_item["configuration"]["storageEncrypted"]
    if is_encrypted:
        return {
            "compliance_type": "COMPLIANT",
            "annotation": "The RDS instance [" + instance_id + "] is comply with CPA standard."
        }

    client = boto3.client("rds")
    ec2 = boto3.client('ec2')

    response = client.describe_db_instances(DBInstanceIdentifier=instance_id)
    print("RDS Details: ", response)


    vpc_id = response["DBInstances"][0]["DBSubnetGroup"]["VpcId"]
    response2 = ec2.describe_vpcs(VpcIds=[vpc_id])
    cidr_block = response2["Vpcs"][0]["CidrBlock"]
    print ("cidr_block ip: ", cidr_block.split("/")[0])
    if not isProductionSubnet(cidr_block.split("/")[0]):
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The RDS instance [" + instance_id + "] is not in production subnet."
        }            

    return {
        "compliance_type": "NON_COMPLIANT",
        "annotation": "The RDS instance [" + instance_id + "] with un-encrypted volume(s) "
    }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "rds compliance checking passed on instance " + instance_id
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

    print ("Evaluation Result:", evaluation)


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

