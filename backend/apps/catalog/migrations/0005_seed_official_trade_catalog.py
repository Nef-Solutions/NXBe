from django.db import migrations


OFFICIAL_TRADES = (
    ('Gasfitería', 'gasfiter, gasfíter, gasfitería, calefont, cañerías'),
    ('Electricidad', 'eléctrico, electricista, electricidad, enchufes, tablero'),
    ('Soldador', 'soldador, soldadura'),
    ('Carpintero', 'carpintero, carpintería'),
    ('Electrónico', 'electrónico, electrónica'),
    ('Yesero', 'yesero, yesería'),
    ('Aseo', 'aseo, limpieza de hogar'),
    ('Albañil', 'albañil, albañilería'),
    ('Ventanero', 'ventanero, ventanas'),
    ('Guardia', 'guardia, seguridad'),
    ('Ceramista', 'ceramista, cerámica, instalación de cerámica'),
    ('Pintor', 'pintor, pintura'),
    ('Refrigeración', 'refrigeración, refrigerador'),
    ('Aire acondicionado', 'aire acondicionado, climatización'),
    ('Instalador de cámaras', 'instalador de cámaras, cámaras de seguridad, CCTV'),
    ('Destape de alcantarillado', 'destape, alcantarillado, desagüe'),
    ('Costurera', 'costurera, costura, arreglos de ropa'),
    ('Peluquería a domicilio', 'peluquería, peluquero, peluquera a domicilio'),
    ('Mecánico', 'mecánico, mecánica, automóvil'),
    ('Cerrajería', 'cerrajero, cerrajería, cerradura, llave'),
    ('Mueblista', 'mueblista, muebles, armado de muebles'),
    ('Trazador', 'trazador, trazado de construcción'),
    ('Ayudante por día', 'ayudante, jornal, trabajo por día'),
    ('Excavador', 'excavador, excavación'),
    ('Instalador de piscinas', 'instalador de piscinas, piscinas'),
    ('Vulcanización', 'vulcanización, vulca, neumáticos'),
    ('Piso flotante', 'piso flotante, instalación de pisos'),
    ('Techumbre', 'techumbre, techo, reparación de techos'),
    ('Instalador de campanas de cocina', 'campana de cocina, extractor de cocina'),
    ('Ampliaciones', 'ampliaciones, ampliación de vivienda'),
    ('Radier', 'radier, hormigón'),
    ('Domótica', 'domótica, casa inteligente'),
    ('Iluminación', 'iluminación, luminarias'),
    ('Decoración', 'decoración, decorador'),
    ('Paneles solares', 'paneles solares, energía solar'),
    ('Instalador', 'instalador, instalación'),
    ('Instalación de malla anticaída', 'malla anticaída, malla de seguridad'),
    ('Cerradura inteligente', 'cerradura inteligente, smart lock'),
    ('Alarmas', 'alarmas, sistema de alarma'),
    ('Citófono y videoportero', 'citófono, videoportero, portero eléctrico'),
    ('Impermeabilizador', 'impermeabilizador, impermeabilización, filtración'),
    ('Tabiquero', 'tabiquero, tabiquería'),
    ('Papel mural', 'papel mural, papel decomural, empapelado'),
    ('Cornisas y zócalos', 'cornisas, zócalos, molduras'),
    ('Aislación térmica', 'aislación térmica, aislación, aislamiento'),
    ('Fumigación y control de plagas', 'fumigación, plagas, control de plagas'),
    ('Lavado de alfombras', 'lavado de alfombras, limpieza de alfombras'),
    ('Lavado de autos', 'lavado de autos, lavado de vehículos'),
    ('Jardinero', 'jardinero, jardinería'),
    ('Retiro de escombros', 'retiro de escombros, escombros'),
    ('Regadío automático', 'regadío automático, riego automático'),
    ('Instalador de bombas', 'instalador de bombas, bombas de agua'),
    ('Pasto sintético', 'pasto sintético, césped artificial'),
    ('Quinchos y parrillas', 'quinchos, parrillas'),
    ('Pérgolas y terrazas', 'pérgolas, terrazas'),
    ('Limpieza de piscinas', 'limpieza de piscinas, mantención de piscinas'),
    ('Cortinas roller y persianas', 'cortinas roller, persianas'),
    ('Tapicería', 'tapicería, tapicero, retapizado'),
    ('Espejos y vidrios', 'espejos, vidrios, cristales'),
    ('Tinas y jacuzzis', 'tinas, jacuzzi, jacuzzis'),
    ('Electromecánico', 'electromecánico, electromecánica'),
    ('Técnico de consolas', 'técnico de consolas, reparación de consolas'),
    ('Cuidador de adulto mayor', 'cuidador, cuidado de adulto mayor'),
    ('Niñera', 'niñera, cuidado infantil'),
    ('Paseador de animales', 'paseador de animales, paseo de perros'),
    ('Peluquería canina', 'peluquería canina, peluquero canino'),
)


def seed_official_trades(apps, schema_editor):
    TradeCategory = apps.get_model('catalog', 'TradeCategory')

    for name, keywords in OFFICIAL_TRADES:
        TradeCategory.objects.get_or_create(
            name=name,
            defaults={'keywords': keywords},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_seed_default_catalog'),
    ]

    operations = [
        migrations.RunPython(seed_official_trades, migrations.RunPython.noop),
    ]
