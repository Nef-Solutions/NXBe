from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0003_professionalprofile_verification_status')]

    operations = [
        migrations.AddField(model_name='user', name='address', field=models.CharField(blank=True, max_length=255, verbose_name='Dirección')),
        migrations.AddField(model_name='user', name='commune', field=models.CharField(blank=True, max_length=120, verbose_name='Comuna')),
        migrations.AddField(model_name='user', name='privacy_policy_accepted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='user', name='privacy_policy_version', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='user', name='rut', field=models.CharField(blank=True, max_length=12, null=True, unique=True, verbose_name='RUT')),
    ]