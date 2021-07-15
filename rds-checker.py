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
    "TagName" : "ApplicationID",
    "TagValues" : []
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
    client = boto3.client("rds")
    ec2 = boto3.client('ec2')

    try:
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

        is_encrypted = response["DBInstances"][0]["StorageEncrypted"]
        if not is_encrypted:
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The RDS instance [" + instance_id + "] with un-encrypted volume(s) "
            }

        db_engine = response["DBInstances"][0]["Engine"]
        print ("DB Engine: ", db_engine)

        if db_engine.startswith("aurora"):
            db_cluster_id = response["DBInstances"][0]["DBClusterIdentifier"]
            print ("Aurora Cluster ID: ", db_cluster_id)
            db_cluster_response = client.describe_db_clusters(DBClusterIdentifier=db_cluster_id)
            print ("Aurora Cluster Response: ", db_cluster_response)
            is_multi_az = db_cluster_response["DBClusters"][0]["MultiAZ"]
        else:
            is_multi_az = response["DBInstances"][0]["MultiAZ"]
        print ("multi-AZ: ", is_multi_az)

        if not is_multi_az:
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The RDS instance [" + instance_id + "] is not multi-AZ "
            }

        is_publicly_accessible = response["DBInstances"][0]["PubliclyAccessible"]
        if is_publicly_accessible:
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The RDS instance [" + instance_id + "] is publicly accessible "
            }

        license_model = response["DBInstances"][0]["LicenseModel"]
        print ("LicenseModel: ", license_model)
        if license_model != "general-public-license" and license_model != "license-included" and license_model != "postgresql-license":
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The RDS instance [" + instance_id + "] is not using general public license "
            }

        tags = configuration_item["tags"]
        if len(tags) == 0:
            return {
                "compliance_type": "NON_COMPLIANT",
                "annotation": "The RDS instance [" + instance_id + "] is missing all/some of the standard tags" 
            }
        for required_tag in RDS_REQUIRED_TAGS:
            r_tag_name = required_tag["TagName"]
            r_tag_values = required_tag["TagValues"]
            if r_tag_name in tags:
                tag_value = tags[r_tag_name]
                if len(r_tag_values)>0 and tag_value not in r_tag_values:
                    return {
                        "compliance_type": "NON_COMPLIANT",
                        "annotation": "The RDS instance [" + instance_id + "] with incorrect value of tag " + r_tag_name
                    }
            else:
                return {
                    "compliance_type": "NON_COMPLIANT",
                    "annotation": "The RDS instance [" + instance_id + "] with missing tag " + r_tag_name
                }

        return {
            "compliance_type": "COMPLIANT",
            "annotation": "The RDS instance [" + instance_id + "] is comply with CPA standard."
        }
           
            
    except botocore.exceptions.ClientError as e:
        print ("e:", e)
        return {
            "compliance_type" : "NON_COMPLIANT",
            "annotation" : "describe_instances failure on instance " + instance_id
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

