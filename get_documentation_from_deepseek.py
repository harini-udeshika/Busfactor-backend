import json
import os
from openai import OpenAI

def get_documentation_from_deepseek(user_prompt,send_progress):
    
    send_progress("Calling DeepSeek API...")
     
    api_key =os.getenv('DEEPSEEK_API_KEY')

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    system_prompt = """
    Analyze the xml input containing data of a github repository and generate a JSON formatted output according to given 
    json format below, which will help new developers to understand 
    the inner working of the code when onboarding. The "flowOfEvents" attribute defines what is the 
    flow when providing the functionality for the particular functionality(what classes and functions that will be invoked and all)

    EXAMPLE JSON OUTPUT:
    {
    "projectOverview":"",
    "moduleBreakdown": {
        "Components": {},
        "Views": {},
        "Global": {}
    },
    "keyWorkflows": {
        "MainAnalysisFlow": {},
        "DataProcessingFlow": {}
    },
    "keyFunctionalities": [
        {
        "functionality":"",
        "flowOfEvents":{}
        }
    ],
    "criticalDependencies": []
    }

    EXAMPLE FLOW OF EVENTS
    "flowOfEvents": {
            "PasswordResetManager.initiatePasswordReset()": "Initiates the password reset process.",
            "TokenGenerator.generateToken()": "Generates a password reset token.",
            "NotificationService.send()": "Sends the password reset token to the user.",
            "PasswordResetManager.validateResetToken()": "Validates the password reset token.",
            "PasswordResetManager.completePasswordReset()": "Completes the password reset process."}
    """
    send_progress("Calling DeepSeek API...")
    
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}]

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        response_format={
            "type": "json_object"
        }
    )
    send_progress("Response recieved!")
    content= json.loads(response.choices[0].message.content)
    return content
    # print(formatted_json)