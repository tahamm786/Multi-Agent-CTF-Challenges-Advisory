from rest_framework import serializers
from .models import SolveSession,AgentEvent 

class AgentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEvent
        fields = ['id', 'agent_name', 'event_type', 'content', 'created_at']


class SolveSessionSerializer(serializers.ModelSerializer):
    events = AgentEventSerializer(many=True, read_only=True)

    class Meta:
        model = SolveSession
        fields = ['id', 'target_input', 'context_notes', 'overall_goal',
                  'status', 'final_report', 'created_at', 'events']