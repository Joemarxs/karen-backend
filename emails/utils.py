# emails/utils.py
from django.core.mail import send_mail

def send_booking_email(name, email, date, time, guests):
    subject = 'Farm Tour Booking Confirmation'
    message = f'''
Hi {name},

Thank you for booking a farm tour!

📅 Date: {date}
⏰ Time: {time}
👥 Number of Guests: {guests}

We look forward to seeing you at the farm!

Regards,  
Farm Tours Team
    '''

    send_mail(
        subject,
        message,
        None,  # uses DEFAULT_FROM_EMAIL from settings
        [email],
        fail_silently=False,
    )
