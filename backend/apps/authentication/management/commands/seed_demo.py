from django.core.management.base import BaseCommand
from django.db import transaction

from apps.authentication.models import ProfessionalProfile, User
from apps.catalog.models import ProfessionalTrade, Specialty, TradeCategory


class Command(BaseCommand):
    help = 'Crea usuarios, profesionales, oficios y especialidades para demostración.'

    @transaction.atomic
    def handle(self, *args, **options):
        category_data = (
            ('Electricidad', 'enchufe,cable,tablero', 'Instalaciones eléctricas'),
            ('Gasfitería', 'fuga,llave,cañería,calefont', 'Reparación de fugas'),
            ('Cerrajería', 'cerradura,llave,puerta', 'Apertura y cambio de cerraduras'),
        )
        categories = []
        for name, keywords, specialty_name in category_data:
            category, _ = TradeCategory.objects.get_or_create(name=name, defaults={'keywords': keywords})
            category.keywords = keywords
            category.save(update_fields=['keywords'])
            specialty, _ = Specialty.objects.get_or_create(category=category, name=specialty_name)
            categories.append((category, specialty))

        def user(email, first_name, last_name, role, rut):
            account = User.objects.filter(email=email).first()
            if account is None:
                account = User(
                    email=email, username=email, first_name=first_name, last_name=last_name,
                    role=role, rut=rut, phone='+56900000000',
                    address='Direccion de demostracion 123', commune='Santiago',
                )
                account.set_password('OverolDemo123!')
                account.save()
            return account

        professional_ruts = ('12345678-5', '98765432-5', '55555555-5')
        for index, (category, specialty) in enumerate(categories, start=1):
            account = user(
                f'profesional{index}@demo.overol.cl', ('Profesional Uno', 'Profesional Dos', 'Profesional Tres')[index - 1], 'Demo',
                User.Role.PROFESSIONAL, professional_ruts[index - 1],
            )
            profile, _ = ProfessionalProfile.objects.get_or_create(
                user=account, defaults={
                    'rut': account.rut,
                    'verification_status': ProfessionalProfile.VerificationStatus.APPROVED,
                    'bio': 'Profesional verificado de demostración.',
                    'coverage_communes': ['Santiago', 'Ñuñoa', 'Providencia'],
                    'work_days': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
                },
            )
            profile.verification_status = ProfessionalProfile.VerificationStatus.APPROVED
            profile.save(update_fields=['verification_status'])
            trade, _ = ProfessionalTrade.objects.get_or_create(
                professional=profile, category=category,
                defaults={'years_experience': 5, 'description': specialty.name},
            )
            specialty.professionals.add(profile)

        user('cliente1@demo.overol.cl', 'Cliente', 'Demo', User.Role.CLIENT, '22222222-2')
        user('cliente2@demo.overol.cl', 'Cliente', 'Prueba', User.Role.CLIENT, '33333333-3')
        admin = user('admin@demo.overol.cl', 'Admin', 'Demo', User.Role.ADMIN, '44444444-4')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=['is_staff', 'is_superuser'])
        self.stdout.write(self.style.SUCCESS('Datos demo creados. Contraseña: OverolDemo123!'))
