from django.db import migrations


SAFETY_RESOURCES = (
    (
        'Accidentes y enfermedades profesionales',
        'CAPACITACION ACCIDENTES Y ENFERMEDADES PROFESIONALES',
        'SimDell Consultores. Diferencias entre accidente laboral y de trayecto, '
        'enfermedad profesional, agentes de riesgo y procedimiento de denuncia.',
        'https://www.youtube.com/watch?v=Y2kBQFdJMz4',
    ),
    (
        'Plan de emergencia y uso de extintores',
        'VIDEO CAPACITACION PLAN DE EMERGENCIA Y USO MATAFUEGOS',
        'SimDell Consultores. Roles de evacuación, respuesta ante incendios, '
        'clases de fuego y uso de extintor manual.',
        'https://www.youtube.com/watch?v=E78Lo3FAGko',
    ),
    (
        'Uso de elementos de protección personal',
        'CAPACITACION DE USO DE ELEMENTOS DE PROTECCION PERSONAL (EPP)',
        'SimDell Consultores. Clasificación, cuidado e inspección de EPP, '
        'incluyendo protección para trabajo en altura.',
        'https://www.youtube.com/watch?v=UHRJ1-CwsWE',
    ),
    (
        'Preparación y respuesta a emergencias',
        'Preparación y respuesta a emergencia',
        'Environtel. Brigadas, niveles de emergencia, equipamiento y protocolos '
        'ante sismos, incendios y derrames.',
        'https://www.youtube.com/watch?v=fsG0sJlIgLI',
    ),
    (
        'Introducción a la seguridad y salud en el trabajo',
        'Introducción a la Seguridad y Salud en el Trabajo (SST)',
        'Environtel. Peligros, riesgos, accidentes, investigación de causas y '
        'medidas de control en oficina y terreno.',
        'https://www.youtube.com/watch?v=eUIvPfOQ2k4',
    ),
    (
        'Conceptos básicos de seguridad y salud en el trabajo',
        'Conceptos basicos de Seguridad y Salud en el Trabajo',
        'Environtel. Prevención de riesgos, accidentes incapacitantes, EPP y '
        'ejemplos de condiciones inseguras.',
        'https://www.youtube.com/watch?v=cpcqOQSIGY0',
    ),
    (
        'Canal Gestor Calidad SSOMA',
        'Canal de gestión de calidad, seguridad, salud ocupacional y medio ambiente.',
        'Canal de YouTube enfocado en gestión de calidad, seguridad, salud '
        'ocupacional y medio ambiente.',
        'https://youtube.com/@gestorcalidadssoma',
    ),
    (
        'Canal Mutual de Seguridad CChC',
        'Canal oficial de Mutual de Seguridad CChC.',
        'Cápsulas y charlas sobre prevención de riesgos laborales, seguridad '
        'vial y salud ocupacional.',
        'https://youtube.com/@mutualtv',
    ),
    (
        'Lista de reproducción de seguridad',
        'Lista de reproducción de videos de seguridad.',
        'Lista de reproducción compartida como material complementario de seguridad.',
        'https://youtube.com/playlist?list=PLWCrmTUW4-e_rzvkeyXgqEkEk4GemRvM0',
    ),
)


def seed_safety_resources(apps, schema_editor):
    ProfessionalContent = apps.get_model('visits', 'ProfessionalContent')

    for order, (title, description, details, url) in enumerate(SAFETY_RESOURCES, start=1):
        ProfessionalContent.objects.get_or_create(
            url=url,
            defaults={
                'title': title,
                'description': f'{description} {details}',
                'module': 'SAFETY',
                'is_external': True,
                'is_visible': True,
                'order': order,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_seed_official_trade_catalog'),
        ('visits', '0003_visitrequest_completed_at'),
    ]

    operations = [
        migrations.RunPython(seed_safety_resources, migrations.RunPython.noop),
    ]
