import django.db.models.deletion
import django.utils.timezone
import files.utils.file_utils
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to=files.utils.file_utils.generate_file_upload_path)),
                ('original_filename', models.CharField(db_index=True, max_length=255)),
                ('file_type', models.CharField(db_index=True, max_length=100)),
                ('size', models.BigIntegerField(db_index=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('file_hash', models.CharField(db_index=True, help_text='SHA-256 hash of file content', max_length=64)),
                ('is_reference', models.BooleanField(db_index=True, default=False, help_text='True if this file is a reference to another file (duplicate)')),
                ('reference_count', models.IntegerField(default=1, help_text='Number of references pointing to this file')),
                ('original_file', models.ForeignKey(blank=True, help_text='Points to the original file if this is a reference', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='references', to='files.file')),
            ],
            options={
                'ordering': ['-uploaded_at'],
                'indexes': [
                    models.Index(fields=['user_id', 'uploaded_at'], name='idx_user_uploaded'),
                    models.Index(fields=['user_id', 'file_type'], name='idx_user_filetype'),
                    models.Index(fields=['user_id', 'size'], name='idx_user_size'),
                    models.Index(fields=['user_id', 'original_filename'], name='idx_user_filename'),
                    models.Index(fields=['file_hash', 'is_reference'], name='idx_hash_reference'),
                    models.Index(fields=['file_hash'], name='idx_hash_lookup'),
                    models.Index(fields=['uploaded_at'], name='idx_uploaded_date'),
                    models.Index(fields=['user_id', 'uploaded_at', 'file_type'], name='idx_user_date_type'),
                    models.Index(fields=['size'], name='idx_size'),
                    models.Index(fields=['user_id', 'size', 'uploaded_at'], name='idx_user_size_date'),
                    models.Index(fields=['is_reference', 'reference_count'], name='idx_reference_count'),
                    models.Index(fields=['original_file'], name='idx_original_file'),
                ],
            },
        ),
        migrations.CreateModel(
            name='UserStorageStats',
            fields=[
                ('user_id', models.CharField(max_length=255, primary_key=True, serialize=False, unique=True)),
                ('total_storage_used', models.BigIntegerField(default=0, help_text='Actual storage used (bytes) after deduplication')),
                ('original_storage_used', models.BigIntegerField(default=0, help_text='Storage that would be used without deduplication')),
                ('file_count', models.IntegerField(default=0, help_text='Total number of files uploaded by user')),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'User Storage Statistics',
                'verbose_name_plural': 'User Storage Statistics',
            },
        ),
        migrations.CreateModel(
            name='RateLimitRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('window_start', models.DateTimeField(db_index=True)),
                ('request_count', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['-window_start'],
                'indexes': [
                    models.Index(fields=['user_id', 'window_start'], name='ratelimit_user_window'),
                ],
                'unique_together': {('user_id', 'window_start')},
            },
        ),
        migrations.CreateModel(
            name='UploadJob',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.CharField(db_index=True, max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('file_size', models.BigIntegerField()),
                ('file_type', models.CharField(max_length=100)),
                ('status', models.CharField(
                    choices=[
                        ('queued', 'Queued'),
                        ('processing', 'Processing'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('duplicate', 'Duplicate Found'),
                    ],
                    db_index=True,
                    default='queued',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('file_id', models.UUIDField(blank=True, help_text='ID of created file if successful', null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('is_duplicate', models.BooleanField(default=False)),
                ('duplicate_file_id', models.UUIDField(blank=True, help_text='ID of existing file if duplicate', null=True)),
                ('kafka_message_id', models.CharField(blank=True, max_length=255, null=True)),
                ('retry_count', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user_id', 'status'], name='uploadjob_user_status'),
                    models.Index(fields=['status', 'created_at'], name='uploadjob_status_date'),
                    models.Index(fields=['user_id', 'created_at'], name='uploadjob_user_date'),
                ],
            },
        ),
    ]
