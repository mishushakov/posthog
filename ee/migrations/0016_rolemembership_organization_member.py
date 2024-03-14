# Generated by Django 4.1.13 on 2024-03-14 13:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("posthog", "0397_projects_backfill"),
        ("ee", "0015_add_verified_properties"),
    ]

    operations = [
        migrations.AddField(
            model_name="rolemembership",
            name="organization_member",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="role_memberships",
                related_query_name="role_membership",
                to="posthog.organizationmembership",
            ),
        ),
    ]
