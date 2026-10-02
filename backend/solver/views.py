import threading
import json
import time
from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AgentEvent,SolveSession
from .serializer import AgentEventSerializer,SolveSessionSerializer
from .agents import run_coordinator

class SolveSessionListCreateView(generics.ListCreateAPIView):

    queryset=SolveSession.objects.all().order_by("-created_at")
    serializer_class=SolveSessionSerializer


    def create(self,request,*args,**kwargs):

        target_input=request.data.get('target_input','').strip()
        if not target_input:
            return Response({"error":"target_input is required"},status=status.HTTP_400_BAD_REQUEST)

        context_notes=request.data.get("context_notes",'')
        overall_goal=request.data.get("overall_goal",'')
        session=SolveSession.objects.create(
            target_input=target_input,
            context_notes=context_notes,
            overall_goal=overall_goal,
            status="running",
        )

        thread=threading.Thread(
            target=_run_session_in_background,
            args=(session.id,target_input,overall_goal,context_notes),
            daemon=True,
        )

        thread.start()

        return Response(SolveSessionSerializer(session).data,status=status.HTTP_201_CREATED)


def _run_session_in_background(session_id,target_input,overall_goal,context_notes):

    session=SolveSession.objects.get(id=session_id)

    try:
        final_report=run_coordinator(target_input,context_notes,overall_goal,session_id=session_id)
        session.final_report=final_report
        session.status="solved"

    except Exception as e:
        session.final_report=f"Run Failed : {e}"
        session.status="failed"

    session.save()

class SolveSessionDetailView(generics.RetrieveAPIView):

    queryset=SolveSession.objects.all()
    serializer_class=SolveSessionSerializer


class SolveSessionStreamView(APIView):
    """SSE Endpoint : streams New agent event rows for this session as they are created, until the session is marked as solved or failed."""

    def get(self,request,pk):

        def event_stream():
            last_id=0

            while True:
                session=SolveSession.objects.filter(id=pk).first()
                if session is None:
                    yield "event : error \n data :{} \n\n"
                    return 

                new_events=AgentEvent.objects.filter(session_id=pk,id__gt=last_id).order_by("id")

                for event in new_events:
                    last_id=event.id
                    payload={
                        "agent_name":event.agent_name,
                        "event_type":event.event_type,
                        "content":event.content,
                        "created_at":event.created_at.isoformat(),
                    }

                    yield f"data: {json.dumps(payload)}\n\n"

                if session.status in ("solved","failed"):
                    yield f"event: done\ndata: {json.dumps({'status':session.status})}\n\n"
                    return
                
                time.sleep(1)


        response=StreamingHttpResponse(event_stream(),content_type="text/event-stream")
        response["Cache-Control"]="no-cache"
        response["X-Accel-Buffering"]="no"

        return response
        



