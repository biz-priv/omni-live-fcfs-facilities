import logging
import json
import boto3

# Initialize the AWS SDK
dynamodb = boto3.client('dynamodb')

INTERNAL_ERROR_MESSAGE = "Internal Error."

def query_dynamodb(table_name, expression, attributes):
    try:
        response = dynamodb.query(
            TableName=table_name,
            KeyConditionExpression=expression,
            ExpressionAttributeValues=attributes
        )
        print("DynamoDB query response: {}".format(json.dumps(response)))
        return response
    except Exception as query_dynamodb_error:
        logging.exception("DynamoDBQueryError: %s", query_dynamodb_error)
        raise DynamoQueryError(json.dumps(
            {"httpStatus": 501, "message": INTERNAL_ERROR_MESSAGE})) from query_dynamodb_error
    

class DynamoQueryError(Exception):
    pass