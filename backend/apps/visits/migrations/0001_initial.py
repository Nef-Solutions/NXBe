import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authentication', '0005_account_security_and_case_messages'),
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('problem_description', models.TextField()),
                ('tentative_schedule', models.CharField(blank=True, max_length=255)),
                ('visit_address', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('ACCEPTED', 'Aceptada'), ('REJECTED', 'Rechazada'), ('CANCELLED', 'Cancelada'), ('EXPIRED', 'Vencida'), ('PROFESSIONAL_FINISHED', 'Finalizada por profesional'), ('COMPLETED', 'Completada'), ('FORCED_CLOSED', 'Cerrada por administración')], default='PENDING', max_length=30)),
                ('rejection_reason', models.TextField(blank=True)),
                ('professional_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('client_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visit_requests', to=settings.AUTH_USER_MODEL)),
                ('professional', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visit_requests', to='authentication.professionalprofile')),
                ('specialty', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='visit_requests', to='catalog.specialty')),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(name='ProfessionalContent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=160)), ('description', models.TextField(blank=True)),
            ('module', models.CharField(choices=[('TAX', 'Tributario'), ('SAFETY', 'Seguridad'), ('MANAGEMENT', 'Gestión')], max_length=20)),
            ('url', models.URLField()), ('is_external', models.BooleanField(default=False)), ('is_visible', models.BooleanField(default=True)), ('order', models.PositiveIntegerField(default=0)),
        ]),
        migrations.CreateModel(name='SupportTicket', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('subject', models.CharField(max_length=160)), ('description', models.TextField()), ('response', models.TextField(blank=True)),
            ('status', models.CharField(choices=[('OPEN', 'Abierto'), ('IN_REVIEW', 'En revisión'), ('RESOLVED', 'Resuelto')], default='OPEN', max_length=20)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ('visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='support_tickets', to='visits.visitrequest')),
        ]),
        migrations.CreateModel(name='Notification', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=160)), ('message', models.TextField()), ('is_read', models.BooleanField(default=False)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ('related_visit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='visits.visitrequest')),
        ], options={'ordering': ('-created_at',)}),
        migrations.CreateModel(name='AfterSalesClaim', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('description', models.TextField()), ('professional_response', models.TextField(blank=True)), ('admin_resolution', models.TextField(blank=True)),
            ('status', models.CharField(choices=[('OPEN', 'Abierto'), ('PROFESSIONAL_RESPONDED', 'Respondido por profesional'), ('ESCALATED', 'Escalado'), ('RESOLVED', 'Resuelto')], default='OPEN', max_length=30)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('resolved_at', models.DateTimeField(blank=True, null=True)),
            ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='claims_opened', to=settings.AUTH_USER_MODEL)),
            ('visit', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='after_sales_claim', to='visits.visitrequest')),
        ]),
        migrations.CreateModel(name='AdminAuditLog', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('action', models.CharField(max_length=120)), ('reason', models.TextField()), ('target_type', models.CharField(max_length=120)), ('target_id', models.PositiveBigIntegerField()), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('administrator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='admin_actions', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ('-created_at',)}),
        migrations.CreateModel(name='Rating', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('quality', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
            ('punctuality', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
            ('treatment', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
            ('comment', models.TextField(blank=True)), ('created_at', models.DateTimeField(auto_now_add=True)),
            ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ratings_given', to=settings.AUTH_USER_MODEL)),
            ('target', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ratings_received', to=settings.AUTH_USER_MODEL)),
            ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='visits.visitrequest')),
        ], options={'constraints': [models.UniqueConstraint(fields=('visit', 'author'), name='unique_rating_per_author_visit')]}),
        migrations.CreateModel(name='ContentProgress', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('completed_at', models.DateTimeField(auto_now_add=True)),
            ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='visits.professionalcontent')),
            ('professional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_progress', to='authentication.professionalprofile')),
        ], options={'constraints': [models.UniqueConstraint(fields=('professional', 'content'), name='unique_content_progress')]}),
    ]