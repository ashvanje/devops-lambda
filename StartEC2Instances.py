import boto3
region = 'ap-southeast-1'
instances = [
# OSC2-CT1
'i-0a74cc643a418f8b0', #sinc3lxosan0030
'i-00abf7977d6e4c4e2', #sinc3lxosan0031
'i-0bad831659f172735', #sinc3lxosan0032
'i-09df23cd1f4254d92', #sinc3lxosan0048
'i-01d2b2c2306de5357', #sinc3lxosan0049
'i-04ddfedb8170c8e66', #sinc3lxosan0050
# keep on for additional resource 'i-0ae9db3309e997b6a', #sinc3lxosan0051
# stopped 'i-0abf3b487c8c1a306', #sinc3lxosan0060
# stopped 'i-020bd49163bf34b36', #sinc3lxosan0061
# OSC1-CT1
# stopped 'i-0ef58ddc2eb6c062a', #sinc2lxosan0117
# stopped 'i-0ae60b470ffe81a38', #sinc2lxosan0120
# stopped 'i-0418d890282541a92', #sinc2lxosan0121
'i-09386f12fdb4ac188', #sinc2lxosan0123
# stopped 'i-08c0f5161b9879b55', #sinc2lxosan0125
# stopped 'i-0832496f2454add59' #sinc2lxosan0126
]

def lambda_handler(event, context):
    ec2 = boto3.client('ec2', region_name=region)
    ec2.start_instances(InstanceIds=instances)
    print(f'started your instances: {instances}.')
	