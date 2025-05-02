from django.conf import settings
import os

def readEnv(envnya):
    file_name = os.path.join(settings.BASE_DIR,'.env')
    file = open(file_name,'r')
    list_env=[]
    for data in file:
        if data.split('=')[0]==envnya:
            if(data.split('=')[1]=="True"):
                return True
            elif(data.split('=')[1]=="False"):
                return False
            return data.split('=')[1]
    return None