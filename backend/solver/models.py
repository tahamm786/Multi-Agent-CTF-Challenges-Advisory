from django.db import models
from django.conf import settings

class SolveSession(models.Model):

    STATUS_CHOICES=[
        ('pending','Pending'),
        ('running','Running'),
        ('solved','Solved'),
        ('failed','Failed'),
        ('rejected', 'Rejected'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True,
    )
    target_input=models.TextField()
    context_notes=models.TextField(blank=True)
    overall_goal=models.TextField(blank=True)
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    final_report=models.TextField(blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session {self.id} - {self.status}"


class AgentEvent(models.Model):

    EVENT_TYPES = [
        ('agent_started', 'Agent Started'),
        ('tool_call', 'Tool Call'),
        ('tool_result', 'Tool Result'),
        ('agent_finished', 'Agent Finished'),
        ('handoff', 'Handoff Decision'),
    ]
    session = models.ForeignKey(SolveSession, on_delete=models.CASCADE, related_name='events')
    agent_name = models.CharField(max_length=50)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.agent_name} - {self.event_type}"