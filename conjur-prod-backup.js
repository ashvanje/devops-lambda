console.log('Loading function');

const aws = require('aws-sdk');
const fs = require('fs');

const ssm = new aws.SSM();
const s3 = new aws.S3({ apiVersion: '2006-03-01' });
const sns = new aws.SNS({ apiVersion: '2010-03-31' });
const snsTopic = "arn:aws:sns:ap-southeast-1:215658305678:health-topic";

exports.handler = async (event, context) => {
    //console.log('Received event:', JSON.stringify(event, null, 2));

    // Get the object from the event and show its content type
    const bucket = "conjur-cp1-backup";
    // const bucket = event.bucketName;
    var date = new Date();
    var day1dayAgo = new Date(date.setDate(date.getDate() - 1)).getDate();
    day1dayAgo = day1dayAgo < 10? "0" + day1dayAgo : day1dayAgo
    console.log("query date: " + day1dayAgo)
    const params = {
        Bucket: bucket,
        Prefix: "p0/" + day1dayAgo //query the day of month
    };
    const ssmParam = {
      "ParameterFilters": [ 
          { 
             "Key": "Name",
             "Option": "Contains",
             "Values": ["-p0--" + day1dayAgo]
          }
      ]
    }
    try {
        var noNewParameters = await ssm.describeParameters(ssmParam).promise().then(data => {
                console.log(data)
                var parameterSize = data.Parameters.length
                var mostRecentDate = new Date(Math.max.apply(null, data.Parameters.map(function(e) {
                    return new Date(e.LastModifiedDate);
                }))); 
                
                var date = new Date();
                var date1dayAgo = new Date(date.setDate(date.getDate() - 2));
                console.log("mostRecentDate: ", mostRecentDate);
                console.log("date1dayAgo", date1dayAgo);
                
                var noNewBackup = mostRecentDate < date1dayAgo || parameterSize == 0
                console.log("1 hour no new backup: ", noNewBackup);
                
                return noNewBackup;
            });
                
        var noNewBackup = await s3.listObjectsV2(params).promise().then(data => {
            console.log(data)
            var mostRecentDate = new Date(Math.max.apply(null, data.Contents.map(function(e) {
                return new Date(e.LastModified);
            })));
            
            var date = new Date();
            var date1dayAgo = new Date(date.setDate(date.getDate() - 2));
            console.log("mostRecentDate: ", mostRecentDate);
            console.log("date1dayAgo", date1dayAgo);
            
            var noNewBackup = mostRecentDate < date1dayAgo
            console.log("1 day no new backup: ", noNewBackup);
            
            return noNewBackup;
            
        });
        
        // console.log("noNewBackup: ", noNewBackup)
        //publish message if no new backup
        if(noNewBackup) {
            await publishNoBackupToSns();
        } else {
            await publishSuccessfulBackupToSns();
        }
        
        return "success"
    } catch (err) {
        console.log(err);
    }
};

async function publishNoBackupToSns() {
    
    var content = fs.readFileSync("conjur_prod_no_backup_alert_msg.txt", "utf8")
    
    content = content.replace("{date}", new Date())
    console.log("content: ", content)
    
    const params = {
        TopicArn: snsTopic,
        Subject: "[ERROR] !!! Alert from DevSecOps: No new Conjur Prod Backup in 1 day",
        Message: content,  
    };
    
    await sns.publish(params).promise().then(data => {
        console.log("publish message to sns")
        console.log(data);           // successful response
    })
    
}

async function publishSuccessfulBackupToSns() {
    
    var content = fs.readFileSync("conjur_prod_successful_backup_alert_msg.txt", "utf8")
    
    content = content.replace("{date}", new Date())
    console.log("content: ", content)
    
    const params = {
        TopicArn: snsTopic,
        Subject: "Alert from DevSecOps: Successful Conjur Prod Backup in 1 day",
        Message: content,  
    };
    
    await sns.publish(params).promise().then(data => {
        console.log("publish message to sns")
        console.log(data);           // successful response
    })
    
}