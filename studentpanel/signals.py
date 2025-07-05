from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import StudentProfile, FeeChallan

@receiver(post_save, sender=StudentProfile)
def generate_student_id(sender, instance, created, **kwargs):
    if created and not instance.unique_id:
        year_part   = timezone.now().strftime("%y")   # e.g. "25"
        serial      = f"{instance.id:02d}"            # id 1 -> "01"
        instance.unique_id = f"STVT{year_part}/{serial}"
        instance.save()

        # create empty challan placeholder (status = Pending)
        FeeChallan.objects.create(student=instance)
