import boto3
import collections
import datetime
import time

ec = boto3.client('ec2')

def lambda_handler(event, context):
#    global lastRequestId
#    if lastRequestId is not None:
#        print("abort Retry...")
#        return
#    lastRequestId = context.aws_request_id
#    print("Context: %s" % context.aws_request_id)
    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag-key', 'Values': ['backup', 'Backup']},
            {'Name': 'tag:Environment', 'Values': ['CP1', 'cp1']},
        ]
    ).get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    print("Found %d instances that need backing up" % len(instances))

    to_tag = collections.defaultdict(list)

    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]
        except IndexError:
            retention_days = 7

        try:
            instance_name = [
                t.get('Value') for t in instance['Tags']
                if t['Key'] == 'Name'][0]
        except IndexError:
            instance_name = instance['InstanceId']

        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                continue
            vol_id = dev['Ebs']['VolumeId']
            print("Found EBS volume %s on instance %s" % (
                vol_id, instance['InstanceId'])
            )

            #snap = ec.create_snapshot(
            #    VolumeId=vol_id,
            #)

            #to_tag[retention_days].append(snap['SnapshotId'])
            
            #ec.create_tags(
            #    Resources=[snap['SnapshotId']],
            #    Tags=[
            #     {'Key': 'InstanceName', 'Value': instance_name},
            #     {'Key': 'CostCenter', 'Value': 'HKGIMTP9'},
            #    ]
            #)

            #print("Retaining snapshot %s of volume %s from instance %s (%s)  for %d days" % (
            #    snap['SnapshotId'],
            #    vol_id,
            #    instance_name,
            #    instance['InstanceId'],
            #    retention_days,
            #))
            
            time.sleep(1)


    for retention_days in to_tag.keys():
        delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
        delete_fmt = delete_date.strftime('%Y-%m-%d')
        print("Will delete %d snapshots on %s" % (len(to_tag[retention_days]), delete_fmt))
        ec.create_tags(
            Resources=to_tag[retention_days],
            Tags=[
                {'Key': 'DeleteOn', 'Value': delete_fmt},
            ]
        )