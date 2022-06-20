
###########################################################################################################################
#Author: Mahender Gocica <mahender.gocica@kyndryl.com>
#Version: 0.1
#Description: Script is used for Fetching the one year old AWS Cloud EBS Volume Snapshots, AMI and associated Snapshots.
# 1. Conect to specific AWS Cloud Reagions [us-east-1 and eu-west-1]
# 2. Based on condition No.Of Days it will Identify the Aged Sanpshots (EBS and AMI Associated Snapshots).
# Permission
# 3. Send attached list of Aged Snapshots over email to business to review and get approvals to Cleanup the Aged AMI's and Snapshots.
# #########################################################################################################################
import json
import boto3
import re
import csv
import os
from datetime import datetime
from datetime import timedelta, timezone
from dateutil.relativedelta import relativedelta
import time
import smtplib
import sys
from io import StringIO
from email.generator import Generator
from os.path import basename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import sys
import logging
import botocore
from botocore.exceptions import ClientError

# Log Debugging configurations
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logging.basicConfig(filename='SanpshotAMILogFile.log', filemode='w', format='%(asctime)s %(message)s', level=logging.DEBUG)
Current_Date_Formatted=datetime.today().strftime('%Y-%m')
logger.info("Current_Date_Formatted: - {}".format(Current_Date_Formatted))

amis = {}
amidnd = []
AMIMorethenOneYearList=[]
InstanceImageID=""
used_amis=[]
ImageAMIIDs=[]
SnapshotID_NonAttachedtoAMI=[] 
csvDataListMainUniqList=[]

def lambda_handler(event, context): 
    try:
        # Variable Declaration
        path="/tmp/"
        s3_bucket = os.environ['S3_Bucket'] ## Change Bucket Name
        logger.info("S3 Bucket Name: - {}".format(s3_bucket))
        Prefix= os.environ['Prefix']
        logger.info("S3 Folder Prefix: - {}".format(Prefix))
        File = os.environ['File']
        logger.info("S3 Upload File: - {}".format(File))
        FileType=os.environ['FileType']
        logger.info("S3 Upload File Type: - {}".format(FileType))
        SnapshotAge=os.environ['SnapshotAge']
        logger.info("SnapshotAge: - {}".format(SnapshotAge))
        s3_key=Prefix+File+Current_Date_Formatted+FileType
        report_name= File+Current_Date_Formatted+FileType
        logger.info("S3 Bucket Name: - {}".format(s3_bucket))
        logger.info("S3 Key: - {}".format(s3_key))
        logger.info("report_name: - {}".format(report_name))
        SnapshotFileName=File+Current_Date_Formatted+FileType
        lambda_path ="/tmp/"+SnapshotFileName
        s3_path=Prefix+SnapshotFileName
        
        regions=['us-east-1','eu-west-1']
        s3 = boto3.resource('s3',"eu-west-1")
        s3_client = boto3.client('s3',"eu-west-1")
        logger.info("In IdentifyAgedSnapshots Function!!!")
        logger.info("In SnapshotFileName!!! - {}".format(SnapshotFileName))
        with open(lambda_path, 'w+') as csvFile:
            try:
                writer = csv.writer(csvFile)
                writer.writerow(['SnapshotId', 'AMIID','ImageName',"Snapshot Creation Date","SnapshotSize","Region"])
                # Get all the snapshot and AMI details by connecting to each region with EC2 Client
                for region in regions:
                    csvDataListMainList = []
                    csvDataListMainUniqList = []
                    client = boto3.client('ec2',region_name=region)
                    ami_response = client.describe_images(Owners=['self'])
                    snapshot_response = client.describe_snapshots(OwnerIds=['self'])
                    autoscaling = boto3.client('autoscaling')
                    lc_response = autoscaling.describe_launch_configurations()
                    
                    #AutoScalling AMI Information
                    for ami in lc_response['LaunchConfigurations']:
                        amidnd.append(ami['ImageId'])
                    logger.info('AWS Connected to fetch Snapshot details- {}'.format(region))
                    snapshots = client.describe_snapshots(OwnerIds=['self'])
                    images = client.describe_images(Owners=['self'])
                    #Get the each snapshot details and identify which are created more than 365 days.
                    instances = client.describe_instances()
                    for reservation in instances['Reservations']:
                        for instance in reservation['Instances']:
                            used_amis.append(instance['ImageId'])
                    for i in range(len(snapshots['Snapshots'])):
                        delete_time = ""
                        StartTime = snapshots['Snapshots'][i]['StartTime']
                        try:
                           delete_time = datetime.now(tz=timezone.utc) - timedelta(days=int(SnapshotAge))
                        except ValueError as e:
                            logging.error('If any ValueError Excptions - {}'.format(e))   
                        # Idenditifying AMI's which are created more than one year along with AMI and associated Snapshot details 
                        if (delete_time.date() > StartTime.date()):
                                SnapshotId = snapshots['Snapshots'][i]['SnapshotId']
                                VolumeSize=snapshots['Snapshots'][i]['VolumeSize']
                                '''Clean abandon ebs snapshots of which no AMI has been found'''
                                snapdndids = []
                                csvDataList = []
                                AMISnapshotIDList=[]
                                ImageIDList=[]
                                BlockSanpshotIDlist=[]
                                for image in images:
                                    if image == "ResponseMetadata":
                                        mylist = len(images['Images'])
                                        for i in range(mylist):
                                            interlist = []
                                            creation_date =  images['Images'][i]['CreationDate']
                                            BlockDeviceMappings =  images['Images'][i]["BlockDeviceMappings"]
                                            imgageid = images['Images'][i]['ImageId']
                                            # try:
                                            #     ec2 = boto3.resource('ec2',region)
                                            #     image2 = ec2.Image(imgageid,region)
                                            #     logger.info("lastLaunchedTime::::image2::::",image2)
                                            #     #response2 = image2.describe_attribute(Attribute='lastLaunchedTime')
                                            #     #logger.info("lastLaunchedTime::::::::",response2)
                                            # except IndexError as error:
                                            #     # Output expected IndexErrors.
                                            #     logger.info("lastLaunchedTime::::error::::{}".format(error))
                                            #     #logging.log_exception(error)
                                            # except Exception as exception:
                                            #     # Output unexpected Exceptions.
                                            #     #logging.log_exception(exception, False)  
                                            #     logger.info("lastLaunchedTime::::exception::::{}".format(exception))
                                            ImageIDList.append(imgageid)
                                            Name=  images['Images'][i]['Name']
                                            delete_time=""
                                            try:
                                                s = creation_date
                                                f = "%Y-%m-%dT%H:%M:%S.%fZ"
                                                creation_date_date = datetime.strptime(s, f)
                                                delete_time = datetime.now(tz=timezone.utc) - timedelta(days=int(SnapshotAge))
                                            except ValueError as e:
                                                logging.error('If any ValueError Excptions - {}'.format(e)) 
                                            if len(BlockDeviceMappings) > 1 and (delete_time.date() > creation_date_date.date()): 
                                                
                                                for j in range(len(BlockDeviceMappings)):
                                                    BlockSanpshotIDEBS =images['Images'][i]["BlockDeviceMappings"][j]
                                                    if "Ebs" in BlockSanpshotIDEBS:
                                                        AMISanpshotID =images['Images'][i]["BlockDeviceMappings"][j]["Ebs"]["SnapshotId"]
                                                        AMISnapshotIDList.append(AMISanpshotID)
                                                        #Adding More than 1 year AMI ID's to List for Deregister AMIs
                                                        AMIMorethenOneYearList.append(imgageid)
                                                        if SnapshotId == AMISanpshotID and (imgageid not in used_amis):
                                                            csvDataList.append(AMISanpshotID)
                                                            csvDataList.append(imgageid)
                                                            csvDataList.append(Name)
                                                            ImageAMIIDs.append(imgageid)
                                                            csvDataList.append(creation_date_date.date())
                                                            csvDataList.append(VolumeSize)
                                                            csvDataList.append(region)
                                                            csvDataListMainList.append(csvDataList) 
                                                        else:
                                                            pass
 
                                # # # Below condition is to add the Snapsohts details which are not in AMI snapshot ID's List
                                if SnapshotId not in AMISnapshotIDList:
                                    try:
                                        img = client.describe_images(Filters=[{'Name': 'block-device-mapping.snapshot-id', 'Values': [SnapshotId]}])
                                        if (len(img['Images']) > 0):
                                            ami_id = img['Images'][0]['ImageId']
                                            print("Snapshot(" + SnapshotId + ") is associated to image(" + ami_id + "). Return True")
                                            
                                        else:
                                            logger.info('Else - {}')
                                            locallist=[]
                                            print("Snapshot(" + SnapshotId + ") is not associated to any image. Return False")
                                            locallist.append(SnapshotId)
                                            locallist.append("")
                                            locallist.append("")
                                            locallist.append(StartTime.date())
                                            locallist.append(VolumeSize)
                                            locallist.append(region)
                                            csvDataListMainList.append(locallist)
                                    except botocore.exceptions.ClientError as error:
                                            if error.response['Error']['Code'] == 'InvalidSnapshot.InUse':
                                                logger.info('SnapShotId '+SnapshotId+' is already being used by an AMI')
                                            else:
                                                logger.info("In ELSE ELSE::::::::")
                                                pass
                                    logger.info('Final List -- csvDataListMainList-- of Snapshot Details - {}'.format(csvDataListMainList))
                                else:
                                    pass
                                                
                                csvDataListMainUniqList = []
                                for ele in csvDataListMainList:
                                    if set(ele) not in [set(x) for x in csvDataListMainUniqList]:
                                        csvDataListMainUniqList.append(ele)
                    logger.info('Print Final List -- csvDataListMainList-- of Snapshot Details - {}'.format(csvDataListMainList))
                    logger.info('Print Final List--csvDataListMainUniqList-- of Snapshot Details - {}'.format(csvDataListMainUniqList))
                    #Writing Data into output file
                    for csvInfo in csvDataListMainUniqList:
                        writer.writerow(csvInfo)
            except Exception as exception:
                    logging.error('If any Exception occure - {}'.format(exception))
                
        logging.info('Snapshot Details Collected - {}')
        csvFile.close()
        try:
           response = s3_client.upload_file(lambda_path, s3_bucket, s3_path)
           logger.info('Snapshot Uploaded Successfully!!')
        except ClientError as e:
            logging.error(e)
            return False
        return {
                'statusCode': 200,
                'body': json.dumps('Lambda execution completed')
            }    
    
    except Exception as exception:
         # Output unexpected Exceptions.
         logging.error('If any exceptions  - {}'.format(exception)) 
        
