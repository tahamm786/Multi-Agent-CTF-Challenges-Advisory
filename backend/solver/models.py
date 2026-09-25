from django.db import models
 

class Challenge(models.Model):

    CHALLENGE_TYPES=[
        ('web','Web Exploitation'), #STORED NAME -> DISPLAYED NAME
        ('crypto','Cryptography'),
        ('forensics','Forensics'),
        ('binary', 'Binary Exploit/Reverse Engineering')
    ]

    name=models.CharField(max_length=200) # LIKE CHAR IN SQL
    challenge_type=models.CharField(max_length=20,choices=CHALLENGE_TYPES)
    target_url=models.URLField(blank=True,null=True) #NULL IS FOR DB LEVEL and BLANK IS FOR DJANGO FORM ACCEPTANCE BLANK
    description=models.TextField(blank=True) #LIKE VARCHAR
    created_at=models.DateTimeField(auto_now_add=True)


    def __str__(self): #PRINTING THIS OBJECT
        return self.name


class SolveSession(models.Model):

    STATUS_CHOICES=[
        ('pending','Pending'),
        ('running','Running'),
        ('solved','Solved'),
        ('failed','Failed')
    ]

    challenge=models.ForeignKey(Challenge,on_delete=models.CASCADE,related_name='sessions') # ONE CHALLENGE MULTIPLE SESSIONS .. CHALLENGE GONE SESSIONS GONE
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    created_at=models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session for {self.challenge.name} - {self.status}"