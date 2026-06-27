import os
import sys
import argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import system_prompt
from call_function import available_functions, call_function

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if api_key is None:
    raise RuntimeError("GEMINI_API_KEY is missing!")

parser = argparse.ArgumentParser(description="Chatbot")
parser.add_argument("user_prompt", type=str, help="User prompt")
parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
args = parser.parse_args()

client = genai.Client(api_key=api_key)

messages: list[types.Content] = [
    types.Content(
        role="user",
        parts=[types.Part(text=args.user_prompt)]
    )
]

agent_resolved = False

for iteration in range(20):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=messages,
        config=types.GenerateContentConfig(
            tools=[available_functions],
            system_instruction=system_prompt,
            temperature=0
        ),
    )

    if response.usage_metadata is None:
        raise RuntimeError("API request failed: usage_metadata is missing.")

    if args.verbose:
        print(f"\n--- Iteration {iteration + 1} ---")
        print(f"User prompt: {args.user_prompt}")
        print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
        print(f"Response tokens: {response.usage_metadata.candidates_token_count}")

    if response.candidates:
        for candidate in response.candidates:
            if candidate.content:
                messages.append(candidate.content)

    if response.function_calls:
        function_results = []
        
        for function_call in response.function_calls:
            function_call_result = call_function(function_call, verbose=args.verbose)

            if not function_call_result.parts:
                raise RuntimeError("Function call result parts list is empty.")

            if function_call_result.parts[0].function_response is None:
                raise RuntimeError("function_response inside the part is None.")

            if function_call_result.parts[0].function_response.response is None:
                raise RuntimeError("Actual response map inside function_response is None.")

            function_results.append(function_call_result.parts[0])

            if args.verbose:
                print(f"-> {function_call_result.parts[0].function_response.response}")
        
        messages.append(types.Content(role="user", parts=function_results))
        
    else:
        print(response.text)
        agent_resolved = True
        break

if not agent_resolved:
    print("Error: The agent failed to resolve the task within the maximum iteration limit (20).", file=sys.stderr)
    sys.exit(1)
