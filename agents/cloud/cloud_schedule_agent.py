from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.message import Message


class CloudScheduleAgent:
    def __init__(self, user_agent=None, route_agent=None, ecology_agent=None):
        self.user_agent = user_agent or CloudUserProfileAgent()
        self.route_agent = route_agent or CloudRoutePlanAgent()
        self.ecology_agent = ecology_agent or CloudEcologyAgent()

    def dispatch(self, msg: Message) -> str:
        user_pref = self.user_agent.get_profile(msg.user_id)
        route_preference = self.user_agent.get_route_preference(msg.user_id, msg.content)
        ecology = self.ecology_agent.get_data()
        route = self.route_agent.plan(msg.content, route_preference=route_preference)
        return f"{user_pref} | {ecology} | {route}"
