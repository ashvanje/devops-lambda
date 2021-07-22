const aws = require('aws-sdk');
const route53 = new aws.Route53();

const lbRecordMapping = {
  'followerLb': 'cpasmflw.cp1.cathaypacific.com',
  'dapLb': 'cpasmdap.cp1.cathaypacific.com',
  'dummyLb': 'dummy.cp1.cathaypacific.com'
};

async function changeRoute53Record(recordName, cnameVal) {
  const param = {
    ChangeBatch: {
      Changes: [
        {
          Action: "UPSERT", 
          ResourceRecordSet: {
            Name: `${recordName}`, 
            ResourceRecords: [
              {
                Value: `${cnameVal}`
              }
            ],
            TTL: 60,
            Type: "CNAME"
          }
        }
      ]
    }, 
    HostedZoneId: `${process.env.hostedZone}`
  };
  
  let response;
  try {
    response = await route53.changeResourceRecordSets(param).promise();
  } catch(e) {
    console.log(response);
    return {'msg': 'Route53 record update failed'};
  }
  return {'msg':'Successfully issued Route53 request.'};
}

async function checkSchema(event) {
  if (!('type' in event) || !('hostname' in event)) {
    throw  new Error('Invalid request');
  }
  if (typeof lbRecordMapping[event.type] == 'undefined') {
    throw  new Error('Invalid request');
  }
  return;
}

exports.handler = async (event) => {
  try {
    await checkSchema(event);
  } catch(e) {
    return {'msg':'invalid request'};
  }
  const recordName = lbRecordMapping[event.type];
  const cnameVal = event.hostname;
  
  console.log(`Going to update ${recordName} to CNAME ${cnameVal}`);
  
  return await changeRoute53Record(recordName, cnameVal);
};
