import boto3
import botocore
import json

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


def lambda_handler(event, context):

    ACCOUNT_ID = context.invoked_function_arn.split(":")[4]
    config = boto3.client('config')
    aggregator="security-control-config-aggr"
    region="ap-southeast-1"

    message="This is a auto-generated message, please approach DevOps team if you have any enquiry on the message's content.\n\n"
    message+="Below is the compliance status of account " + ACCOUNT_ID + "\n\n"

    rules = config.describe_config_rules()
    for rule in rules["ConfigRules"]:
        rule_name = rule["ConfigRuleName"]
        message += "Non-Compliance Result of [" + rule_name + "]: \n"
        #message += "\n========== NON_COMPLIANT ============\n"
        response = config.get_compliance_details_by_config_rule(ConfigRuleName=rule_name, ComplianceTypes=["NON_COMPLIANT"])
        if len(response["EvaluationResults"]) > 0:
            for result in response["EvaluationResults"]:
                message += result["EvaluationResultIdentifier"]["EvaluationResultQualifier"]["ResourceId"]
                if "Annotation" in result:
                    message += ": " + result["Annotation"] + "\n"
                else:
                    message += "\n"
        else:
            message += "Nil\n"
        message += "\n\n"
#        message += "========== NON_COMPLIANT ============\n"
#        response = config.get_compliance_details_by_config_rule(ConfigRuleName=rule_name, ComplianceTypes=["COMPLIANT"])
#        for result in response["EvaluationResults"]:
#            message += result["EvaluationResultIdentifier"]["EvaluationResultQualifier"]["ResourceId"]
#        message += "\n\n"

    print ("Message: " + message)
    subject = "[" + ACCOUNT_ID + "] compliance report"

    sns = boto3.client('sns')

    topic_arn = "arn:aws:sns:ap-southeast-1:" + ACCOUNT_ID + ":compliance-reporter-topic"
    try:
        sns.publish(TopicArn=topic_arn, Subject=subject, Message=message)
    except botocore.exceptions.ClientError as e:
        print ("Fail to send message to topic " + topic_arn)
        print ("Reason: ",e)

