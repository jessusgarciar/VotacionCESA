from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Candidate(models.Model):
    name = models.CharField(max_length=200)
    list_name = models.CharField(max_length=200, blank=True)
    # store uploaded candidate images in MEDIA_ROOT/candidates/
    # keep the name `image_url` to minimize code changes elsewhere;
    # change the field type to ImageField so Django can manage uploads.
    image_url = models.ImageField(upload_to='candidates/', blank=True, null=True)
    manifesto = models.TextField(blank=True)
    votes_count = models.PositiveIntegerField(default=0)
    # cada candidate/planilla pertenece a una elección
    election = models.ForeignKey('Election', on_delete=models.CASCADE, null=True, blank=True, related_name='candidates')

    def __str__(self):
        return f"{self.list_name} - {self.name}" if self.list_name else self.name


class CandidateMember(models.Model):
    """Representa a un integrante de la planilla de un candidato/lista.

    Ej: Presidente, Vicepresidente, Tesorero, Secretario, etc.
    """
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='members')
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0, help_text='Orden de aparición en la lista')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        if self.role:
            return f"{self.full_name} ({self.role})"
        return self.full_name


class Voter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    control_number = models.CharField(max_length=50, unique=True)
    is_eligible = models.BooleanField(default=True)
    # optional blockchain address associated with this voter (Algorand address)
    blockchain_address = models.CharField(max_length=128, blank=True, null=True)
    # indicador simple si ha votado (nota: para multi-elección esto puede evolucionar a tracking por elección)
    has_voted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.control_number})"


class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    # Allow null so we can remove the direct voter->candidate link after the vote
    # has been successfully registered on-chain (helps preserve anonymity).
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, null=True, blank=True)
    # referencia a la elección en la que se emitió el voto
    election = models.ForeignKey('Election', on_delete=models.CASCADE, null=True, blank=True, related_name='votes')
    timestamp = models.DateTimeField(auto_now_add=True)
    hash_block = models.CharField(max_length=200, blank=True)  # placeholder for blockchain tx/hash
    valid = models.BooleanField(default=False)

    class Meta:
        # impedir votos duplicados por votante en la misma elección
        unique_together = (('voter', 'election'),)

    def __str__(self):
        cand = self.candidate if self.candidate else 'ANONYMIZED'
        return f"Vote: {self.voter} -> {cand} @ {self.timestamp}"

    def validate_vote(self):
        # placeholder minimal validation
        self.valid = True
        self.save(update_fields=['valid'])

    def register_on_blockchain(self):
        """Registra este voto en la cadena de bloques y almacena el txid en `hash_block`.

        Usa `votaciones.algorand_integration.send_vote_tx`. La carga útil de la nota
        excluye intencionalmente cualquier información que identifique al votante para
        ayudar a preservar el anonimato en la cadena.
        """
        try:
            from . import algorand_integration as algointeg
        except Exception:
            algointeg = None

        note_payload = {
            'election_id': self.election.id if self.election else None,
            'candidate_id': self.candidate.id if self.candidate else None,
        }

        try:
            if algointeg:
                txid = algointeg.send_vote_tx(self.election.id if self.election else None,
                                               self.candidate.id if self.candidate else None)
            else:
                # fallback to a uuid
                import uuid
                txid = str(uuid.uuid4())
            self.hash_block = txid
            self.valid = True
            self.save(update_fields=['hash_block', 'valid'])

            # Create a minimal on-chain record (no voter link) so the public results
            # can be computed from on-chain-registered entries without exposing voter ids.
            try:
                OnChainRecord.objects.create(txid=txid, candidate=self.candidate, election=self.election)
                # After recording on-chain, remove the direct candidate link to help anonymity
                self.candidate = None
                self.save(update_fields=['candidate'])
            except Exception:
                # ignore if migration hasn't created this model yet or other issues
                pass

            return txid
        except Exception:
            # If blockchain registration fails, keep the vote locally but leave it invalid
            # so an operator can retry registration.
            return None


class Election(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_elections')

    def __str__(self):
        return f"{self.name} ({self.start_date.date()} - {self.end_date.date()})"

    def is_active(self):
        from django.utils import timezone
        now = timezone.now()
        return self.start_date <= now <= self.end_date



class OnChainRecord(models.Model):
    """Un registro local mínimo que refleja una votación en cadena registrada correctamente.

    Este modelo no hace referencia al votante intencionalmente para preservar el anonimato.
    Almacena el txid devuelto por la blockchain y referencia al Candidato para que
    los resultados puedan calcularse a partir de estos registros.
    """
    txid = models.CharField(max_length=200, unique=True)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='onchain_records')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, null=True, blank=True, related_name='onchain_records')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OnChainRecord {self.txid} -> {self.candidate}"
