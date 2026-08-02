import os
from typing import cast
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam,ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition

load_dotenv()
Tool=dict

class ChatOpenAI:
    def __init__(self,
                 model:str,
                 system_prompt:str="",
                 tools:list[Tool]|None=None,
                 context:str=""):
        self.llm=AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )
        self.model=model
        self.tools:list[Tool]=tools if tools is not None else []
        self.messages:list[ChatCompletionMessageParam]=[]
        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })
        if context:
            self.messages.append({
                "role": "user",
                "content": context
            })

    def _get_tools_definition(self)->list[ChatCompletionToolParam]:
        return [ChatCompletionToolParam(
            type="function",
            function=FunctionDefinition(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"]
            )
        ) for t in self.tools]

    async def chat(self,user_input:str):
        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        stream=await self.llm.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self._get_tools_definition() if self.tools else [],
            stream=True,
        )

        content=""
        tool_calls=[]

        async for chunk in stream:
            delta=chunk.choices[0].delta
            if delta.content:
                content+=delta.content
            if delta.tool_calls:
                for tool_call_chunk in delta.tool_calls:
                    while len(tool_calls)<=tool_call_chunk.index:
                        tool_calls.append(
                            {
                                "id": "",
                                "function": {"name": "", "arguments": ""},
                            }
                        )
                    current=tool_calls[tool_call_chunk.index]
                    if tool_call_chunk.id:
                        current["id"]+=tool_call_chunk.id
                    if tool_call_chunk.function and tool_call_chunk.function.name:
                        current["function"]["name"]+=tool_call_chunk.function.name
                    if tool_call_chunk.function and tool_call_chunk.function.arguments:
                        current["function"]["arguments"]+=tool_call_chunk.function.arguments
        print()
        assistant:dict={
            "role": "assistant",
            "content": content
        }
        if tool_calls:
            assistant["tool_calls"]=[
                {
                    "id": t["id"],
                    "type": "function",
                    "function": t["function"],
                }
                for t in tool_calls
            ]
        self.messages.append(cast(ChatCompletionMessageParam, assistant))
        return {
            "content": content,
            "tool_calls": tool_calls
        }

    def tool_result(self,tool_call_id:str,result:str):
        self.messages.append(
            cast(ChatCompletionMessageParam,
                {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call_id
                }
            )
        )
