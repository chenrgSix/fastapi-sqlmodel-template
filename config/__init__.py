from config.settings import Settings, get_settings
settings = get_settings()

def get_yaml_conf(k):
    return settings.yaml_config.get(k, None)

def show_configs():
    return settings