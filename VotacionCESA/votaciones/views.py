from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from .models import Candidate, Voter, Vote, CandidateMember, Election, OnChainRecord
from . import algorand_reader
from django.db.models import Q
from django.contrib.auth import get_user_model


@require_GET
def api_candidates(request):
    # optional: filter by election_id query param
    election_id = request.GET.get('election_id')
    qs = Candidate.objects.all().order_by('-votes_count')
    if election_id:
        # include candidates explicitly assigned to the election
        # and also candidates without an election (fallback for admin-created candidates)
        qs = qs.filter(Q(election_id=election_id) | Q(election__isnull=True))
    else:
        # try to use the active election if present
        from django.utils import timezone
        now = timezone.now()
        active = Election.objects.filter(start_date__lte=now, end_date__gte=now).first()
        if active:
            qs = qs.filter(election=active)
    data = [
        {
            'id': c.id,
            'name': c.name,
            'list_name': c.list_name,
            'image_url': c.image_url,
            'manifesto': c.manifesto,
            # Prefer indexer-derived counts when available, otherwise prefer local on-chain mirror,
            # and finally fall back to DB count.
            'votes_count': (algorand_reader.get_counts_for_election(c.election) or {}).get(c.id)
                           or OnChainRecord.objects.filter(candidate=c).count()
                           or c.votes_count,
            'members': [
                {
                    'full_name': m.full_name,
                    'role': m.role,
                } for m in c.members.all()
            ],
        } for c in qs
    ]
    return JsonResponse({'candidates': data})


@require_POST
def api_vote(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden('authentication required')

    candidate_id = request.POST.get('candidate_id')
    if not candidate_id:
        return HttpResponseBadRequest('candidate_id required')

    candidate = get_object_or_404(Candidate, pk=candidate_id)
    # determine election (either provided or from candidate)
    election_id = request.POST.get('election_id')
    election = None
    if election_id:
        election = get_object_or_404(Election, pk=election_id)
    else:
        election = candidate.election
    # Ensure the logged user has a Voter profile
    try:
        voter = request.user.voter
    except Exception:
        return HttpResponseBadRequest('user not registered as voter')

    # Check election validity (dates)
    from django.utils import timezone
    now = timezone.now()
    if election and not (election.start_date <= now <= election.end_date):
        return HttpResponseBadRequest('election not active')

    # Check if voter already voted in this election
    if Vote.objects.filter(voter=voter, election=election).exists():
        return HttpResponseBadRequest('user already voted in this election')

    vote = Vote.objects.create(voter=voter, candidate=candidate, election=election)
    # attempt to register the vote on-chain (this function will mark vote.valid and
    # populate vote.hash_block on success)
    txid = None
    try:
        txid = vote.register_on_blockchain()
    except Exception:
        txid = None

    # update counts locally (DB counts are a fallback; authoritative counts should come
    # from the blockchain reader in a full implementation)
    try:
        candidate.votes_count = Vote.objects.filter(candidate=candidate).count()
        candidate.save()
    except Exception:
        pass

    # mark voter as having voted (simple flag)
    try:
        voter.has_voted = True
        voter.save(update_fields=['has_voted'])
    except Exception:
        pass

    # compute total votes across candidates
    total_votes = Vote.objects.count()

    resp = {
        'status': 'ok',
        'vote_id': vote.id,
        'candidate_votes': candidate.votes_count,
        'total_votes': total_votes,
        'txid': txid,
    }

    return JsonResponse(resp)


@require_GET
def api_elections(request):
    from django.utils import timezone
    now = timezone.now()
    qs = Election.objects.all().order_by('-start_date')
    data = []
    for e in qs:
        data.append({
            'id': e.id,
            'name': e.name,
            'start_date': e.start_date.isoformat(),
            'end_date': e.end_date.isoformat(),
            'is_active': e.start_date <= now <= e.end_date,
        })
    return JsonResponse({'elections': data})


@require_GET
def api_stats(request):
    """Return simple statistics: total_votes, eligible_voters, participation (%) for an election (optional)."""
    election_id = request.GET.get('election_id')
    from django.utils import timezone
    now = timezone.now()
    # eligible voters
    eligible = Voter.objects.filter(is_eligible=True).count()
    if election_id:
        # prefer indexer counts
        idx_counts = None
        try:
            # attempt to use indexer counts for this election
            idx_counts = algorand_reader.get_counts_from_indexer(int(election_id))
        except Exception:
            idx_counts = None

        if idx_counts is not None:
            total_votes = sum(idx_counts.values())
        else:
            total_votes = OnChainRecord.objects.filter(election_id=election_id).count() or Vote.objects.filter(election_id=election_id).count()
    else:
        # if no election specified, count all votes
        active = Election.objects.filter(start_date__lte=now, end_date__gte=now).first()
        if active:
            idx_counts = algorand_reader.get_counts_for_election(active)
            if idx_counts is not None:
                total_votes = sum(idx_counts.values())
            else:
                total_votes = OnChainRecord.objects.filter(election=active).count() or Vote.objects.filter(election=active).count()
        else:
            total_votes = OnChainRecord.objects.count() or Vote.objects.count()

    participation = 0.0
    if eligible:
        participation = round((total_votes / eligible) * 100, 1)

    return JsonResponse({'total_votes': total_votes, 'eligible_voters': eligible, 'participation': participation})
