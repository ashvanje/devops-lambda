const aws = require("aws-sdk");
// const {getCrossAccountCredentials} = require('./sts-service.js');
const stsService = require('./sts-service.js');


var iamClient = null;


exports.listAccessKeys = async function(client, username) {
    
    var params = {
        UserName: username
    };
    
    var result = await new Promise((resolve, reject) => {
        client.listAccessKeys(params, function(err, data) {
            if (err) {
                // throw (err, err.stack); // an error occurred
                reject(err)
            }
            else {
                console.log("got access key list")
                console.log(data);      // successful response
                resolve(data.AccessKeyMetadata);
            }
        });
    })
    
    return result;
    
}

exports.createAccessKey = async function(client, username) {
    
    var params = {
        UserName: username
    };
    
    var result = await new Promise((resolve, reject) => {
        client.createAccessKey(params, function(err, data) {
            if (err) {
                // throw (err, err.stack); // an error occurred
                reject(err)
            }
            else {
                console.log("created access key: " + data.AccessKey.AccessKeyId)
                console.log(data);      // successful response
                resolve(data.AccessKey);
            }
        });
    })
    return result;
}

exports.updateAccessKey = async function(client, accessKeyId, username) {
    
    var params = {
        AccessKeyId: accessKeyId,
        UserName: username,
        Status: "Inactive"
    };
    
    var result = await new Promise((resolve, reject) => {
        client.updateAccessKey(params, function(err, data) {
            if (err) {
                // throw (err, err.stack); // an error occurred
                reject(err)
            }
            else {
                console.log("updated access key: " + accessKeyId)
                console.log(data);      // successful response
                resolve(data);
            }
        });
    })
    return result;
}

exports.deleteAccessKey = async function(client, accessKeyId, username) {
    
    var params = {
        AccessKeyId: accessKeyId,
        UserName: username
    };
    
    var result = await new Promise((resolve, reject) => {
        client.deleteAccessKey(params, function(err, data) {
            if (err) {
                // throw (err, err.stack); // an error occurred
                reject(err)
            }
            else {
                console.log("deleted access key: " + accessKeyId)
                console.log(data);      // successful response
                resolve(data);
            }
        });
    })
    return result;
}

async function getIamClient() {
    return await new Promise((resolve, reject) => {
        if(!iamClient) {
            console.log("connecting to iam client the first time")
            stsService.getCrossAccountCredentials().then((data) => {
                console.log("sts data: ")
                console.log(data)
                // iamClient = new aws.IAM(test);
                iamClient = new aws.IAM(data);
                // console.log("iamClient: ")
                // console.log(iamClient)
                resolve(iamClient)
            }, (err) => {
                console.log(err)
                reject(err)
            })
            
        } else {
            console.log("reuse existing iam client")
            resolve(iamClient)
        } 
    });
}