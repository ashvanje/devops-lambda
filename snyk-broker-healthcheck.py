import boto3, requests, json, os
sns = boto3.client('sns')

def check_all_brokers():
  ip_str = os.environ['BROKER_IP']
  protocol = os.environ['HEALTHCHECK_PROTOCOL']
  port = os.environ['HEALTHCHECK_PORT']
  path = os.environ['HEALTHCHECK_PATH']
  ips = ip_str.split(',')
  ok = True
  for ip in ips:
    r = requests.get(url = f'{protocol}://{ip}:{port}{path}')
    rjson = r.json()
    print(f'Response from {ip}: ' + json.dumps(rjson))
    ok = ok and rjson['ok']
  
  return ok

def handler(event, context):
  ok = check_all_brokers()
  if not ok:
    response = sns.publish(
      # TopicArn='arn:aws:sns:ap-southeast-1:215658305678:snyk-broker-healthcheck-failed',    
      TopicArn='arn:aws:sns:ap-southeast-1:215658305678:health-topic',    
      Message='Snyk broker healthcheck failed!',    
    )
    print(response)