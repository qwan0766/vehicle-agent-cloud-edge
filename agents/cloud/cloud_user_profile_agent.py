from data.user_profiles import DEFAULT_PROFILE, USER_PROFILES


class CloudUserProfileAgent:
    def get_profile(self, user_id: str) -> str:
        return USER_PROFILES.get(user_id, DEFAULT_PROFILE)
