from django.db import migrations


DEFAULT_CATALOG = (
    {
        'name': 'Electricidad',
        'keywords': 'enchufe,cable,tablero,instalación eléctrica',
        'specialties': ('Instalaciones eléctricas',),
    },
    {
        'name': 'Gasfitería',
        'keywords': 'fuga,llave,cañería,calefont',
        'specialties': ('Reparación de fugas',),
    },
    {
        'name': 'Cerrajería',
        'keywords': 'cerradura,llave,puerta',
        'specialties': ('Apertura y cambio de cerraduras',),
    },
)


def create_default_catalog(apps, schema_editor):
    TradeCategory = apps.get_model('catalog', 'TradeCategory')
    Specialty = apps.get_model('catalog', 'Specialty')

    for category_data in DEFAULT_CATALOG:
        category, _ = TradeCategory.objects.get_or_create(
            name=category_data['name'],
            defaults={'keywords': category_data['keywords']},
        )
        if category.keywords != category_data['keywords']:
            category.keywords = category_data['keywords']
            category.save(update_fields=['keywords'])

        for specialty_name in category_data['specialties']:
            Specialty.objects.get_or_create(
                category=category,
                name=specialty_name,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_enable_postgis'),
    ]

    operations = [
        migrations.RunPython(create_default_catalog, migrations.RunPython.noop),
    ]
