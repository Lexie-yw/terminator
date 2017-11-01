from django.conf import settings


def features(request):
    features = getattr(settings, "FEATURES", {})
    features = {
            "autoterm": features.get("autoterm", True),
            "import_tbx": features.get("import_tbx", True),
            "export_tbx": features.get("export_tbx", True),
            "proposals": features.get("proposals", True),
            "registration": getattr(settings, "REGISTRATION_OPEN", True),
    }
    return {"features": features}
