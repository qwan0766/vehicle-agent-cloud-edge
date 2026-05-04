from data.user_profiles import DEFAULT_PROFILE, USER_PROFILES
from rag.documents import PROFILE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class CloudUserProfileAgent:
    def __init__(self):
        self.retriever = SimpleRetriever(PROFILE_DOCUMENTS)

    def get_profile(self, user_id: str) -> str:
        return USER_PROFILES.get(user_id, DEFAULT_PROFILE)

    def retrieve_context(self, user_id: str, content: str = ""):
        query = f"{user_id} {content}".strip()
        return [
            result
            for result in self.retriever.search(query, top_k=2)
            if result.document.metadata.get("user_id") == user_id
        ]

    def get_route_preference(self, user_id: str, content: str = "") -> str:
        for result in self.retrieve_context(user_id, content):
            route_preference = result.document.metadata.get("route_preference")
            if route_preference:
                return str(route_preference)
        return ""
