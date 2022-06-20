import json
import boto3
import time
import urllib.parse
import datetime
import os
import botocore
import urllib
import csv
from datetime import date
from botocore.exceptions import ClientError
from email.generator import Generator
from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

Current_Date_Formatted = datetime.datetime.today().strftime ('%Y-%m')
print("Current_Date_Formatted:",Current_Date_Formatted)

s3 = boto3.resource('s3')
client = boto3.client('s3')

print('Loading function')

def lambda_handler(event, context):
    
    s3_bucket = os.environ['S3_Bucket'] ## Change Bucket Name
    logger.info("S3 Bucket Name: - {}".format(s3_bucket))
    Prefix= os.environ['Prefix']
    logger.info("S3 Folder Prefix: - {}".format(Prefix))
    File = os.environ['File']
    logger.info("S3 Upload File: - {}".format(File))
    FileType=os.environ['FileType']
    logger.info("S3 Upload File Type: - {}".format(FileType))
    
    s3_key=Prefix+File+Current_Date_Formatted+FileType
    
    report_name= File+Current_Date_Formatted+FileType
    logger.info("S3 Bucket Name: - {}".format(s3_bucket))
    logger.info("S3 Key: - {}".format(s3_key))
    logger.info("report_name: - {}".format(report_name))
    
    download_uri = "s3://" + s3_bucket + "/" + s3_key
    download_report = "/tmp/" + report_name
    print("Downloading AgedSnapshot Report from S3 bucket to ", download_report);
    
    try:
        s3.meta.client.download_file(s3_bucket, s3_key, download_report)
        print("Done.")
        RowList=[]
        AMIList=[]
        SnapshotList=[]
        with open(download_report, "r") as csvfile:
            spamreader = csv.reader(csvfile, delimiter=",")
            for row in spamreader:
                currentrow=', '.join(row)
                RowList.append(currentrow)
                #RowList.
                #AllList.append(RowList)
                splitrow=currentrow.split(",")
                #print("splitrow",splitrow[1])
                if len(splitrow[1])>0:
                   AMIList.append(splitrow[1]) 
                   if splitrow[1] == ' ':
                      SnapshotList.append(splitrow[0])
        AMIFinalList = [ele for ele in AMIList if ele != ' '] 
        AMIFinalList.pop(0)
        print("FinalList List::::",AMIFinalList) 
        print("EBS snapsohts:::",SnapshotList)
        for imageid in AMIFinalList:
            #response = client.deregister_image(ImageId=imageid)
            print("Successfully Deregister ImageId:::::",imageid)
        for SnapshotID in SnapshotList:
            #response = client.delete_snapshot(SnapshotId='string')
            print("Successfully Deleted SanpshotID:::::",SnapshotID)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
        
    # Send email using SES with attachment
    
    msg = MIMEMultipart()
    msg["Subject"] = "This is an email with an attachment!"
    Sender = os.environ['Sender']
    Receiver=os.environ['Receiver']
    logger.info("Sender: - {}".format(Sender))
    logger.info("Receiver: - {}".format(Receiver))
    msg["From"] = Sender      ## Modify to your "From" Address
    msg["To"] = Receiver        ## Modify to your "To" Address
    listtoemail=[]
    listtoemail.append(msg['To'])
    print(listtoemail)
    # Set message body

    html = """<html>
                <head></head>
                <body>
                  <p>Hi <br><br>
                    Attached list of Kantar AWS Aged Snapshot Cleandup. <br><br><br
                    Thank you <br>
                    KyndrylCloudOps <br><br>
                    This is an automatic generated email, Please reachout to '<a href="kantar-aws-support@kyndryl.com">KyndrylCloudOps</a>' for any support/concerns.<br>
                  </p>
                </body>
                </html>
                            """                      
    body = MIMEText(html, 'html')
    msg.attach(body)
    with open(download_report, "rb") as attachment:
        part = MIMEApplication(attachment.read())
        part.add_header("Content-Disposition",
                        "attachment",
                        filename=report_name)
    msg.attach(part)

    # Convert message to string and send
    ses_client = boto3.client("ses", region_name="us-east-1")
    response = ses_client.send_raw_email(
        Source=msg['From'],
        Destinations=listtoemail,
        RawMessage={"Data": msg.as_string()}
    )
    print(response)
    print("Successfully sent email with report attachment")
