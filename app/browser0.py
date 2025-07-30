from abc import ABC,abstractmethod
from typing import Optional
from playwright.async_api import Page, BrowserContext
from typing import Optional


class ActionPlanner(ABC):
    pass

class BrowserAgentOptions():
    pass

class BrowserAgent():
    def __init__(self, 
                 page: Page,
                 context: BrowserContext,
                 action_planner: ActionPlanner,
                 goal: str,
                 options: Optional[BrowserAgentOptions] = None):
        
        self.page:Page = page
        self.context:BrowserContext = context
        self.options = options
        self.action_planner = action_planner
        self.goal = goal
        self.max_steps=50