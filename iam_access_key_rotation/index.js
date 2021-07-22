const aws = require('aws-sdk')
const iamService = require('./iam-service.js');
const stsService = require('./sts-service.js');

exports.handler = async (event) => {
    
    //sample input
    /*
    {
      "body": "{\"accountId\":\"038983778757\",\"username\":\"cx-managed-s3-user\"}"
    }
    */
    
    console.log(event)
    
    let body = JSON.parse(event.body)
    
    var user = body.username;
    await stsService.setAccountId(body.accountId);
    
    var iamClient = await getIamClient();
    console.log(event)
    
    var listRes = await iamService.listAccessKeys(iamClient, user)
    
    console.log(listRes.length)
    
    
    if(listRes.length == 2) {
        //return if there are 2 access key
        return outputAccessKeyLimitErrorObj(user);
    }
    
    // remove inactive access key
    /*
    for(let d of listRes) {
        if(d.Status == "Inactive") {
            console.log("inactive access key: " + d.AccessKeyId)
            var deleteRes = await iamService.deleteAccessKey(iamClient, d.AccessKeyId, user)
        }
    }
    */
    
    // create new access key
    var createRes = await iamService.createAccessKey(iamClient, user);
    // var createRes = {"test": "test"}
    
    // inactivate old access key
    if(createRes.AccessKeyId) {
        for(let d of listRes) {
            if(d.Status == "Active") {
                console.log("Active access key: " + d.AccessKeyId)
                // var updateRes = await iamService.updateAccessKey(iamClient, d.AccessKeyId, user)
            }
            
        }
    }
    
    console.log("Return:")
    console.log(createRes)
    
    var output = outputObj(createRes);
    console.log(output)
    return output;
};





function outputObj(res) {
    
    var date = new Date()
    
    // res = {
    //     "UserName": "cx-managed-s3-user",
    //     "AccessKeyId": date.getHours() + ":" + date.getMinutes(),
    //     "Status": "Active",
    //     "SecretAccessKey": date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds(),
    //     "CreateDate": "2021-05-24T06:47:51.000Z"
    // }
    
    return {
        "isBase64Encoded": false,
        "statusCode": 200,
        // "headers": { "headerName": "headerValue", ... },
        "headers": {
            "content-type": "application/json",
            "x-custom-header" : "my custom header value"
        },
        "body": JSON.stringify(res)
    }
    
}

function outputAccessKeyLimitErrorObj(user) {
    
    var res = {
        body: "access key limit exceeded, skipped rotating for this iam user - " + user
    }
    
    return {
        "isBase64Encoded": false,
        "statusCode": 500,
        "headers": {
            "content-type": "application/json",
        },
        "body": JSON.stringify(res)
    }
    
}



async function getIamClient() {
    return await new Promise((resolve, reject) => {
        // console.log("connecting to iam client the first time")
        stsService.getCrossAccountCredentials().then((data) => {
            console.log("sts data: ")
            console.log(data)
            // iamClient = new aws.IAM(test);
            var iamClient = new aws.IAM(data);
            // console.log("iamClient: ")
            // console.log(iamClient)
            resolve(iamClient)
        }, (err) => {
            console.log(err)
            reject(err)
        })
    });
}