# Generated by Django 5.0.6 on 2024-07-29 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playlists', '0002_playlist_idx_playlist_rating_avg_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playlist',
            name='related',
            field=models.ManyToManyField(blank=True, related_name='related_playlist', through='playlists.PlaylistRelated', to='playlists.playlist'),
        ),
    ]
