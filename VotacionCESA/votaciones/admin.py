from django.contrib import admin
from .models import Candidate, Voter, Vote, CandidateMember, Election


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('list_name', 'name', 'votes_count', 'election')
    list_filter = ('election',)
    inlines = []


class CandidateMemberInline(admin.TabularInline):
    model = CandidateMember
    extra = 1
    fields = ('full_name', 'role', 'order')

# attach inline to CandidateAdmin
CandidateAdmin.inlines = [CandidateMemberInline]


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'created_by')
    search_fields = ('name',)


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('user', 'control_number', 'is_eligible')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'candidate', 'timestamp', 'hash_block', 'valid')
