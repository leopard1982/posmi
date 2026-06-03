from django.conf import settings
import os

def readEnv(envnya):
    file_name = os.path.join(settings.BASE_DIR, '.env')
    with open(file_name, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, _, value = line.partition('=')
            if key == envnya:
                value = value.strip()
                if value == 'True':
                    return True
                if value == 'False':
                    return False
                return value
    return None
