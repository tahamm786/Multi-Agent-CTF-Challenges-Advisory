import threading
import json
import time
from django.http import StreamingHttpResponse
from django.db import connection
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.renderers import JSONRenderer, BaseRenderer
from django.contrib.auth.models import User
from .models import AgentEvent,SolveSession
from .serializer import AgentEventSerializer,SolveSessionSerializer
from .agents import run_coordinator
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from .allowlist import is_allowed_target

class SessionCreateThrottle(UserRateThrottle):
    scope = 'session_create'
    rate = '5/hour'

class SolveSessionListCreateView(generics.ListCreateAPIView):

    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionCreateThrottle]
    serializer_class = SolveSessionSerializer

    def get_queryset(self):
        return SolveSession.objects.filter(owner=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):

        target_input = request.data.get('target_input', '').strip()
        if not target_input:
            return Response({"error": "target_input is required"}, status=status.HTTP_400_BAD_REQUEST)

        if target_input.lower().startswith(("http://", "https://")) and not is_allowed_target(target_input):
            return Response(
                {"error": "Target is not on the approved list of training platforms."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        context_notes = request.data.get("context_notes", '')
        overall_goal = request.data.get("overall_goal", '')
        session = SolveSession.objects.create(
            target_input=target_input,
            context_notes=context_notes,
            overall_goal=overall_goal,
            status="running",
            owner=request.user,
        )

        thread = threading.Thread(
            target=_run_session_in_background,
            args=(session.id, target_input, overall_goal, context_notes),
            daemon=True,
        )

        thread.start()

        return Response(SolveSessionSerializer(session).data, status=status.HTTP_201_CREATED)


def _run_session_in_background(session_id, target_input, overall_goal, context_notes):

    session = SolveSession.objects.get(id=session_id)

    try:
        final_report = run_coordinator(target_input, context_notes, overall_goal, session_id=session_id)
        session.final_report = final_report
        if session.final_report and session.final_report.startswith("This doesn't look like"):
            session.status = "rejected"
        else:
            session.status = "solved"

    except Exception as e:
        session.final_report = f"Run Failed : {e}"
        session.status = "failed"

    session.save()


class SolveSessionDetailView(generics.RetrieveAPIView):

    serializer_class = SolveSessionSerializer

    def get_queryset(self):
        return SolveSession.objects.filter(owner=self.request.user)


# 1. Define a simple renderer to tell DRF that we support the SSE format
class EventStreamRenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'txt'
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
    
class SolveSessionStreamView(APIView):
    """SSE Endpoint: streams new agent event rows for this session as they are
    created, until the session is marked as solved or failed.

    NOTE: EventSource (the browser SSE client) cannot send custom headers,
    so it can't carry the usual `Authorization: Token ...` header. Instead,
    the frontend passes the token as a `?token=` query param, and we look
    the user up manually here rather than relying on DRF's normal auth flow.
    """

    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer, EventStreamRenderer]
    
    def get(self, request, pk):
        token_key = request.GET.get("token")
        
        token_key = request.GET.get("token")
        token_obj = Token.objects.filter(key=token_key).select_related("user").first()
        if not token_obj:
            return Response({"error": "Unauthorized"}, status=401)

        session = SolveSession.objects.filter(id=pk, owner=token_obj.user).first()
        if session is None:
            return Response({"error": "Not found"}, status=404)
        
        def event_stream():
            last_id = 0
            start = time.monotonic()
            MAX_SECONDS = 600  # 10 min
            while True:
                if time.monotonic() - start > MAX_SECONDS:
                    yield f"event: timeout\ndata: {json.dumps({'status':'timeout'})}\n\n"
                    return
                
                session = SolveSession.objects.filter(id=pk).first()
                if session is None:
                    yield "event: error\ndata: {}\n\n"
                    return

                new_events = AgentEvent.objects.filter(session_id=pk, id__gt=last_id).order_by('id')
                for event in new_events:
                    last_id = event.id
                    payload = {
                        "agent_name": event.agent_name,
                        "event_type": event.event_type,
                        "content": event.content,
                        "created_at": event.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                if session.status in ('solved', 'failed'):
                    yield f"event: done\ndata: {json.dumps({'status': session.status})}\n\n"
                    return

                time.sleep(1)

                connection.close()

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")
        if not username or not password:
            return Response({"error": "username and password are required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"error": "username already taken"}, status=400)

        user = User.objects.create_user(username=username, password=password)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username}, status=201)


class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username})