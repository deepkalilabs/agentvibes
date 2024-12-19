import os
import shutil
import boto3
import sh
import re
from botocore.exceptions import ClientError
from .helpers.ecr_manager import ECRManager
import json
import uuid
import logging
from datetime import datetime
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
from supabase import Client
from helpers.supabase.client import get_supabase_client
supabase: Client = get_supabase_client()

class LambdaGenerator:
    # TODO: Dynamically generate IAM roles.
    def __init__(self, code_chunk_dirty: str, user_id: str, notebook_name: str, notebook_id: str, dependencies: str):
        self.code_chunk_dirty = code_chunk_dirty
        self.user_id = user_id
        self.notebook_name = notebook_name.split('.')[0]
        self.lambda_fn_name = f"{user_id}_{self.notebook_name}_lambda"
        self.api_name = f"{user_id}_{self.notebook_name}_api"
        self.notebook_id = notebook_id
        self.lambda_zip_folder = ''
        self.code_chunk_clean = ''
        # TODO: Make a base lambda layer for basic dependencies.
        self.dependencies = dependencies
        self.lambda_handler = 'lambda_function.lambda_handler'
        
        self.base_folder_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "lambda_dumps",
            self.lambda_fn_name
        )

        self.helper_script_path = os.path.join(
            os.path.dirname(__file__),
            "helpers",
            "scripts"
        )
        
        self.aws_role_identifier = os.environ.get("AWS_ROLE_IDENTIFIER")
        self.region = os.environ.get("AWS_REGION")
        
        self.ecr_manager = ECRManager(self.lambda_fn_name, self.base_folder_path)
        
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        
        self.api_gateway_client = boto3.client('apigateway')

        self.lambda_fn_arn = ''
        self.api_id = ''
        self.api_root_id = ''
        self.submit_endpoint_id = ''
        self.status_endpoint_id = ''
        self.result_endpoint_id = ''
        self.submit_endpoint = ''
        
        if os.path.exists(self.base_folder_path):
            shutil.rmtree(self.base_folder_path)
        os.makedirs(self.base_folder_path)
        logger.info(f"Initialized LambdaGenerator for user {user_id} and notebook {notebook_name}")
    
    @property
    def ARN(self):
        iam = boto3.client('iam')
        response = iam.get_role(RoleName=self.aws_role_identifier)
        arn = response['Role']['Arn']
        logger.debug(f"Retrieved ARN: {arn}")
        return arn
    
    @property
    def account_id(self):
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        logger.debug(f"Retrieved account ID: {account_id}")
        return account_id

    
    def save_lambda_code(self):
        #TODO: Use LLM gods to generate this code
        lambda_header_code = open(os.path.join(self.helper_script_path, 'lambda_header_code.py'), 'r').read()
        trigger_code_path = os.path.join(self.helper_script_path, 'lambda_trigger_code.py')
        trigger_code = open(trigger_code_path, 'r').read()
        self.code_chunk_clean = lambda_header_code + '\n' + self.code_chunk_dirty + '\n' + trigger_code
        
        with open(os.path.join(self.base_folder_path, 'lambda_function.py'), 'w') as f:
            f.write(self.code_chunk_clean)
            
        logger.info("Lambda code saved successfully")
        return self.code_chunk_clean
    
    def prepare_container(self):
        with open(os.path.join(self.base_folder_path, 'requirements.txt'), 'w') as f:
            f.write(self.dependencies)
            
        docker_file_sample = open(os.path.join(self.helper_script_path, 'dockerfile_sample'), 'r').read()
        
        with open(os.path.join(self.base_folder_path, 'Dockerfile'), 'w') as f:
            f.write(docker_file_sample)
            
        logger.info("Container preparation completed")
            
    def build_and_push_container(self):
        logger.info("Starting container build and push")
        self.image_uri = self.ecr_manager.build_and_push_image()
        logger.info(f"Container built and pushed with URI: {self.image_uri}")

    def create_lambda_fn(self):
        """
        Create or update AWS Lambda function using boto3.
        """    
        try:
            self.lambda_client.delete_function(
                FunctionName=self.lambda_fn_name
            )
            logger.info(f"Successfully deleted Lambda function: {self.lambda_fn_name}")
        except ClientError as e:
            logger.warning(f"Lambda function not found: {str(e)}")
            
        logger.info(f"Creating new Lambda function: {self.lambda_fn_name}")
        response = self.lambda_client.create_function(
            FunctionName=self.lambda_fn_name,
            PackageType='Image',
            Role=self.ARN,
            Code={
                'ImageUri': self.image_uri
            },
            Timeout=900,  # 15 minutes
            MemorySize=1024,
            Environment={
                'Variables': {
                    'ASYNC_MODE': 'true'
                }
            }
        )
        
        self.lambda_fn_arn = response['FunctionArn']
        logger.info(f"Lambda function created with ARN: {self.lambda_fn_arn}")
        return response
        
    def delete_existing_api(self):
        """Delete API if it exists with the same name"""
        try:
            # List all APIs
            apis = self.api_gateway_client.get_rest_apis()
            
            # Find API with matching name
            for api in apis['items']:
                if api['name'] == self.api_name:
                    logger.info(f"Deleting existing API: {api['name']} ({api['id']})")
                    self.api_gateway_client.delete_rest_api(
                        restApiId=api['id']
                    )
                    # Wait a bit after deletion (API Gateway has eventual consistency)
                    # time.sleep(30)
        except Exception as e:
            logger.error(f"Error checking/deleting existing API: {str(e)}")
            
    def create_submit_endpoint(self):
        logger.info("Creating submit endpoint")
        
        # Step 1: Create the resource
        submit_endpoint_resource = self.api_gateway_client.create_resource(
            restApiId=self.api_id,
            parentId=self.api_root_id,
            pathPart='submit'
        )
        submit_endpoint_resource_id = submit_endpoint_resource['id']
        
        # Step 2: Set up method with JSON validation
        self.api_gateway_client.put_method(
            restApiId=self.api_id,
            resourceId=submit_endpoint_resource_id,
            httpMethod='POST',
            authorizationType='NONE',
            apiKeyRequired=False,
            requestModels={
                'application/json': 'JSONModel'
            },
            requestValidatorId=self.validator_id
        )

        requestTemplateBody = f'''{{
            "body": $input.json('$'),
            "request_id": "$context.requestId",
            "notebook_id": "{self.notebook_id}",
            "timestamp": "$context.requestTimeEpoch"
        }}'''

        # Step 3: Configure integration with async Lambda invocation
        self.api_gateway_client.put_integration(
            restApiId=self.api_id,
            resourceId=submit_endpoint_resource_id,
            httpMethod='POST',
            type='AWS',  # AWS type for custom response mapping
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{self.lambda_fn_arn}/invocations',
            requestTemplates={
                'application/json': requestTemplateBody
            },
            requestParameters={
                'integration.request.header.X-Amz-Invocation-Type': "'Event'"
            },
            passthroughBehavior='WHEN_NO_TEMPLATES'
        )
        
        # Step 4: Add method response for 202 Accepted
        self.api_gateway_client.put_method_response(
            restApiId=self.api_id,
            resourceId=submit_endpoint_resource_id,
            httpMethod='POST',
            statusCode='202',
            responseModels={
                'application/json': 'Empty'
            },
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': True,
                'method.response.header.Access-Control-Allow-Headers': True
            }
        )
        
        # Step 5: Add integration response
        self.api_gateway_client.put_integration_response(
            restApiId=self.api_id,
            resourceId=submit_endpoint_resource_id,
            httpMethod='POST',
            statusCode='202',
            selectionPattern='',  # Empty pattern matches successful lambda invocations
            responseTemplates={
                'application/json': json.dumps({
                    'request_id': "$context.requestId",
                    'status': 'SUBMITTED',
                    'submitted_at': "$context.requestTimeEpoch"
                })
            },
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'",
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
            }
        )
        
        # Step 6: Add Lambda permission
        self.lambda_client.add_permission(
            FunctionName=self.lambda_fn_arn,
            StatementId=f'APIGateway-{self.api_name}-{uuid.uuid4()}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{self.region}:{self.account_id}:{self.api_id}/*/*/submit'
        )
        
        logger.info(f"Submit endpoint created with ID: {submit_endpoint_resource_id}")
        return submit_endpoint_resource_id
        
    def create_api_endpoint(self):
        try:
            # self.delete_existing_api()
            logger.info(f"Creating API endpoint for {self.api_name}")
            api = self.api_gateway_client.create_rest_api(
                name=self.api_name,
                description=f"Async API Gateway for {self.lambda_fn_name}",
                endpointConfiguration={
                    'types': ['REGIONAL']
                }
            )
            
            self.api_id = api['id']
            
            validator = self.api_gateway_client.create_request_validator(
                restApiId=self.api_id,
                name='ValidateJSON',
                validateRequestBody=True,
                validateRequestParameters=True
            )
            self.validator_id = validator['id']
            
            self.api_gateway_client.create_model(
                restApiId=self.api_id,
                name='JSONModel',
                contentType='application/json',
                schema=json.dumps({
                    "$schema": "http://json-schema.org/draft-04/schema#",
                    "type": "object"
                })
            )
                    
            resources = self.api_gateway_client.get_resources(restApiId=self.api_id)
            self.api_root_id = resources['items'][0]['id']
            
            self.submit_endpoint_id = self.create_submit_endpoint()
            logger.info(f"Created submit endpoint with ID: {self.submit_endpoint_id}")
            
            self.api_gateway_client.create_deployment(
                restApiId=self.api_id,
                stageName='prod'
            )
            
            self.submit_endpoint = f'https://{self.api_id}.execute-api.{self.region}.amazonaws.com/prod/submit'

            logger.info(f"API endpoints created successfully: submit={self.submit_endpoint}")

            self.store_endpoint_supabase()
            
            return True, self.submit_endpoint
            
        except Exception as e:
            logger.error(f"Error creating API endpoint: {str(e)}")
            return False, str(e)

            # {
            #   "csv_file_uri": "s3://llm-data-viz-agentkali/data_uploads/00328009-93c5-4816-93f5-b33ce9aea716.csv"
            # }
            
    def store_endpoint_supabase(self):
        supabase.table('notebooks').update({
            'submit_endpoint': self.submit_endpoint,
            'updated_at': datetime.now().isoformat()
        }).eq('id', self.notebook_id).execute()
        

# if __name__ == "__main__":
#     pass
#     # Your code as a string
#     #TODO: think about how to pass args here.
#     code_str = '''
#     def hello_world(name: str): 
#         return f"Hello {name}"
#     print(hello_world("om"))
    
#     def lambda_handler(event, context):
#         # Place your existing code here
#         result = hello_world()
#         return result
#     '''