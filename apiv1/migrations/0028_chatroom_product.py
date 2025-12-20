from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('apiv1', '0027_message_is_media'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chatrooms', to='apiv1.product'),
        ),
    ]
