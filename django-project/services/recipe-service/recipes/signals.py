from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models.signals import pre_delete
from django.dispatch import receiver

User = get_user_model()


@receiver(pre_delete, sender=User)
def delete_abtest_records(sender, instance, **kwargs):
    """Delete ab-test rows that reference this user before Django deletes the user.

    The recipes_abtest* tables are not Django-managed models so their FK
    constraints use NO ACTION rather than CASCADE. Without this signal,
    deleting a user raises an IntegrityError and returns a 500.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM recipes_abtestassignment WHERE user_id = %s",
            [instance.pk],
        )
        cursor.execute(
            "DELETE FROM recipes_abtestevent WHERE user_id = %s",
            [instance.pk],
        )
        cursor.execute(
            "DELETE FROM recipes_abtestexposure WHERE user_id = %s",
            [instance.pk],
        )
