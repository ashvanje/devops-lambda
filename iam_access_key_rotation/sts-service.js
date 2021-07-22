const aws = require("aws-sdk");

var stsClient = null;

var accountId = null;

exports.getCrossAccountCredentials = async function() {
    
    const timestamp = (new Date()).getTime();
    console.log("timestamp: " + timestamp + ", accountId: " + accountId)
    const params = {
      RoleArn: `arn:aws:iam::${accountId}:role/_Cathay_DevopsLambdaDeployAccessRole`,
      RoleSessionName: `assumed-role-${timestamp}`,
      DurationSeconds: 3600,
    };
    return await new Promise((resolve, reject) => {
      getStsClient().assumeRole(params, (err, data) => {
        if (err) {
          console.log("rej")
            reject(err);
        }
        else {
          console.log("data1: ")
          console.log(data)
          resolve({
            accessKeyId: data.Credentials.AccessKeyId,
            secretAccessKey: data.Credentials.SecretAccessKey,
            sessionToken: data.Credentials.SessionToken,
          });
        }
      });
    });
    
}

exports.setAccountId = function(id) {
    accountId = id;
}

function getStsClient() {
    if(!stsClient) {
        var stsClient = new aws.STS({apiVersion: '2012-10-17'});
    }
    return stsClient;
}

// module.export = {
//   getCrossAccountCredentials
// }