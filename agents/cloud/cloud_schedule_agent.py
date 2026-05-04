from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.message import Message


class CloudScheduleAgent:
    def __init__(self):
        self.user_agent = CloudUserProfileAgent()
        self.route_agent = CloudRoutePlanAgent()
        self.ecology_agent = CloudEcologyAgent()

    def dispatch(self, msg: Message) -> str:
        user_pref = self.user_agent.get_profile(msg.user_id)
        ecology = self.ecology_agent.get_data()
        route = self.route_agent.plan(msg.content)
        return f"{user_pref} | {ecology} | {route}"
