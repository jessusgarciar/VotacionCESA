from django.contrib import admin
from .models import Candidate, Voter, Vote, CandidateMember, Election
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django import forms
from django.contrib import messages
from django.utils.html import format_html
from .utils import import_voters_from_file


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
    list_display = ('name', 'start_date', 'end_date', 'created_by', 'download_report')
    search_fields = ('name',)
    
    def download_report(self, obj):
        """Muestra un botón para descargar el reporte PDF de la elección."""
        url = reverse('votaciones:election_pdf_by_id', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">📄 PDF</a>',
            url
        )
    download_report.short_description = 'Reporte'
    download_report.allow_tags = True


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('user', 'control_number', 'is_eligible')
    change_list_template = 'admin/votaciones/voter_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('import-voters/', self.admin_site.admin_view(self.import_voters_view), name='votaciones_import_voters')
        ]
        return custom + urls

    class UploadForm(forms.Form):
        csvfile = forms.FileField(label='CSV file')
        create_users = forms.BooleanField(required=False, initial=True)
        default_password = forms.CharField(required=False)

    def import_voters_view(self, request):
        if not request.user.is_staff:
            return redirect('admin:login')
        if request.method == 'POST':
            form = self.UploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = request.FILES['csvfile']
                create_users = form.cleaned_data.get('create_users')
                default_password = form.cleaned_data.get('default_password') or None
                summary = import_voters_from_file(f, create_users=create_users, default_password=default_password)
                for level, msg in summary.get('messages', []):
                    if level == 'success':
                        messages.success(request, msg)
                    elif level == 'warning':
                        messages.warning(request, msg)
                    else:
                        messages.info(request, msg)
                messages.success(request, f"Import completed: created={summary['created']} updated={summary['updated']} skipped={summary['skipped']}")
                return redirect('..')
        else:
            form = self.UploadForm()
        context = {
            'opts': self.model._meta,
            'form': form,
            'title': 'Import voters from CSV',
        }
        return render(request, 'admin/votaciones/import_voters.html', context)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'candidate', 'timestamp', 'hash_block', 'valid')
