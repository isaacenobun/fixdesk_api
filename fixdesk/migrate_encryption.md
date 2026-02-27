Step 1 — Add a New Encrypted Column

Keep the original column untouched.

Add:

first_name_encrypted = EncryptedTextField(null=True, blank=True)


Now your table looks like:

id	first_name (plaintext)	first_name_encrypted
1	John	NULL

Nothing breaks yet.

Step 2 — Copy Data Into Encrypted Column

Run a migration:

for user in User.objects.all():
    user.first_name_encrypted = user.first_name
    user.save(update_fields=["first_name_encrypted"])


Now:

id	first_name	first_name_encrypted
1	John	🔒 encrypted blob

Still safe.

No behavior changed yet.

Step 3 — Switch Application to Use Encrypted Field

Update your model:

@property
def first_name_secure(self):
    return self.first_name_encrypted


Or replace usage everywhere in serializers/views.

Now your app reads from encrypted column.

Plaintext column still exists but is unused.

Still no downtime.

Step 4 — Remove Plaintext Column

After verifying everything works:

Drop first_name

Rename first_name_encrypted → first_name

Now your table is clean:

id	first_name (encrypted)

Migration complete.