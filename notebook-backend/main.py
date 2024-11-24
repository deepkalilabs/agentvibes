from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
from jupyter_client import KernelManager
import os
from pydantic import BaseModel
import ssl
from pprint import pprint
from lambda_generator.generate_lambda_fn import LambdaGenerator
import sh
from jupyter_client.kernelspec import KernelSpecManager
import sys
from io import StringIO

app = FastAPI()

class OutputExecutionMessage(BaseModel):
    type: str
    cellId: str
    output: str

class OutputSaveMessage(BaseModel):
    type: str
    success: bool
    message: str

class OutputLoadMessage(BaseModel):
    type: str
    success: bool
    message: str
    cells: list
    
class OutputGenerateLambdaMessage(BaseModel):
    type: str
    success: bool
    message: str

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to manage kernels per session
sessions = {}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    print(f"New connection with session ID: {session_id}")
    
    await websocket.accept()
    
    print(f"New connection with session ID: {session_id}")

    if session_id not in sessions:
        # Start a new kernel for the session
        user_id = 1
        env_name = f"venv_kernel_{user_id}"
        curr_envs = {os.path.basename(env): env for env in json.loads(sh.conda("env", "list", "--json"))['envs']}
        relevant_env_path = curr_envs[env_name]
        relevant_env_path_python = os.path.join(relevant_env_path, "bin", "python3")
        
        if env_name not in curr_envs:
            sh.conda(
                "create", "-n", env_name, "python=3.9", "ipykernel",
                _out=sys.stdout, _err=sys.stderr, force=True
            )
        try:
            sh.Command(relevant_env_path_python)(
                "-m", "ipykernel", "install", 
                "--user", "--name", env_name, "--display-name", env_name,
                _out=sys.stdout, _err=sys.stderr)
            
        except sh.ErrorReturnCode as e:
            print(f"Error installing kernel: {e}")
        
        ksm = KernelSpecManager()
        
        if env_name not in ksm.find_kernel_specs():
            raise ValueError(f"Kernel '{env_name}' not found.")
        
        km = KernelManager(kernel_name=env_name)
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        sessions[session_id] = {'km': km, 'kc': kc}
    else:
        kc = sessions[session_id]['kc']

    try:
        while True:
            data = await websocket.receive_json()
            
            print(f"Received data: {data}\n\n")
            if data['type'] == 'execute':
                code = data['code']
                output = await execute_code(kernel_client=kc, relevant_env_path=relevant_env_path, code=code)

                print(f"Sending output: {output}, type: {type(output)}, cellId: {data['cellId']}\n\n")
                msgOutput = OutputExecutionMessage(type='output', cellId=data['cellId'], output=output)
                await websocket.send_json(msgOutput.model_dump())
            
            elif data['type'] == 'save_notebook':
                response = await save_notebook(data)
                print("response", response)
                response = OutputSaveMessage(type='notebook_saved', success=response['success'], message=response['message'])
                await websocket.send_json(response.model_dump())
                
            elif data['type'] == 'load_notebook':
                response = await load_notebook(data['filename'])
                response = OutputLoadMessage(type='notebook_loaded', success=response['status'] == 'success', message=response['message'], cells=response['notebook'])
                await websocket.send_json(response.model_dump())
                
            elif data['type'] == 'deploy_lambda':
                # TODO: Better dependency management here.
                # TODO: Get status/msg directly from function.
                dependencies = await execute_code(kernel_client=kc, relevant_env_path=relevant_env_path, code='!pip freeze')
                lambda_handler = LambdaGenerator(data['allCode'], 1, data['notebookName'], dependencies)
                status = False

                msg = "Processing the notebook"
                response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=msg)
                await websocket.send_json(response.model_dump())
                lambda_handler.save_lambda_code()

                msg = "Preparing your code for prod"
                lambda_handler.prepare_container()
                response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=msg)
                await websocket.send_json(response.model_dump())
                
                msg = "Shipping your code to the cloud"
                lambda_handler.build_and_push_container()
                response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=msg)
                await websocket.send_json(response.model_dump())
                
                # msg = "Setting up your code to handle requests"
                response = lambda_handler.create_lambda_fn()
                # response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=msg)
                # await websocket.send_json(response.model_dump())
                
                msg = "Creating an API for you"
                response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=msg)
                await websocket.send_json(response.model_dump())
                
                status, message = lambda_handler.create_api_endpoint()
                response = OutputGenerateLambdaMessage(type='lambda_generated', success=status, message=message)
                await websocket.send_json(response.model_dump())
                
            msgOutput = ''
            
    except WebSocketDisconnect:
        pass
    finally:
        # Optionally, you can decide when to shut down the kernel
        pass
    
async def execute_code(kernel_client, relevant_env_path: str, code: str) -> str:
    try:
        if code.strip().startswith('!'):
            magic_command = code.split(" ")[0][1:]
            base_magic_command = code.split(" ")[1:]
            
            output_buffer = StringIO()
            error_buffer = StringIO()
            
            result = sh.Command(os.path.join(relevant_env_path, "bin", magic_command))(
                *base_magic_command,
                _out=output_buffer, _err=error_buffer
            )
            return output_buffer.getvalue()
        
    except Exception as e:
        return "Error in the magic command: " + str(e)
        
    kernel_client.execute(code)
    output = ""
    count = 0
    while True:
        print("waiting for message")
        try:
            msg = kernel_client.get_iopub_msg(timeout=1)
            msg_type = msg['header']['msg_type']
            content = msg['content']
            if msg_type == 'status' and content['execution_state'] == 'busy':
                print("execution busy")
                count += 1
                if count > 5:
                    continue
            if msg_type == 'stream':
                print("stream", content)
                output += content['text']
            elif msg_type == 'execute_result':
                print("execute_result", content)
                output += content['data']['text/plain']
            elif msg_type == 'error':
                print("error", content)
                output += '\n'.join(content['traceback'])
            elif msg_type == 'status' and content['execution_state'] == 'idle':
                # Execution finished
                output += '# Execution finished\n'
                break
            print(f"content: {content} \n\n")
        except Exception as e:
            if str(e).strip():
                print(f"error: {e} \n\n")
                count += 1
                if count > 10:
                    break
            continue
    return output

async def save_notebook(data: dict):
    try:
        notebook = data.get('cells')
        filename = data.get('filename')
        print("notebook", notebook)
        if not notebook:
            return {"success": False, "message": "No cells found in the file provided."}
        
        filepath = os.path.join('notebooks', filename)
        with open(filepath, 'w') as f:
            json.dump(notebook, f)
        print(f"Saved notebook to {filepath}")
        return {"success": True, "message": "Notebook saved successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def load_notebook(filename: str):
    filepath = os.path.join('notebooks', filename)
    if not os.path.exists(filepath):
        return {"status": "error", "message": "Notebook not found.", "notebook": []}
    with open(filepath, 'r') as f:
        notebook = json.load(f)
    if not notebook:
        return {"status": "error", "message": "Notebook is empty.", "notebook": []}
    return {"status": "success", "notebook": notebook, "message": "Notebook loaded successfully."}

# Endpoint for "one-click deploy" functionality
@app.post("/deploy")
async def deploy_app(data: dict):
    # Implement your deployment logic here
    # For example, you can package the notebook and deploy it to a server or cloud service
    return {"status": "success", "message": "Application deployed successfully."}

if __name__ == "__main__":
    if not os.path.exists('notebooks'):
        os.makedirs('notebooks')

    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        reload_excludes=[
            "lambda_dumps/**",
            "**/lambda_dumps/**",
            "**/lambda_function.py",              # Exclude any lambda_function.py
            "**/requirements.txt"                 # Exclude any requirements.txt
        ]
    )
    

