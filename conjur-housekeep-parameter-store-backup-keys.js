const aws = require('aws-sdk');
const ssm = new aws.SSM();

exports.handler = async (event) => {
  let parameters = await ssm.describeParameters({
    ParameterFilters: [{Key: 'Name',Option: 'BeginsWith',Values: ['conjur']}]
  }).promise();
  parameters = parameters['Parameters'].filter(parameter => {
    const lastDate = Date.parse(parameter.LastModifiedDate);
    const now = new Date().getTime();
    return lastDate < now - (parseInt(process.env.TTL, 10) * 24 * 60 * 60 * 1000) ? true : false;
  });
  console.log('Backup keys to be deleted:');
  console.log(parameters);
  const toBeDeletedList = parameters.map(p => p.Name);
  if (toBeDeletedList.length > 0) {
    let result = await ssm.deleteParameters({ Names: toBeDeletedList }).promise();
    console.log(`The result of key deletion: ${result}`);
  } else {
    console.log('No keys to be deleted.');
  }
  return {'msg':'Completed!'};
};
