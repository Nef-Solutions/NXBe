import django.db.models.deletion
from django.db import migrations, models


def create_default_subscription_plan(apps, schema_editor):
    Plan = apps.get_model('payments', 'ProfessionalSubscriptionPlan')
    Plan.objects.get_or_create(
        code='professional-monthly',
        defaults={
            'name': 'Suscripción profesional mensual',
            'amount': 10000,
            'duration_months': 1,
            'is_active': True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_paymenttransaction_professional_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfessionalSubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=60, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('amount', models.DecimalField(decimal_places=0, max_digits=10)),
                ('duration_months', models.PositiveSmallIntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.AddConstraint(
            model_name='professionalsubscriptionplan',
            constraint=models.CheckConstraint(
                condition=models.Q(('amount__gt', 0)),
                name='subscription_plan_amount_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='professionalsubscriptionplan',
            constraint=models.CheckConstraint(
                condition=models.Q(('duration_months__gt', 0)),
                name='subscription_plan_duration_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='professionalsubscriptionplan',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('is_active',),
                name='only_one_active_subscription_plan',
            ),
        ),
        migrations.RunPython(create_default_subscription_plan, migrations.RunPython.noop),
        migrations.AddField(
            model_name='paymenttransaction',
            name='subscription_plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='payments',
                to='payments.professionalsubscriptionplan',
            ),
        ),
        migrations.AddField(
            model_name='paymenttransaction',
            name='subscription_duration_months',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddConstraint(
            model_name='paymenttransaction',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(('subscription_plan__isnull', True))
                    | models.Q(('professional__isnull', False), ('visit__isnull', True))
                ),
                name='subscription_plan_only_for_professional_payment',
            ),
        ),
    ]
