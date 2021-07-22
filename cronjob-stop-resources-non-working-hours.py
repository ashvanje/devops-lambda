import boto3

ec2 = boto3.resource('ec2')
rds = boto3.client('rds')

# --
# EC2
# --

def ec2_find_to_be_stopped_instances():
  filters = [
    {
      'Name': 'instance-state-name',
      'Values': ['running'],
    },
    {
      'Name': 'tag:StopAtNonWorkingHours',
      'Values': ['true'],
    },
  ]
  instances = ec2.instances.filter(Filters=filters)
  print(f'[DEBUG] EC2 instances to be stopped: {[ instance.id for instance in instances ]}')
  return instances

def ec2_stop_instances():
  print('[INFO] Preparing to stop the EC2 instances...')
  instances = ec2_find_to_be_stopped_instances()
  if len(list(instances)) > 0:
    print(f'[INFO] Stopping {len(list(instances))} EC2 instances...')
    instances.stop()
  else:
    print('[WARN] No EC2 instances to stop')

# --
# RDS
# --

def rds_filter_to_be_stopped_instances_by_tag(instance):
  tags = rds.list_tags_for_resource(ResourceName=instance['DBInstanceArn'])['TagList']
  for tag in tags:
    if tag['Key'] == 'StopAtNonWorkingHours' and tag['Value'] in [ 'true' ]:
      return True
  return False

def rds_find_to_be_stopped_instances():
  instances = rds.describe_db_instances()['DBInstances']
  instances = [
    instance for instance in instances
    if instance['DBInstanceStatus'] == 'available'
        and rds_filter_to_be_stopped_instances_by_tag(instance)
  ]
  print(f'[DEBUG] RDS instances to be stopped: {[ instance["DBInstanceIdentifier"] for instance in instances ]}')
  return instances

def rds_stop_instances():
  print('[INFO] Preparing to stop the RDS instances...')
  instances = rds_find_to_be_stopped_instances()
  if len(instances) > 0:
    print(f'[INFO] Stopping {len(instances)} RDS instances...')
    for instance in instances:
      rds.stop_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier'])
  else:
    print('[WARN] No RDS instances to stop')

# --
# Lambda
# --

def lambda_handler(event, context):
  ec2_stop_instances()
  rds_stop_instances()
