import json, boto3, re
from botocore.exceptions import ClientError
s3 = boto3.client('s3')
config = boto3.client('config')

required_tags = [
  { 'Key': 'ApplicationID', 'Regex': '^\d{4}$' },
  { 'Key': 'Environment', 'Regex': '^[DPT]\d{1,3}$|^cp1$|^ct1$' }
]
    
def check_tags(tags):
  result =  {'valid':True, 'missing': [], 'wrong': []}
  existing_keys = tags.keys()
  required_keys = [ tag['Key'] for tag in required_tags ]
  
  for required_key in required_keys:
    if not required_key in existing_keys:
      result['missing'].append(required_key)
      result['valid'] = False
  
  for required_tag in required_tags:
    if not required_tag['Key'] in tags:
      continue
    
    matched_tag = tags[required_tag['Key']]
      
    pattern = re.compile(required_tag['Regex'])
    wrong=False
    for item in matched_tag.split():
      if not pattern.match(item):
        wrong = True
    
    if wrong:    
      result['wrong'].append(required_tag['Key'])
      result['valid'] = False
  
  return result
  
  
def lambda_handler(event, context):
  if event and 'invokingEvent' in event:
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event['configurationItem']
    print(config_item['resourceId'])
    print(config_item['resourceType'])
    print(config_item['tags'])

    app_id_tag_compliance = 'COMPLIANT'
    compliance_msg = ''
    try:
      tags = config_item['tags']
      print('taggings of resource ', config_item['resourceId'], ' of type ', config_item['resourceType'], ': ', tags)
      result = check_tags(tags)
      if result['valid']:
        app_id_tag_compliance = 'COMPLIANT'
        compliance_msg = 'All tags are set appropriately'
      else:
        app_id_tag_compliance = 'NON_COMPLIANT'
        compliance_msg=''
        if len(result['missing']) > 0:
          compliance_msg += f"Tags {result['missing']} is/are missing. "
          
        if len(result['wrong']) > 0:
          compliance_msg += f"Tags {result['wrong']} is/are of wrong format. "

    except ClientError as e:
      print('Exception when getting tags for bucket: ', bucket)
      if e.response['Error']['Code'] == 'NoSuchTagSet':
        print('No tag set for ', bucket)
        app_id_tag_compliance = 'NON_COMPLIANT'
        compliance_msg = bucket + ' does not have any taggings'
  else:
    raise Exception('[ERROR] event argument not passed in lambda handler')
  
  print(f'Evaluation result: {app_id_tag_compliance} ({compliance_msg})')
  response = config.put_evaluations(
    Evaluations=[
         {
             'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
             'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
             'ComplianceType': app_id_tag_compliance,
             'Annotation': compliance_msg,
             'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
         },
     ],
     ResultToken=event['resultToken']
  )

