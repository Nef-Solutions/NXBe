from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .policy import inspect_message
from .quota import AssistantQuotaExceeded
from .serializers import ChatMessageSerializer
from .services import AssistantUnavailableError, answer_message


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'assistant'

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data['message']

        blocked_response = inspect_message(message)
        if blocked_response:
            return Response({'reply': blocked_response})

        try:
            reply = answer_message(request.user, message)
        except AssistantQuotaExceeded as error:
            return Response(
                {'detail': str(error)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except AssistantUnavailableError:
            return Response(
                {'detail': 'El asistente no está disponible en este momento. Inténtalo más tarde.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'reply': reply})
