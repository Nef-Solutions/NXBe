from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0002_professional_trade'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS postgis',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
