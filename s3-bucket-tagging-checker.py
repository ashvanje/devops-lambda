import json, boto3
from botocore.exceptions import ClientError
s3 = boto3.client('s3')
config = boto3.client('config')

required_tags = [
  { 'Key': 'ApplicationID', 'Value': [] }
]
    
def check_tags(tag_set):
  existing_keys = [ tag['Key'] for tag in tag_set ]
  required_keys = [ tag['Key'] for tag in required_tags ]
  
  if not all( tag_key in existing_keys for tag_key in required_keys ):
    return False
  
  for required_tag in required_tags:
    matched_tag = next( tag for tag in tag_set if tag['Key'] == required_tag['Key'] )
      
    if len(required_tag['Value']) > 0 and matched_tag not in required_tag['Value']:
      return False
      
  return True
  
  
def lambda_handler(event, context):
  if event and 'invokingEvent' in event:
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event['configurationItem']
    bucket = config_item['configuration']['name']
    
    app_id_tag_compliance = 'COMPLIANT'
    compliance_msg = ''
    try:
      tag_set = s3.get_bucket_tagging(Bucket = bucket)['TagSet']
      print('taggings of bucket ', bucket, ': ', tag_set)
      if check_tags(tag_set):
        app_id_tag_compliance = 'COMPLIANT'
        compliance_msg = 'All tags are set appropriately'
      else:
        app_id_tag_compliance = 'NON_COMPLIANT'
        compliance_msg = 'Some tags are missing'
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

