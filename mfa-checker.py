import json, boto3, os
from botocore.exceptions import ClientError
from pprint import pprint
from datetime import datetime, timedelta

iam = boto3.client('iam')

def has_login_profile(username):
  try:
    iam.get_login_profile(UserName=username)
    return True
  except ClientError as e:
    if e.response['Error']['Code'] == 'NoSuchEntity':
      return False
    else:
      raise e


def has_mfa_enabled(username):
  response = iam.list_mfa_devices(UserName=username)
  if(len(response['MFADevices']) > 0):
    return True
  else:
    return False


def is_created_within_window(username):
  create_date = iam.get_login_profile(UserName=username)['LoginProfile']['CreateDate']
  if(datetime.now(create_date.tzinfo) < create_date + timedelta(hours=int(os.environ['disable_window']))):
    return True
  else:
    return False
  
  
def disable_user(username):
  accessKeys = list(map(lambda metadata: metadata['AccessKeyId'], iam.list_access_keys(UserName=username)['AccessKeyMetadata']))
  print(username + 'is going to be disabled...')
  for key in accessKeys:
    iam.update_access_key(UserName=username, AccessKeyId=key, Status='Inactive')
  
  iam.delete_login_profile(UserName=username)
  return
  
  
def lambda_handler(event, context):
    allUsers = list(map(lambda user: user['UserName'], iam.list_users()['Users']))
    print('All IAM Users:')
    print(allUsers)
    
    usersWithConsoleAccess = list(filter(lambda user: has_login_profile(user), allUsers))
    print('All IAM Users with console access:')
    print(usersWithConsoleAccess)
    
    usersCreatedOutOfWindow = list(filter(lambda user: not is_created_within_window(user), usersWithConsoleAccess))
    print('All created out of the allowable window:')
    print(usersCreatedOutOfWindow)
    
    usersWithoutMFA = list(filter(lambda user: not has_mfa_enabled(user), usersCreatedOutOfWindow))
    print('All IAM Users without MFA enabled:')
    print(usersWithoutMFA)
    
    for user in usersWithoutMFA:
      disable_user(user)
    
    return {
      'statusCode': 200,
      'body': json.dumps('MFA check done.')
    }


