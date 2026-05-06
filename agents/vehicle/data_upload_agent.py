class DataUploadAgent:
    role_name = "数据上报 Agent"

    def __init__(self, feedback_service=None):
        self.feedback_service = feedback_service

    def record(self, result):
        if not self.feedback_service:
            return {}
        return self.feedback_service.record(result)
