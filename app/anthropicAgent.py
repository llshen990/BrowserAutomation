from browser import ActionPlanner, Coordinate,ScrollBar,BrowserState
from typing import Optional,Union,cast
from PIL import Image
import io
import os
import random
import json
from math import floor
from datetime import datetime
import base64
from dataclasses import dataclass
from anthropic import Anthropic
from anthropic.types.beta import BetaMessage,BetaTextBlockParam,BetaImageBlockParam,BetaToolUseBlockParam
from browser import BrowserStep,BrowserActionType,BrowserAction,_kind
# from human_pause import is_challenge_present, wait_for_human, PAUSE_ON_CHALLENGE

# Base64 encoded cursor image
CURSOR_64 = "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAQCAYAAAAvf+5AAAAAw3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjabVBRDsMgCP33FDuC8ijF49i1S3aDHX9YcLFLX+ITeOSJpOPzfqVHBxVOvKwqVSQbuHKlZoFmRzu5ZD55rvX8Uk9Dz2Ql2A1PVaJ/1MvPwK9m0TIZ6TOE7SpUDn/9M4qH0CciC/YwqmEEcqGEQYsvSNV1/sJ25CvUTxqBjzGJU86rbW9f7B0QHSjIxoD6AOiHE1oXjAlqjQVyxmTMkJjEFnK3p4H0BSRiWUv/cuYLAAABhWlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AYht+2SqVUHCwo0iFD1cWCqIijVqEIFUKt0KqDyaV/0KQhSXFxFFwLDv4sVh1cnHV1cBUEwR8QZwcnRRcp8buk0CLGg7t7eO97X+6+A/yNClPNrnFA1SwjnUwI2dyqEHxFCFEM0DoqMVOfE8UUPMfXPXx8v4vzLO+6P0evkjcZ4BOIZ5luWMQbxNObls55nzjCSpJCfE48ZtAFiR+5Lrv8xrnosJ9nRoxMep44QiwUO1juYFYyVOIp4piiapTvz7qscN7irFZqrHVP/sJwXltZ5jrNKJJYxBJECJBRQxkVWIjTrpFiIk3nCQ//kOMXySWTqwxGjgVUoUJy/OB/8Lu3ZmFywk0KJ4DuF9v+GAaCu0Czbtvfx7bdPAECz8CV1vZXG8DMJ+n1thY7Avq2gYvrtibvAZc7wOCTLhmSIwVo+gsF4P2MvikH9N8CoTW3b61znD4AGepV6gY4OARGipS97vHuns6+/VvT6t8Ph1lyr0hzlCAAAA14aVRYdFhNTDpjb20uYWRvYmUueG1wAAAAAAA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJYTVAgQ29yZSA0LjQuMC1FeGl2MiI+CiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgIHhtbG5zOnN0RXZ0PSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VFdmVudCMiCiAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICB4bWxuczpHSU1QPSJodHRwOi8vd3d3LmdpbXAub3JnL3htcC8iCiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIKICAgeG1wTU06RG9jdW1lbnRJRD0iZ2ltcDpkb2NpZDpnaW1wOjFiYzFkZjE3LWM5YmMtNGYzZi1hMmEzLTlmODkyNWNiZjY4OSIKICAgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo4YTUyMWJhMC00YmNlLTQzZWEtYjgyYS04ZGM2MTBjYmZlOTgiCiAgIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDplODQ3ZjUxNC00MWVlLTQ2ZjYtOTllNC1kNjI3MjMxMjhlZTIiCiAgIGRjOkZvcm1hdD0iaW1hZ2UvcG5nIgogICBHSU1QOkFQST0iMi4wIgogICBHSU1QOlBsYXRmb3JtPSJMaW51eCIKICAgR0lNUDpUaW1lU3RhbXA9IjE3MzAxNTc3NjY5MTI3ODciCiAgIEdJTVA6VmVyc2lvbj0iMi4xMC4zOCIKICAgdGlmZjpPcmllbnRhdGlvbj0iMSIKICAgeG1wOkNyZWF0b3JUb29sPSJHSU1QIDIuMTAiCiAgIHhtcDpNZXRhZGF0YURhdGU9IjIwMjQ6MTA6MjhUMTY6MjI6NDYtMDc6MDAiCiAgIHhtcDpNb2RpZnlEYXRlPSIyMDI0OjEwOjI4VDE2OjIyOjQ2LTA3OjAwIj4KICAgPHhtcE1NOkhpc3Rvcnk+CiAgICA8cmRmOlNlcT4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6ZTVjOTM2ZDYtYjMzYi00NzM4LTlhNWUtYjM3YTA5MzdjZDAxIgogICAgICBzdEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKExpbnV4KSIKICAgICAgc3RFdnQ6d2hlbj0iMjAyNC0xMC0yOFQxNjoyMjo0Ni0wNzowMCIvPgogICAgPC9yZGY6U2VxPgogICA8L3htcE1NOkhpc3Rvcnk+CiAgPC9yZGY6RGVzY3JpcHRpb24+CiA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgCjw/eHBhY2tldCBlbmQ9InciPz5/5aQ8AAAABmJLR0QAcgByAAAtJLTuAAAACXBIWXMAAABZAAAAWQGqnamGAAAAB3RJTUUH6AocFxYuv5vOJAAAAHhJREFUKM+NzzEOQXEMB+DPYDY5iEVMIpzDfRxC3mZyBK7gChZnELGohaR58f7a7dd8bVq4YaVQgTvWFVjCUcXxA28qcBBHFUcVRwWPPuFfXVsbt0PPnLBL+dKHL+wxxhSPhBcZznuDXYKH1uGzBJ+YtPAZRyy/jTd7qEoydWUQ7QAAAABJRU5ErkJggg=="
CURSOR_BYTES = base64.b64decode(CURSOR_64)

class AnthropicPlannerOptions:
    pass

@dataclass
class ScalingRatio():
    ratio_x: float
    ratio_y:float
    origin_size:Coordinate
    new_size:Coordinate

@dataclass
class MessageOptions:
    mouse_position:bool
    screenshot:bool
    tabs:bool

class AnthropicPlanner(ActionPlanner):
    def __init__(self,options:Optional[AnthropicPlannerOptions]=None) -> None:
        self.model="claude-3-5-sonnet-20241022"
        self.max_tokens=1024
        self.beta_flag=["computer-use-2024-10-22"]
        self.client = Anthropic(api_key=os.getenv('apikey'))
        self.input_token_usage:int=0
        self.output_token_usage:int=0
        self.debug_img_path="C:\\001-MyProj\\compx576\\debug\\screenshot.png"



    def screenshot_conversion(self,screenshot_buffer: bytes, current_state:BrowserState):
                              
        with Image.open(io.BytesIO(screenshot_buffer)) as img:
            resized = img.resize((current_state.width, current_state.height), Image.Resampling.LANCZOS).convert("RGBA")
            
            width,height = resized.size

            mouse_position = current_state.mouse
            scrollbar = current_state.scrollbar
            print(mouse_position)

            # Create scrollbar overlay
            scrollbar_width = 10
            scrollbar_height = int(height * scrollbar.height)
            scrollbar_top = int(height * scrollbar.offset)

            # Create gray rectangle for scrollbar
            scrollbar_img = Image.new(
                "RGBA", (scrollbar_width, scrollbar_height), (128, 128, 128, 179)
            )
            ## Create image copy and add scrollbar
            composite = resized.copy()
            composite.paste(scrollbar_img, (width - scrollbar_width, scrollbar_top),scrollbar_img)

            ## add cursor
            cursor_img = Image.open(io.BytesIO(CURSOR_BYTES))
            composite.paste(
                cursor_img,
                (
                    max(0, mouse_position.x - cursor_img.width // 2),
                    max(0, mouse_position.y - cursor_img.height // 2),
                ),
                cursor_img,
            )
           
        
            target_width = 1280
            target_height = 800

            # Calculate dimensions that fit within target while maintaining aspect ratio
            composite.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)

            output_buffer = io.BytesIO()
            composite.save(output_buffer, format="PNG")
            return output_buffer.getvalue()

    def get_screenshot_ratio(self,orig_size:Coordinate):
        orig_ratio = orig_size.x/orig_size.y
        if orig_ratio > 1280/800:
            new_width = 1280
            new_height = floor(1280/orig_ratio)
        else:
            new_height = 800
            new_width = floor(800*orig_ratio)                    
        width_ratio = orig_size.x/new_width
        height_ratio = orig_size.y/new_height
        return ScalingRatio(
            ratio_x = width_ratio,
            ratio_y = height_ratio,
            origin_size = orig_size,
            new_size = Coordinate(new_width,new_height)
        )
        
    def browser_to_llm_coordinate(self,input_coord:Coordinate,scaling_ratio:ScalingRatio):
        return Coordinate(
            x=min(max(floor(input_coord.x/scaling_ratio.ratio_x),1),scaling_ratio.new_size.x),
            y=min(max(floor(input_coord.y/scaling_ratio.ratio_y),1),scaling_ratio.new_size.y)
        )

    def llm_to_browser_coordinate(self,input_coord:Coordinate,scaling_ratio:ScalingRatio):
        return Coordinate(
            x=min(max(floor(input_coord.x*scaling_ratio.ratio_x),1),scaling_ratio.origin_size.x),
            y=min(max(floor(input_coord.y*scaling_ratio.ratio_y),1),scaling_ratio.origin_size.y)
        )



    def create_tool_id(self):
        prefix="toolu_"
        chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        id_length=22
        result=prefix
        for _ in range(id_length):
            result+=random.choice(chars)
        return result

    def format_state_into_msg(self,tool_id,browserstate:BrowserState,msgOptions:MessageOptions):
        text_message = ""
        msg_content:list[Union[BetaTextBlockParam,BetaImageBlockParam]]=[]
        if msgOptions.mouse_position:
            screenshot_dim = Coordinate(x=browserstate.width,y=browserstate.height)
            scaling_ratio = self.get_screenshot_ratio(screenshot_dim)
            mouse_pos = self.browser_to_llm_coordinate(browserstate.mouse,scaling_ratio)
            text_message += f"mouse position:({mouse_pos.x},{mouse_pos.y})\n"
        if msgOptions.tabs:
            tabs_as_dicts=[]
            for tab in browserstate.tabs:
                tab_dict={
                    "tab_id":tab.id,
                    "title":tab.title,
                    "active_tab":tab.active,
                    "new_tab":tab.new
                }
                tabs_as_dicts.append(tab_dict)
            text_message += f"\n\nOpen Browser tabs:{json.dumps(tabs_as_dicts)}\n\n"
        if not text_message:
            text_message = "Action has been performed"
        msg_content.append(
            {
                "type":"text",
                "text":text_message.strip()
            }
        )
        
        if msgOptions.screenshot:
            print("screenshot True,will save screenshot")
            # screenshot_buffer = base64.b64decode(browserstate.screenshot)
            screenshot_buffer = browserstate.screenshot
            resized = self.screenshot_conversion(screenshot_buffer,browserstate)
            if self.debug_img_path:
                with open(self.debug_img_path,'wb') as f:
                    f.write(resized)
            msg_content.append(
                {
                "type":"image",
                "source":{
                    "type":"base64",
                    "media_type":"image/png",
                    "data":base64.b64encode(resized).decode("ascii")
                }
                }
            )
        return {
            "role":'user',
            "content":[
                { 
                "type":"tool_result",
                "tool_use_id":tool_id,
                "content":msg_content
                }    
            ]                   
        }
        
    def system_prompt(self, additional_instructions: list[str]):
        instructions = "\n".join(
            f"* {instruction}" for instruction in additional_instructions
        )
        prompt = f"""
<SYSTEM_CAPABILITY>
* You are a computer use tool that is controlling a browser in fullscreen mode to complete a goal for the user. The goal is listed below in <USER_TASK>.
* The browser operates in fullscreen mode, meaning you cannot use standard browser UI elements like STOP, REFRESH, BACK, or the address bar. You must accomplish your task solely by interacting with the website's user interface or calling "switch_tab" or "stop_browsing"
* After each action, you will be provided with mouse position, open tabs, and a screenshot of the active browser tab.
* Use the Page_down or Page_up keys to scroll through the webpage. If the website is scrollable, a gray rectangle-shaped scrollbar will appear on the right edge of the screenshot. Ensure you have scrolled through the entire page before concluding that content is unavailable.
* The mouse cursor will appear as a black arrow in the screenshot. Use its position to confirm whether your mouse movement actions have been executed successfully. Ensure the cursor is correctly positioned over the intended UI element before executing a click command.
* After each action, you will receive information about open browser tabs. This information will be in the form of a list of JSON objects, each representing a browser tab with the following fields:
  - "tab_id": An integer that identifies the tab within the browser. Use this ID to switch between tabs.
  - "title": A string representing the title of the webpage loaded in the tab.
  - "active_tab": A boolean indicating whether this tab is currently active. You will receive a screenshot of the active tab.
  - "new_tab": A boolean indicating whether the tab was opened as a result of the last action.
* Follow all directions from the <IMPORTANT> section below. 
* The current date is {datetime.now().isoformat()}.
</SYSTEM_CAPABILITY>

The user will ask you to perform a task and you should use their browser to do so. After each step, analyze the screenshot and carefully evaluate if you have achieved the right outcome. Explicitly show your thinking for EACH function call: "I have evaluated step X..." If not correct, try again. Only when you confirm a step was executed correctly should you move on to the next one. You should always call a tool! Always return a tool call. Remember call the stop_browsing tool when you have achieved the goal of the task. Use keyboard shortcuts to navigate whenever possible.

<IMPORTANT>
* After moving the mouse to the desired location, always perform a left-click to ensure the action is completed.
* You will use information provided in user's <USER DATA> to fill out forms on the way to your goal.
* Return exactly one tool_use action per assistant message. Do not include multiple actions in a single response
* Ensure that any UI element is completely visible on the screen before attempting to interact with it.
* {instructions}
</IMPORTANT>"""

        return prompt.strip()

    def browser_hist_step_to_action(self,step:BrowserStep):
        val: dict[str,any] = {}
        if _kind(step.action.action) == _kind(BrowserActionType.SCROLL_DOWN):
            val["action"] = "key"
            val["text"] = "Page_Down"
            return val
        if _kind(step.action.action) == _kind(BrowserActionType.SCROLL_UP):
            val["action"] = "key"
            val["text"] = "Page_Up"
            return val

        val["action"] = step.action.action
       
        if step.action.text:
            val["text"] = step.action.text
        if step.action.coordinate:
            img_dim = Coordinate(step.state.width,step.state.height)
            scaling = self.get_screenshot_ratio(img_dim)
            llm_coordinates = self.browser_to_llm_coordinate(step.action.coordinate,scaling)
            val["coordinate"] = [llm_coordinates.x,llm_coordinates.y]
        return val
     

    def format_final_msg(self,goal,additional_context, current_state, session_history):
        messages : list[BetaImageBlockParam]=[]
        tool_id = self.create_tool_id()
        system_prompt= """
            please complete the following task:
            <USER_DATA>
            {goal}
            </USER_DATA>
            Using the supporting contextual data:
            {additional_context}
            """
        msg0={
            "role":"user",
            "content":[{
                "type":"text",
                "text":system_prompt.format(goal=goal,additional_context=additional_context)
            }]
        }

        msg1={
            "role":"assistant",
            "content":[
                {
                "type":"text",
                "text":"Grab a view of the browser to understand what is the starting website state."
                },
                {
                "type":"tool_use",
                "id":tool_id,
                "name":"computer",
                "input":{
                    "action":"screenshot"
                }
                }
            ]
        }
        
        messages.extend([msg0,msg1])

        for hist_step in session_history:
            options = MessageOptions(mouse_position=False, screenshot=False, tabs=False)
            tool_result_msg = self.format_state_into_msg(tool_id,hist_step.state,options)
            messages.append(tool_result_msg)

            tool_id = hist_step.action.id or self.create_tool_id()
            tool_use_list : list[Union[BetaTextBlockParam,BetaToolUseBlockParam]]=[]
            # tool_use_blk = self.format_action_into_msg(hist_step.action)
            tool_use_blk = self.browser_hist_step_to_action(hist_step)
            msg_dict={
                "type":"tool_use",
                "id":tool_id,
                "name":"computer",
                "input":tool_use_blk
            }
            tool_use_list.append(msg_dict)
            assistant_msg={
                "role":"assistant",
                "content":tool_use_list
            }
            messages.append(assistant_msg)

        current_state_message = self.format_state_into_msg(
            tool_id,
            current_state,
            MessageOptions(mouse_position=True, screenshot=True, tabs=True),
        )
        messages.append(current_state_message)
        # print(messages)
        return messages


    def plan_action(self, goal, additional_context, additional_instructions, current_state, session_history):
        system_prompt = self.system_prompt(additional_instructions)
        messages = self.format_final_msg(goal,additional_context, current_state, session_history)
        scaling = self.get_screenshot_ratio(
            Coordinate(x=current_state.width, y=current_state.height)
        )
        tools=[
                {
                    "type": "computer_20241022",
                    "name": "computer",
                    "display_width_px": current_state.width,
                    "display_height_px": current_state.height,
                    "display_number": 1,
                },
                {
                    "name": "switch_tab",
                    "description": "Call this function to switch the active browser tab to a new one",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "tab_id": {
                                "type": "integer",
                                "description": "The ID of the tab to switch to",
                            },
                        },
                        "required": ["tab_id"],
                    },
                },
                {
                    "name": "stop_browsing",
                    "description": "Call this function when you have achieved the goal of the task.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "success": {
                                "type": "boolean",
                                "description": "Whether the task was successful",
                            },
                            "error": {
                                "type": "string",
                                "description": "The error message if the task was not successful",
                            },
                        },
                        "required": ["success"],
                    },
                },
            ]
        response = self.client.beta.messages.create(
            model=self.model,
            system = system_prompt,
            max_tokens=self.max_tokens,
            messages=messages,
            tools=tools,
            betas=self.beta_flag,
            service_tier="auto"         
        )
        print(
            f"Token usage - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}"
        )
        self.input_token_usage += response.usage.input_tokens
        self.output_token_usage += response.usage.output_tokens
        print(
            f"Cumulative token usage - Input: {self.input_token_usage}, Output: {self.output_token_usage}, Total: {self.input_token_usage + self.output_token_usage}"
        )

        action = self.parse_action(response, scaling, current_state)
        

        return action



    def parse_action(self,response:BetaMessage,scaling:ScalingRatio,current_state:BrowserState):

        print("in AnthropicAgent parse_action, first-hand claude response>>>>")

        print(response.content)
        # return BrowserAction(
        #         action=BrowserActionType.SUCCESS,
        #         reasoning='xxx',
        #         text=None,
        #         coordinate=None,
        #         id=000000,
        #     )

        tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        reasoning = " ".join(
            content.text for content in response.content if content.type == "text"
        )
        if len(tool_uses) == 0:
            return BrowserAction(
                action=BrowserActionType.FAILURE,
                reasoning=reasoning,
                coordinate=None,
                text=None,
                id=self.create_tool_id(),
            )

        # for step in tool_uses:
        last_step = tool_uses[-1]
        print(last_step)
        print(last_step.name)
        if last_step.type != "tool_use":
            return BrowserAction(
                action=BrowserActionType.FAILURE,
                reasoning=reasoning,
                text="Wrong message called",
                coordinate=None,
                id=last_step.id,
            )
        if last_step.name == "stop_browsing":
            input_data = cast(dict, last_step.input)
            if not input_data.get("success"):
                return BrowserAction(
                    action=BrowserActionType.FAILURE,
                    reasoning=reasoning,
                    text=input_data.get("error", "Unknown error"),
                    coordinate=None,
                    id=last_step.id,
                )
            return BrowserAction(
                action=BrowserActionType.SUCCESS,
                reasoning=reasoning,
                text=None,
                coordinate=None,
                id=last_step.id,
            )

        if last_step.name == "switch_tab":
            input_data = cast(dict, last_step.input)
            if "tab_id" not in input_data:
                return BrowserAction(
                    action=BrowserActionType.FAILURE,
                    reasoning=reasoning,
                    text=input_data.get(
                        "error", "No tab id for switch_tab function call"
                    ),
                    coordinate=None,
                    id=last_step.id,
                )
            return BrowserAction(
                action=BrowserActionType.SWITCH_TAB,
                reasoning=reasoning,
                text=str(
                    input_data["tab_id"]
                ),  # Convert to string since text is Optional[str]
                coordinate=None,
                id=last_step.id,
            )
        
        if last_step.name != "computer":
            return BrowserAction(
                action=BrowserActionType.FAILURE,
                reasoning=reasoning,
                text="Wrong message called",
                coordinate=None,
                id=last_step.id,
            )
        
        input_data = cast(dict, last_step.input)
        action = input_data.get("action", "")
        coordinate: Optional[list[int]] = input_data.get("coordinate")  # Make Optional
        text: Optional[str] = input_data.get("text")  # Make Optional

        if isinstance(coordinate, str):
            print("Coordinate is a string:", coordinate)
            print(last_step)
            raw = json.loads(coordinate)
            if isinstance(raw, tuple):
                coordinate = raw
            elif isinstance(raw, dict):
                if "x" in raw and "y" in raw:
                    coordinate = (raw["x"], raw["y"])

        if isinstance(coordinate, dict):
            if "x" in coordinate and "y" in coordinate:
                print("Coordinate object has x and y properties")
                coordinate = (coordinate["x"], coordinate["y"])
        if isinstance(coordinate, list):
            coordinate = (coordinate[0], coordinate[1])
        

        if action == "key" or action == "type":
            if not text:
                return BrowserAction(
                    action=BrowserActionType.FAILURE,
                    reasoning=reasoning,
                    text=f"No text provided for {action}",
                    coordinate=None,
                    id=last_step.id,
                )

            if action == "key":
                # Handle special key mappings from utils.parse_xdotool
                text_lower = text.lower().strip()
                if text_lower in ("page_down", "pagedown"):
                    return BrowserAction(
                        action=BrowserActionType.SCROLL_DOWN,
                        reasoning=reasoning,
                        coordinate=None,
                        text=None,
                        id=last_step.id,
                    )
                if text_lower in ("page_up", "pageup"):
                    return BrowserAction(
                        action=BrowserActionType.SCROLL_UP,
                        reasoning=reasoning,
                        coordinate=None,
                        text=None,
                        id=last_step.id,
                    )

            return BrowserAction(
                action=(
                    BrowserActionType.KEY if action == "key" else BrowserActionType.TYPE
                ),
                reasoning=reasoning,
                text=text,
                coordinate=None,
                id=last_step.id,
            )
        elif action == "mouse_move":
            if not coordinate:
                return BrowserAction(
                    action=BrowserActionType.FAILURE,
                    reasoning=reasoning,
                    text="No coordinate provided",
                    coordinate=None,
                    id=last_step.id,
                )
            browser_coordinates = self.llm_to_browser_coordinate(
                Coordinate(x=coordinate[0], y=coordinate[1]), scaling
            )
            # Calculate the distance moved
            distance_moved = (
                (browser_coordinates.x - current_state.mouse.x) ** 2
                + (browser_coordinates.y - current_state.mouse.y) ** 2
            ) ** 0.5
            print(f"Distance moved: {distance_moved}")

            # Check if the movement is within a minimal threshold to consider as jitter
            if distance_moved <= 5:
                print("Minimal mouse movement detected, considering as jitter.")
                return BrowserAction(
                    action=BrowserActionType.LEFT_CLICK,
                    reasoning=reasoning,
                    coordinate=None,
                    text=None,
                    id=last_step.id,
                )

            return BrowserAction(
                action=BrowserActionType.MOUSE_MOVE,
                reasoning=reasoning,
                coordinate=browser_coordinates,
                text=None,
                id=last_step.id,
            )
        elif action == "left_click_drag":
            if not coordinate:
                return BrowserAction(
                    action=BrowserActionType.FAILURE,
                    reasoning=reasoning,
                    text="No coordinate provided",
                    coordinate=None,
                    id=last_step.id,
                )

            browser_coordinates = self.llm_to_browser_coordinate(
                Coordinate(x=coordinate[0], y=coordinate[1]), scaling
            )

            return BrowserAction(
                action=BrowserActionType.LEFT_CLICK_DRAG,
                reasoning=reasoning,
                coordinate=browser_coordinates,
                text=None,
                id=last_step.id,
            )
        elif action in (
            "left_click",
            "right_click",
            "middle_click",
            "double_click",
            "screenshot",
            "cursor_position",
        ):
            action_type = {
                "left_click": BrowserActionType.LEFT_CLICK,
                "right_click": BrowserActionType.RIGHT_CLICK,
                "middle_click": BrowserActionType.MIDDLE_CLICK,
                "double_click": BrowserActionType.DOUBLE_CLICK,
                "screenshot": BrowserActionType.SCREENSHOT,
                "cursor_position": BrowserActionType.CURSOR_POSITION,
            }[action]

            return BrowserAction(
                action=action_type,
                reasoning=reasoning,
                coordinate=None,
                text=None,
                id=last_step.id,
            )
        else:
            return BrowserAction(
                action=BrowserActionType.FAILURE,
                reasoning=reasoning,
                text=f"Unsupported computer action: {action}",
                coordinate=None,
                id=last_step.id,
            )