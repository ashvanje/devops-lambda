import boto3
import botocore
import json
import datetime

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
def evaluate_compliance(event):

    owner_id = event["accountId"]
    ec2 = boto3.client('ec2')

    response = ec2.describe_images(Owners=[owner_id])

    public_ami = []
    for ami in response["Images"]:
        print ("evaluting ami ", ami)
        if ami["Public"]:
            public_ami.append(ami["ImageId"])
    if len(public_ami) > 0:
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": "the following ami(s) are publicly accessible: " + public_ami
        }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "all ami(s) are comply with CPA standard"
    }

def lambda_handler(event, context):

    evaluation = evaluate_compliance(event)
    print("Evaluation Result :", evaluation)

    config = boto3.client('config')

    response = config.put_evaluations(
       Evaluations=[
           {
               'ComplianceResourceType': 'AWS::::Account',
               'ComplianceResourceId': event["accountId"],
               'ComplianceType': evaluation["compliance_type"],
               "Annotation": evaluation["annotation"],
               'OrderingTimestamp': datetime.datetime.now()
           }

       ],
       ResultToken=event['resultToken'])

