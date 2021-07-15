import json, requests, boto3, calendar, time, os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
logs = boto3.client('logs')

def lambda_handler(event, context):
    token = os.environ['SNYK_TOKEN']
    groupid = os.environ['SNYK_GROUP_ID']
    # today = datetime.today().strftime('%Y-%m-%d')
    yesterday = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
    headers = {
        'content-type': 'application/json',
        'authorization': f'token {token}'
    }
    r = requests.post(f'https://snyk.io/api/v1/group/{groupid}/audit?from={yesterday}&sortOrder=DESC', headers=headers)
    log_events = []
    
    for event in r.json():
        if(datetime.strptime(event['created'], "%Y-%m-%dT%H:%M:%S.%fZ") > datetime.now() - timedelta(minutes=1)):
            tmp={}
            tmp['message'] = json.dumps(event)
            tmp['timestamp'] = calendar.timegm(datetime.strptime(event['created'], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple()) * 1000
            log_events.append(tmp)
    
    print(log_events)
    if(len(log_events) == 0):
        return
    
    # for event in log_events:
        # print(event['timestamp'])

    log_events = sorted(log_events, key = lambda i: i['timestamp']) 
    try:
        response = logs.create_log_group(logGroupName='snyk-audit-log')
    except logs.exceptions.ResourceAlreadyExistsException:
        print('log group already created')
    
    try:        
        response = logs.create_log_stream(logGroupName='snyk-audit-log', logStreamName='audit-log')
    except logs.exceptions.ResourceAlreadyExistsException:
        print('log stream already created')
    
    response = logs.describe_log_streams(
        logGroupName='snyk-audit-log',
        logStreamNamePrefix='audit-log'
    )
    print(response)
    sequence_token = response['logStreams'][0]['uploadSequenceToken']
        
    response = logs.put_log_events(
        logGroupName='snyk-audit-log',
        logStreamName='audit-log',
        # logEvents=log_events,
        logEvents=log_events,
        sequenceToken=sequence_token
    )
    print(response)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }