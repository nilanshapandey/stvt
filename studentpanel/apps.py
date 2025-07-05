
from django.apps import AppConfig

class StudentpanelConfig(AppConfig):
    name = "studentpanel"
    def ready(self):
        import studentpanel.signals
