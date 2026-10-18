import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0004_user_profile_and_privacy')]

    operations = [
        migrations.AddField(model_name='user', name='account_status', field=models.CharField(choices=[('ACTIVE', 'Activa'), ('SUSPENDED', 'Suspendida'), ('BLOCKED', 'Bloqueada'), ('DEACTIVATED', 'Dada de baja')], default='ACTIVE', max_length=20)),
        migrations.AddField(model_name='user', name='failed_login_attempts', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='user', name='locked_until', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='user', name='profile_photo', field=models.ImageField(blank=True, upload_to='profiles/')),
        migrations.CreateModel(
            name='VerificationCaseMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('admin_response', models.TextField(blank=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('professional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_messages', to='authentication.professionalprofile')),
            ],
            options={'ordering': ('-created_at',)},
        ),
    ]