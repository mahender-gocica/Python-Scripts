import json
import boto3
import time
import urllib.parse
import datetime
import os
import botocore
import urllib

from datetime import date
from botocore.exceptions import ClientError
from email.generator import Generator
from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import logging

# Log Debugging configurations
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logging.basicConfig(filename='SanpshotAMILogFile.log', filemode='w', format='%(asctime)s %(message)s', level=logging.DEBUG)

Current_Date_Formatted = datetime.datetime.today().strftime ('%Y-%m')
logger.info("Current_Date_Formatted: - {}".format(Current_Date_Formatted))

s3 = boto3.resource('s3')
client = boto3.client('s3')

print('Loading function')

def lambda_handler(event, context):
    # TODO implement
    logger.info("event: - {}".format(event))
    apiEndpoint = event['APIGatewayEndpoint']
    logger.info("API Endpoint:: - {}".format(apiEndpoint))
    executionName = event['ExecutionContext']['Execution']['Name']
    logger.info("executionName:: - {}".format(executionName))
    statemachineName = event['ExecutionContext']['StateMachine']['Name']
    logger.info("statemachineName:: - {}".format(statemachineName))
    taskToken = event['ExecutionContext']['Task']['Token']
    logger.info("taskToken:: - {}".format(taskToken))
    approveEndpoint = apiEndpoint + "/execution?action=approve&ex=" + executionName + "&sm=" + statemachineName + "&taskToken=" + urllib.parse.quote(taskToken, safe='')
    logger.info("approveEndpoint:: - {}".format(approveEndpoint))
    
    rejectEndpoint = apiEndpoint + "/execution?action=reject&ex=" + executionName + "&sm=" + statemachineName + "&taskToken=" + urllib.parse.quote(taskToken, safe='')
    logger.info("rejectEndpoint:: - {}".format(rejectEndpoint))
    
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
    logger.info("Downloading AgedSnapshot Report from S3 bucket to: - {}".format(download_report))
    
    try:
        s3.meta.client.download_file(s3_bucket, s3_key, download_report)
        logger.info("Downloaded AgedSnapshot Report from S3 bucket to: - {}".format(download_report))
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            logging.debug("The object does not exist{}".format(e))
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
    logger.info("listtoemail: - {}".format(listtoemail))
    # Set message body

    html = """<html>
                <head></head>
                <body>
                  <p>Hi <br><br>
                    Kantar AWS Aged Snapshot Details. Below are approvals and Reject Links <br>
                    Approval Link: '<a href="%s">Approve</a>' <br>
                    Reject Link: '<a href="%s">Reject</a>' <br><br>
                    Thank you <br>
                    ec-devops <br><br>
                    This is an automatic generated email, Please reachout to '<a href="kantar-aws-support@kyndryl.com">Kyndryl DevOps IT</a>' for any support/concerns.<br>
                  </p>
                </body>
                </html>
                            """ %(approveEndpoint, rejectEndpoint )                       
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
    logger.info("Email Response: - {}".format(response))
    logger.info("Successfully sent email with report attachment")
