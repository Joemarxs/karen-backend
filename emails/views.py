# emails/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import send_booking_email

@csrf_exempt  # only for development — add CSRF protection in production
def book_tour_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            email = data.get('email')
            date = data.get('date')
            time = data.get('time')
            guests = data.get('guests')

            send_booking_email(name, email, date, time, guests)

            return JsonResponse({'message': 'Email sent successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)
