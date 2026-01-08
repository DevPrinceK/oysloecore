from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiv1', '0028_chatroom_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='is_closed',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='If True, members can read history but cannot send new messages.',
            ),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='is_deleted',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Soft-delete flag. Deleted chatrooms are excluded from all chatroom/message retrieval.',
            ),
        ),
    ]
