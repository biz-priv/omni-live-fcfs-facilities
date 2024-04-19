import json
import csv 
import boto3
import time
import os
import requests
from datetime import datetime, timedelta
from src.shared.dynamo import query_dynamodb
env = os.environ['Environment']
username = os.environ['Username']
password = os.environ['Password']
mcleod_headers = {'Accept': 'application/json',
                    'Content-Type': 'application/json'}

INTERNAL_ERROR_MESSAGE = "Internal Error."

def lambda_handler(event, context):
    print("event:",event)   
    for item in event["Payload"]:
        order_id=item['item']["order_id"]
        order_info = validate_order(order_id)
        if not order_info or order_info['status']['S'] == 'Rejected':
            output=get_order(order_id)
            print("ids",order_id,os.environ['Environment'])
            response=get_orders(output)
            # Update status based on response
            if response == 200:
                status = 'Accepted'
            else:
                status = 'Rejected'
            # Store data in DynamoDB
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(os.environ['Dynamo_Table'])
            table.put_item(
                Item={
                    'order_id': order_id,
                    'status': status
                }
                    )
            
        return {
            'statusCode': 200,
            'body': json.dumps('Succeeded')
        }

def get_location_info(location_id):
    url = f"https://tms-lvlp.loadtracking.com:6790/ws/api/locations/{location_id}"
    response = requests.get(url, auth=(username, password), headers=mcleod_headers)
    #with open(r'C:\Users\andre\Downloads\json1.json', 'w', encoding='utf-8') as f:
    #    json.dump(response.json(), f, ensure_ascii=False, indent=4)
    output = response.json()
    try:
        fcfs_facility = output['fcfs']
    except:
        output['fcfs'] = False
        fcfs_facility = output['fcfs']
    return output

def get_order(order_id):
    if env=='dev':
        get_url3 = f"https://tms-lvlp.loadtracking.com:6790/ws/orders/{order_id}"
    else:
        get_url3 = f"https://tms-lvlp.loadtracking.com/ws/orders/{order_id}"
    get_response3 = requests.get(get_url3, auth=(username, password), headers=mcleod_headers)
    get_output3 = get_response3.json()
    return get_output3

def get_orders(output):
    
    # check to see if order has already been updated
    is_what_we_want = False
    order_id = output['id']
    num_of_stops = len(output['stops'])
    for stop in output['stops']:
        location_id = stop['location_id']
        location_name = stop['location_name']
        location_data = get_location_info(location_id)
        #if location_data['fcfs'] == False:
        if location_data['fcfs'] == True:
            appt_open = stop['sched_arrive_early']
            appt_open = datetime.strptime(appt_open, "%Y%m%d%H%M%S%z")
            try:
                appt_close = stop['sched_arrive_late']
                appt_close = datetime.strptime(appt_close, "%Y%m%d%H%M%S%z")
            except:
                appt_close = appt_open
            day_of_week = appt_open.strftime('%A').upper()
            if day_of_week == "MONDAY":
                day_open = "monday_open"
                day_close = "monday_close"
            elif day_of_week == "TUESDAY":
                day_open = "tuesday_open"
                day_close = "tuesday_close"
            elif day_of_week == "WEDNESDAY":
                day_open = "wednesday_open"
                day_close = "wednesday_close"
            elif day_of_week == "THURSDAY":
                day_open = "thursday_open"
                day_close = "thursday_close"
            elif day_of_week == "FRIDAY":
                day_open = "friday_open"
                day_close = "friday_close"
            elif day_of_week == "SATURDAY":
                day_open = "saturday_open"
                day_close = "saturday_close"
            elif day_of_week == "SUNDAY":
                day_open = "sunday_open"
                day_close = "sunday_close"
            try:
                location_open = datetime.strptime(location_data[day_open], "%Y%m%d%H%M%S%z")
                location_close = datetime.strptime(location_data[day_close], "%Y%m%d%H%M%S%z")
                location_open = location_open.strftime("%H:%M")
                location_close = location_close.strftime("%H:%M")
                hours_open = location_open.split(":")[0]
                minutes_open = location_open.split(":")[1]
                hours_close = location_close.split(":")[0]
                minutes_close = location_close.split(":")[1]
                appt_open = appt_open.replace(hour=int(hours_open), minute=int(minutes_open))
                appt_close = appt_close.replace(hour=int(hours_close), minute=int(minutes_close))
                appt_open = appt_open.strftime("%Y%m%d%H%M%S%z")
                appt_close = appt_close.strftime("%Y%m%d%H%M%S%z")
                #print(appt_open)  
                #print(appt_close)
                stop['sched_arrive_early'] = appt_open
                stop['sched_arrive_late'] = appt_close
                stop['confirmed'] = True
                is_what_we_want = True
            except:
                pass
    if is_what_we_want == True:
        put_url = f"https://tms-lvlp.loadtracking.com:6790/ws/api/orders/update"
        put_response = requests.put(put_url, auth=(username, password), headers=mcleod_headers, json=output)
        print(put_response.status_code)
        return put_response.status_code
        # add updated order id to DB so that we don't update it again


def validate_order(order_id):
    try:
        response = query_dynamodb(os.environ['Dynamo_Table'],
                                'order_id = :order_id', {":order_id": {"S": order_id}})
        if not response['Items']:
            return False
        return response['Items'][0]
    except Exception as validate_error:
        print("ValidateDynamoDBError: %s",
                          json.dumps(validate_error))
        raise ValidateDynamoDBError(json.dumps(
            {"httpStatus": 501, "message": INTERNAL_ERROR_MESSAGE})) from validate_error
    
class ValidateDynamoDBError(Exception):
    pass