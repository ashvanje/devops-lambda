console.log('Loading function');

const aws = require('aws-sdk');
const fs = require('fs');

const s3 = new aws.S3({ apiVersion: '2006-03-01' });
const sns = new aws.SNS({ apiVersion: '2010-03-31' });
const snsTopic = "arn:aws:sns:ap-southeast-1:215658305678:health-topic";

exports.handler = async (event, context) => {
    //console.log('Received event:', JSON.stringify(event, null, 2));

    // Get the object from the event and show its content type
    const bucket = "iast-ct1-backup";
    // const bucket = event.bucketName;
    const params = {
        Bucket: bucket
    };
    try {
        var noNewBackup = await s3.listObjectsV2(params).promise().then(data => {
            // console.log(data)
            // var content = data.Contents
            var mostRecentDate = new Date(Math.max.apply(null, data.Contents.map(function(e) {
                return new Date(e.LastModified);
            })));
            
            var date = new Date();
            var date7daysAgo = new Date(date.setDate(date.getDate() - 7));
            console.log("mostRecentDate: ", mostRecentDate);
            console.log("date7daysAgo", date7daysAgo);
            
            var noNewBackup = mostRecentDate < date7daysAgo
            console.log("7 days no new backup: ", noNewBackup);
            
            
            
            return noNewBackup;
            
            // //publish message if no new backup
            // publishToSns();
        });
        
        // console.log("noNewBackup: ", noNewBackup)
        //publish message if no new backup
        if(noNewBackup) {
            await publishToSns();
        }
        
        return "success"
    } catch (err) {
        console.log(err);
    }
};

async function publishToSns() {
    
    var content = fs.readFileSync("seeker_no_backup_alert_msg.txt", "utf8")
    
    
    content = content.replace("{date}", new Date())
    console.log("content: ", content)
    
    const params = {
        TopicArn: snsTopic,
        Subject: "Alert from DevSecOps: No new Seeker Backup in 7 days",
        Message: content,  
    };
    
    
    await sns.publish(params).promise().then(data => {
        console.log("publish message to sns")
        console.log(data);           // successful response
    })
    
}