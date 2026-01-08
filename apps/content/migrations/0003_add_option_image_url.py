# Generated migration for Option.image_url field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_add_image_url_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='option',
            name='image_url',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Cloudinary URL for option card image',
                verbose_name='image URL'
            ),
        ),
    ]
