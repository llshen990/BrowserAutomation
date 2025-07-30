from browser import ActionPlanner, Coordinate,ScrollBar,BrowserState
from typing import Optional
from PIL import Image
import io
import base64


# Base64 encoded cursor image
CURSOR_64 = "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAQCAYAAAAvf+5AAAAAw3pUWHRSYXcgcHJvZmlsZSB0eXBlIGV4aWYAAHjabVBRDsMgCP33FDuC8ijF49i1S3aDHX9YcLFLX+ITeOSJpOPzfqVHBxVOvKwqVSQbuHKlZoFmRzu5ZD55rvX8Uk9Dz2Ql2A1PVaJ/1MvPwK9m0TIZ6TOE7SpUDn/9M4qH0CciC/YwqmEEcqGEQYsvSNV1/sJ25CvUTxqBjzGJU86rbW9f7B0QHSjIxoD6AOiHE1oXjAlqjQVyxmTMkJjEFnK3p4H0BSRiWUv/cuYLAAABhWlDQ1BJQ0MgcHJvZmlsZQAAeJx9kT1Iw0AYht+2SqVUHCwo0iFD1cWCqIijVqEIFUKt0KqDyaV/0KQhSXFxFFwLDv4sVh1cnHV1cBUEwR8QZwcnRRcp8buk0CLGg7t7eO97X+6+A/yNClPNrnFA1SwjnUwI2dyqEHxFCFEM0DoqMVOfE8UUPMfXPXx8v4vzLO+6P0evkjcZ4BOIZ5luWMQbxNObls55nzjCSpJCfE48ZtAFiR+5Lrv8xrnosJ9nRoxMep44QiwUO1juYFYyVOIp4piiapTvz7qscN7irFZqrHVP/sJwXltZ5jrNKJJYxBJECJBRQxkVWIjTrpFiIk3nCQ//kOMXySWTqwxGjgVUoUJy/OB/8Lu3ZmFywk0KJ4DuF9v+GAaCu0Czbtvfx7bdPAECz8CV1vZXG8DMJ+n1thY7Avq2gYvrtibvAZc7wOCTLhmSIwVo+gsF4P2MvikH9N8CoTW3b61znD4AGepV6gY4OARGipS97vHuns6+/VvT6t8Ph1lyr0hzlCAAAA14aVRYdFhNTDpjb20uYWRvYmUueG1wAAAAAAA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJYTVAgQ29yZSA0LjQuMC1FeGl2MiI+CiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgIHhtbG5zOnN0RXZ0PSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VFdmVudCMiCiAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICB4bWxuczpHSU1QPSJodHRwOi8vd3d3LmdpbXAub3JnL3htcC8iCiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIKICAgeG1wTU06RG9jdW1lbnRJRD0iZ2ltcDpkb2NpZDpnaW1wOjFiYzFkZjE3LWM5YmMtNGYzZi1hMmEzLTlmODkyNWNiZjY4OSIKICAgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo4YTUyMWJhMC00YmNlLTQzZWEtYjgyYS04ZGM2MTBjYmZlOTgiCiAgIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDplODQ3ZjUxNC00MWVlLTQ2ZjYtOTllNC1kNjI3MjMxMjhlZTIiCiAgIGRjOkZvcm1hdD0iaW1hZ2UvcG5nIgogICBHSU1QOkFQST0iMi4wIgogICBHSU1QOlBsYXRmb3JtPSJMaW51eCIKICAgR0lNUDpUaW1lU3RhbXA9IjE3MzAxNTc3NjY5MTI3ODciCiAgIEdJTVA6VmVyc2lvbj0iMi4xMC4zOCIKICAgdGlmZjpPcmllbnRhdGlvbj0iMSIKICAgeG1wOkNyZWF0b3JUb29sPSJHSU1QIDIuMTAiCiAgIHhtcDpNZXRhZGF0YURhdGU9IjIwMjQ6MTA6MjhUMTY6MjI6NDYtMDc6MDAiCiAgIHhtcDpNb2RpZnlEYXRlPSIyMDI0OjEwOjI4VDE2OjIyOjQ2LTA3OjAwIj4KICAgPHhtcE1NOkhpc3Rvcnk+CiAgICA8cmRmOlNlcT4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6ZTVjOTM2ZDYtYjMzYi00NzM4LTlhNWUtYjM3YTA5MzdjZDAxIgogICAgICBzdEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKExpbnV4KSIKICAgICAgc3RFdnQ6d2hlbj0iMjAyNC0xMC0yOFQxNjoyMjo0Ni0wNzowMCIvPgogICAgPC9yZGY6U2VxPgogICA8L3htcE1NOkhpc3Rvcnk+CiAgPC9yZGY6RGVzY3JpcHRpb24+CiA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgCjw/eHBhY2tldCBlbmQ9InciPz5/5aQ8AAAABmJLR0QAcgByAAAtJLTuAAAACXBIWXMAAABZAAAAWQGqnamGAAAAB3RJTUUH6AocFxYuv5vOJAAAAHhJREFUKM+NzzEOQXEMB+DPYDY5iEVMIpzDfRxC3mZyBK7gChZnELGohaR58f7a7dd8bVq4YaVQgTvWFVjCUcXxA28qcBBHFUcVRwWPPuFfXVsbt0PPnLBL+dKHL+wxxhSPhBcZznuDXYKH1uGzBJ+YtPAZRyy/jTd7qEoydWUQ7QAAAABJRU5ErkJggg=="
CURSOR_BYTES = base64.b64decode(CURSOR_64)

class AnthropicPlannerOptions:
    pass


class AnthropicPlanner(ActionPlanner):
    def __init__(self,options:Optional[AnthropicPlannerOptions]=None) -> None:
        pass

    def screenshot_conversion(self,screenshot_buffer: bytes, current_state:BrowserState):
                              
        with Image.open(io.BytesIO(screenshot_buffer)) as img:
            resized = img.resize((current_state.width, current_state.height), Image.Resampling.LANCZOS).convert("RGBA")
            
            width,height = resized.size

            mouse_position = current_state.mouse
            scrollbar = current_state.scrollbar

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

    def get_ratio():
        pass

    def llm_to_browser_coordinate():
        pass



    def browser_to_llm_coordinate():
        pass

    def format_state_into_msg():
        pass



    def browser_steo_to_action():
        pass

    def format_into_final_msg():
        pass

    


        
