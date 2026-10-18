import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('catalog', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='ProfessionalTrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('years_experience', models.PositiveSmallIntegerField(default=0)),
                ('description', models.TextField(blank=True)),
                ('certification', models.FileField(blank=True, upload_to='certifications/')),
                ('certification_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='professional_trades', to='catalog.tradecategory')),
                ('professional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trades', to='authentication.professionalprofile')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('professional', 'category'), name='unique_active_trade_category')]},
        ),
    ]