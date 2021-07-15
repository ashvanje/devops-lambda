import json, boto3, time
from botocore.exceptions import ClientError

rds = boto3.client('rds', region_name='ap-southeast-1')
cloudwatchlogs = boto3.client('logs', region_name='ap-southeast-1')
cloudwatch = boto3.client('cloudwatch', region_name='ap-southeast-1')
sns = boto3.client('sns', region_name='ap-southeast-1')
config = boto3.client('config')

def log_type_mapping(engine_type):
  '''
  Map the rds engine to the necessary log types published

  Parameters:
  engine_type (str): The engine type of the rds


  Returns:
  list: list of logs necessary to be published
  '''
  mapping = {
    'mariadb': ['audit', 'error', 'general'],
    'mysql': ['audit', 'error', 'general'],
    'postgres': ['postgresql'],
    'aurora': ['audit', 'error', 'general'],
    'oracle': ['audit'],
    'oracle-ee': ['audit'],
  }
  
  if engine_type in mapping:
    return mapping[engine_type]
  else:
    return []
    
    
def failed_login_keyword_mapping(engine_type):
  '''
  Map the rds engine to the keywords indicating failed login attempts

  Parameters:
  engine_type (str): The engine type of the rds


  Returns:
  str: the failed login attempts keywords
  '''
  mapping = {
    'mariadb': 'Access denied',
    'mysql': 'Access denied',
    'postgres': 'password authentication failed',
    'aurora': 'Access denied',
    'oracle': '1017 RETURNCODE',
    'oracle-ee': '1017 RETURNCODE'
  }
  
  if engine_type in mapping:
    return mapping[engine_type]
  else:
    return ''


def log_group_postfix_mapping(engine_type):
  '''
  Map the rds engine to the log group postfix

  Parameters:
  engine_type (str): The engine type of the rds


  Returns:
  str: the log group postfix

  '''
  mapping = {
    'mariadb': '/error',
    'mysql': '/error',
    'postgres': '/postgresql',
    'aurora': '/error',
    'oracle': '/audit',
    'oracle-ee': '/audit'
  }
  
  if engine_type in mapping:
    return mapping[engine_type]
  else:
    return ''


def check_rds(profile):
  '''
  Check if all necessary rds logs are exported to CloudWatch

  Parameters:
  profile (dict): One of the instance profile returned by the describe_db_instances call


  Returns:
  bool: True if necessary logs are exported; False otherwise

  '''
  engine_type = profile['engine']
  if 'enabledCloudwatchLogsExports' in profile:
    print(profile['enabledCloudwatchLogsExports'])
    print(profile['engine'])
    
  if not 'enabledCloudwatchLogsExports' in profile or \
     not all( log in profile['enabledCloudwatchLogsExports'] for log in log_type_mapping(engine_type) ):
    return False
  else:
    return True


def modify_rds(identifier, engine_type, is_cluster):
  '''
  Modify the CloudWatch export config for the rds with given profile

  Parameters:
  profile (dict): One of the instance profile returned by the describe_db_instances call


  Returns:
  Nil

  '''
  for i in range(8):
    try:
      if is_cluster:
        rds.modify_db_cluster(DBClusterIdentifier=identifier, CloudwatchLogsExportConfiguration={'EnableLogTypes': log_type_mapping(engine_type)})
      else:
        rds.modify_db_instance(DBInstanceIdentifier=identifier, CloudwatchLogsExportConfiguration={'EnableLogTypes': log_type_mapping(engine_type)})
    except ClientError as e:
      if e.response['Error']['Code'] == 'InvalidParameterCombination':
        print('DB has already been modified previously, skipping...')
        break
      else:
        time.sleep(30)
    else:
      break
    

def check_and_modify_rds(profile):
  '''
  Check if all necessary logs are published to CloudWatch. If not, publish the logs

  Parameters:
  profile (dict): One of the instance profile returned by the describe_db_instances call

  Returns:
  dict:
    modified (bool): If modified True, False otherwisse
    identifier (str): Empty string if not modified

  '''
  # print(profile)
  is_cluster = False if profile['dBInstanceIdentifier'] else True
  identifier = profile['dBClusterIdentifier'] if is_cluster else profile['dBInstanceIdentifier']
  
  if not check_rds(profile):
    print('This RDS is not configured properly. Modifying...')
    modify_rds(identifier, profile['engine'], is_cluster)
  
  return {
    'identifier': identifier,
    'is_cluster': is_cluster, 
    'engine': profile['engine']
  }
    
def lambda_handler(event, context):
    if event and 'invokingEvent' in event:
      invoking_event = json.loads(event['invokingEvent'])
      config_item = invoking_event['configurationItem']
      profile = config_item['configuration']
      identifier = profile['dBInstanceIdentifier'] if profile['dBInstanceIdentifier'] else profile['dBClusterIdentifier']
    
      print(f'Checking rds {identifier}...')
      result = check_and_modify_rds(profile)
      
      '''
      This block create metric filters for the error log
      '''
      print(f'{identifier} has missing metric filter. Setting it up...')
      prefix = '/aws/rds/cluster/' if result['is_cluster'] else '/aws/rds/instance/'
      identifier = result['identifier']
      postfix = log_group_postfix_mapping(result['engine'])
      
      log_group_name = prefix + identifier + postfix
      print(f'Setting up metric filter for {log_group_name}')
      
      cloudwatchlogs.put_metric_filter(
        logGroupName = log_group_name,
        filterName='Access-denied-' + result['engine'],
        filterPattern=failed_login_keyword_mapping(result['engine']),
        metricTransformations=[
          {
            'metricName': 'AccessDeniedCount',
            'metricNamespace': 'LogMetrics',
            'metricValue': '1',
            'defaultValue': 0.0
          }
        ]
      )
      
      '''
      This block create alarm based on the metric filters previously setup
      '''
      print(f'Setting alert for {identifier}...')
      response = sns.create_topic(Name='compliance-reporter-topic')
      rds_sns_alert_topic = response['TopicArn']

      cloudwatch.put_metric_alarm(
        AlarmName='RDS-Frequent-Failed-Login-Attempts',
        AlarmDescription='Alarm for frequent failed login attempts, which indicates that the databases are under attack potentially.',
        ActionsEnabled=False,
        Namespace='LogMetrics',
        MetricName='AccessDeniedCount',
        Statistic='Sum',
        Period=300,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=5.0,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        AlarmActions=[
          rds_sns_alert_topic
        ]
      )
    
    response = config.put_evaluations(
    Evaluations=[
           {
               'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
               'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
               'ComplianceType': 'COMPLIANT',
               'Annotation': 'The filter is set for this RDS',
               'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
           },
       ],
       ResultToken=event['resultToken']
    )
    
    print('Checked and modified if necessary!')
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }


