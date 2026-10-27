
import django.db.models.deletion
from django.db import migrations, models


PROFILE_NAMES = [
    "Administrator",
    "Standard",
    "Developer",
    "Client",
    "Human Resource",
]


def convert_profiles(apps, schema_editor):
    User = apps.get_model("users", "User")
    Profile = apps.get_model("users", "Profile")
    db_alias = schema_editor.connection.alias

    profile_ids = {}

    for name in PROFILE_NAMES:
        profile, _ = Profile.objects.using(db_alias).get_or_create(
            name=name,
            defaults={
                "is_active": True,
                "is_default": name == "Standard",
            },
        )
        profile_ids[name] = profile.pk

    for name, profile_id in profile_ids.items():
        User.objects.using(db_alias).filter(
            profiles=name
        ).update(profiles=str(profile_id))


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_alter_user_profiles"),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
            ],
        ),
        migrations.RunPython(
            convert_profiles,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="user",
            name="profiles",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="users.profile",
            ),
        ),
    ]
