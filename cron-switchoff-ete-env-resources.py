import boto3

ec2 = boto3.resource('ec2')

def lambda_handler(event, context):
  filters = [
    {
      'Name': 'tag:StopAtNonWorkingHours',
      'Values': ['true'],
    },
    {
      'Name': 'instance-state-name',
      'Values': ['running']
    }
  ]
  
  instances = ec2.instances.filter(Filters=filters)
  
  RunningInstances = [instance.id for instance in instances]

  # For debug purpose
  print(RunningInstances)
  
  if len(RunningInstances) > 0:
    shuttingDown = ec2.instances.filter(InstanceIds=RunningInstances).stop()
    print(shuttingDown)
    # print(RunningInstances)
  else:
    print("WARNING: no instances in the specified env is running")