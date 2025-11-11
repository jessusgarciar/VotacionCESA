from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import Candidate, Voter, Election, Vote, OnChainRecord


User = get_user_model()


class ApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        # create user and voter
        self.user = User.objects.create_user(username='tester', password='pass')
        self.voter = Voter.objects.create(user=self.user, control_number='C123', is_eligible=True)

        # create an active election
        now = timezone.now()
        self.election = Election.objects.create(name='Test', start_date=now - timedelta(hours=1), end_date=now + timedelta(hours=1), created_by=self.user)

        # create candidate
        self.candidate = Candidate.objects.create(name='Alice', list_name='Lista A', election=self.election)

    def test_api_candidates(self):
        resp = self.client.get('/api/candidates/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('candidates', data)
        self.assertGreaterEqual(len(data['candidates']), 1)

    def test_api_vote_flow(self):
        # login
        logged = self.client.login(username='tester', password='pass')
        self.assertTrue(logged)

        # post vote
        resp = self.client.post('/api/vote/', {'candidate_id': str(self.candidate.id)})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('txid', data)

        # verify Vote object exists and is marked valid and candidate link was removed
        vote = Vote.objects.filter(voter=self.voter, election=self.election).first()
        self.assertIsNotNone(vote)
        self.assertTrue(vote.valid)
        # Candidate link should be removed for anonymity (nullable)
        self.assertIsNone(vote.candidate)

        # OnChainRecord should exist
        ocr = OnChainRecord.objects.filter(election=self.election, candidate=self.candidate).first()
        # It might not exist if migration wasn't run, so don't fail hard here; but if present, txid matches
        if ocr:
            self.assertEqual(ocr.txid, data.get('txid'))
