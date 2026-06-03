from django.shortcuts import render
from django.http import response
from django.core.mail import send_mail,send_mass_mail
from django.conf import settings

def posmiMail(subject:str,message:str,address:str):
    try:
        full_message = message + "\n\n[POSMI APPS]"
        send_mail(subject=subject,message=full_message,from_email=settings.DEFAULT_FROM_EMAIL,recipient_list=[address])
        return True
    except Exception as ex:
        print(ex)
        return False