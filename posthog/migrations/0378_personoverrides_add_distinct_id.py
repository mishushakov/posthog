# Generated by Django 3.2.19 on 2023-12-21 23:36

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):
    dependencies = [
        ("posthog", "0377_flatpersonoverride"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="flatpersonoverride",
            name="flatpersonoverride_unique_old_person_by_team",
        ),
        migrations.RemoveConstraint(
            model_name="flatpersonoverride",
            name="flatpersonoverride_check_circular_reference",
        ),
        migrations.RemoveIndex(
            model_name="flatpersonoverride",
            name="posthog_fla_team_id_224253_idx",
        ),
        migrations.AddField(
            model_name="flatpersonoverride",
            name="distinct_id",
            field=models.CharField(max_length=400, null=True),
        ),
        migrations.AddField(
            model_name="pendingpersonoverride",
            name="distinct_id",
            field=models.CharField(max_length=400, null=True),
        ),
        migrations.AddIndex(
            model_name="flatpersonoverride",
            index=models.Index(
                fields=["team_id", "override_person_id", "distinct_id"], name="posthog_fla_team_id_fbe072_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="flatpersonoverride",
            constraint=models.UniqueConstraint(
                fields=("team_id", "old_person_id", "distinct_id"), name="flatpersonoverride_unique_old_person_by_team"
            ),
        ),
        migrations.AddConstraint(
            model_name="flatpersonoverride",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("distinct_id__isnull", True),
                    ("old_person_id__exact", django.db.models.expressions.F("override_person_id")),
                    _negated=True,
                ),
                name="flatpersonoverride_check_circular_reference",
            ),
        ),
    ]
