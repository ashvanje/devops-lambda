import boto3

ec2 = boto3.resource('ec2')
rds = boto3.client('rds')

# --
# EC2
# --

def ec2_find_to_be_started_instances():
  filters = [
    {
      'Name': 'instance-state-name',
      'Values': ['stopped'],
    },
    {
      'Name': 'tag:StartAtWorkingHours',
      'Values': ['true'],
    },
  ]
  instances = ec2.instances.filter(Filters=filters)
  print(f'[DEBUG] EC2 instances to be started: {[ instance.id for instance in instances ]}')
  return instances

def ec2_start_instances():
  print('[INFO] Preparing to start the EC2 instances...')
  instances = ec2_find_to_be_started_instances()
  if len(list(instances)) > 0:
    print(f'[INFO] Starting {len(list(instances))} EC2 instances...')
    instances.start()
  else:
    print('[WARN] No EC2 instances to start')

# --
# RDS
# --

def rds_filter_to_be_started_instances_by_tag(instance):
  tags = rds.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
  for tag in tags:
    if tag['Key'] == 'StartAtWorkingHours' and tag['Value'] in [ 'true' ]:
      return True
  return False

def rds_find_to_be_started_instances():
  instances = rds.describe_db_instances()['DBInstances']
  instances = [
    instance for instance in instances
    if instance['DBInstanceStatus'] == 'stopped'
        and rds_filter_to_be_started_instances_by_tag(instance)
  ]
  print(f'[DEBUG] RDS instances to be started: {[ instance["DBInstanceIdentifier"] for instance in instances ]}')
  return instances

def rds_start_instances():
  print('[INFO] Preparing to start the RDS instances...')
  instances = rds_find_to_be_started_instances()
  if len(instances) > 0:
    print(f'[INFO] Starting {len(instances)} RDS instances...')
    for instance in instances:
      rds.start_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier'])
  else:
    print('[WARN] No RDS instances to start')

# --
# Lambda
# --

def lambda_handler(event, context):
  ec2_start_instances()
  rds_start_instances()
