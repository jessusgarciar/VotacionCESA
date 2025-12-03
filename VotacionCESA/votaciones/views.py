from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
import logging
import io
from datetime import datetime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from .models import Candidate, Voter, Vote, CandidateMember, Election, OnChainRecord, PDFReport
from . import algorand_reader
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import FrontendUserCreationForm, VoterForm, CandidateForm
from django.urls import reverse
from django.db import IntegrityError
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.text import slugify
import os
from django.forms import inlineformset_factory
from .models import CandidateMember

# PDF generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


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
            'image_url': (c.image_url.url if getattr(c, 'image_url') and hasattr(c.image_url, 'url') else ''),
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


def csrf_failure(request, reason=""):
    """Debug helper: show CSRF tokens/cookie when DEBUG=True.

    This view is intended for local debugging only. It reveals the csrftoken cookie,
    any csrfmiddlewaretoken submitted via POST, and X-CSRFToken header values so you
    can diagnose mismatches. It is only enabled when Django DEBUG is True.
    """
    from django.conf import settings
    if not getattr(settings, 'DEBUG', False):
        return HttpResponse('CSRF verification failed.', status=403)

    cookie = request.COOKIES.get('csrftoken')
    form_token = request.POST.get('csrfmiddlewaretoken')
    header_token = request.META.get('HTTP_X_CSRFTOKEN') or request.META.get('HTTP_X_CSRF_TOKEN')
    referer = request.META.get('HTTP_REFERER')
    host = request.META.get('HTTP_HOST')

    html = (
        "<html><body>"
        f"<h2>CSRF verification failed (debug)</h2>"
        f"<p>Reason: {reason}</p>"
        "<ul>"
        f"<li><strong>csrftoken cookie</strong>: {cookie!s}</li>"
        f"<li><strong>csrfmiddlewaretoken (form)</strong>: {form_token!s}</li>"
        f"<li><strong>X-CSRFToken header</strong>: {header_token!s}</li>"
        f"<li><strong>Referer</strong>: {referer!s}</li>"
        f"<li><strong>Host</strong>: {host!s}</li>"
        "</ul>"
        "<p>This page is shown because DEBUG=True. Do not enable in production.</p>"
        "</body></html>"
    )
    return HttpResponse(html, status=403)


@require_POST
def api_vote(request):
    logger = logging.getLogger(__name__)
    if not request.user.is_authenticated:
        logger.warning('api_vote: unauthenticated request')
        return JsonResponse({'error': 'authentication required'}, status=403)

    candidate_id = request.POST.get('candidate_id')
    if not candidate_id:
        logger.warning('api_vote: candidate_id missing in POST data')
        return JsonResponse({'error': 'candidate_id required'}, status=400)

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
        logger.warning('api_vote: user %s not registered as voter', getattr(request.user, 'username', None))
        return JsonResponse({'error': 'user not registered as voter'}, status=400)

    # Check election validity (dates)
    from django.utils import timezone
    now = timezone.now()
    if election and not (election.start_date <= now <= election.end_date):
        logger.info('api_vote: election not active for election %s', getattr(election, 'id', None))
        return JsonResponse({'error': 'election not active'}, status=400)

    # Check if voter already voted in this election
    if Vote.objects.filter(voter=voter, election=election).exists():
        logger.info('api_vote: user %s already voted in election %s', getattr(request.user, 'username', None), getattr(election, 'id', None))
        return JsonResponse({'error': 'user already voted in this election'}, status=400)

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


@require_GET
def api_blockchain_records(request):
    """Return recent on-chain records created by the application.

    This endpoint is used by the frontend `blockchain.html` explorer to show
    recent transactions recorded via OnChainRecord.
    """
    qs = OnChainRecord.objects.select_related('candidate', 'election').order_by('-timestamp')[:200]
    data = []
    for r in qs:
        data.append({
            'txid': r.txid,
            'candidate': str(r.candidate) if r.candidate else None,
            'election': str(r.election) if r.election else None,
            'timestamp': r.timestamp.isoformat(),
            'status': 'verified',
        })
    return JsonResponse({'records': data})


# --- Admin frontend forms (staff-only) -------------------------------------------------
def staff_required(view_func):
    # Use reverse_lazy to avoid resolving the 'login' URL at import time.
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url=reverse_lazy('login'))(view_func)


@staff_required
def create_user_view(request):
    if request.method == 'POST':
        form = FrontendUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data.get('email')
            if email:
                user.email = email
                user.save(update_fields=['email'])
            # optionally create voter profile
            if form.cleaned_data.get('create_voter'):
                control = form.cleaned_data.get('control_number') or f"ctrl_{user.username}"
                try:
                    Voter.objects.create(user=user, control_number=control, is_eligible=True)
                except IntegrityError:
                    messages.error(request, 'El número de control ya existe; el usuario fue creado pero no se creó el perfil de votante.')
            messages.success(request, f'Usuario {user.username} creado.')
            return redirect(reverse('votaciones:create_user'))
    else:
        form = FrontendUserCreationForm()
    return render(request, 'manage/create_user.html', {'form': form})


@staff_required
def create_voter_view(request):
    if request.method == 'POST':
        form = VoterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votante creado/actualizado correctamente.')
            return redirect(reverse('votaciones:create_voter'))
    else:
        form = VoterForm()
    return render(request, 'manage/create_voter.html', {'form': form})


@staff_required
def create_candidate_view(request):
    # Use a ModelForm for CandidateMember so we can set placeholders/widgets
    from .forms import CandidateMemberForm
    MemberFormset = inlineformset_factory(
        Candidate, CandidateMember,
        form=CandidateMemberForm,
        fields=('full_name', 'role', 'order'),
        extra=3,
        can_delete=True,
    )

    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)
        # Validate candidate form first. We'll bind the member formset to the saved
        # candidate instance so the inline formset has a parent to attach to.
        if form.is_valid():
            candidate = form.save(commit=False)
            # handle uploaded image if present
            image = form.cleaned_data.get('image')
            if image:
                # create a safe filename
                base = slugify(candidate.name) or 'candidate'
                ext = os.path.splitext(image.name)[1]
                filename = f'candidates/{base}{ext}'
                # ensure unique filename
                i = 1
                save_name = filename
                while default_storage.exists(save_name):
                    save_name = f'candidates/{base}-{i}{ext}'
                    i += 1
                saved_path = default_storage.save(save_name, image)
                # assign saved path to ImageField
                candidate.image_url = saved_path
            candidate.save()
            # now bind formset to the saved candidate and validate/save members
            formset = MemberFormset(request.POST, instance=candidate)
            if formset.is_valid():
                formset.save()
            else:
                # If members invalid, render page with form and formset errors
                return render(request, 'manage/create_candidate.html', {'form': form, 'formset': formset})
            messages.success(request, 'Planilla (Candidate) creada correctamente.')
            return redirect(reverse('votaciones:create_candidate'))
        else:
            # Candidate form invalid: show an empty formset (members errors can't be validated without a parent instance)
            formset = MemberFormset()
    else:
        form = CandidateForm()
        formset = MemberFormset()

    return render(request, 'manage/create_candidate.html', {'form': form, 'formset': formset})


@staff_required
def generate_election_pdf(request, election_id=None):
    """
    Genera un PDF con el reporte completo del proceso electoral.
    Incluye: información de la elección, candidatos, resultados, estadísticas y registros blockchain.
    """
    from django.utils import timezone
    
    # Obtener la elección
    if election_id:
        election = get_object_or_404(Election, pk=election_id)
    else:
        # Usar la elección activa o la más reciente
        now = timezone.now()
        election = Election.objects.filter(start_date__lte=now, end_date__gte=now).first()
        if not election:
            election = Election.objects.order_by('-end_date').first()
    
    if not election:
        return HttpResponse('No hay elecciones disponibles.', status=404)
    
    # Crear el buffer para el PDF
    buffer = io.BytesIO()
    
    # Configurar el documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d')
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2c5282')
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8
    )
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_RIGHT
    )
    
    # Elementos del documento
    elements = []
    
    # Encabezado con fecha de generación
    now = timezone.now()
    elements.append(Paragraph(f"Generado: {now.strftime('%d/%m/%Y')}", header_style))
    elements.append(Spacer(1, 20))
    
    # Título principal
    elements.append(Paragraph("REPORTE DEL PROCESO ELECTORAL", title_style))
    elements.append(Paragraph(f"<b>{election.name}</b>", ParagraphStyle(
        'ElectionName',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5568')
    )))
    elements.append(Spacer(1, 30))
    
    # === INFORMACIÓN DE LA ELECCIÓN ===
    elements.append(Paragraph("INFORMACIÓN DE LA ELECCIÓN", subtitle_style))
    
    election_info = [
        ['Campo', 'Valor'],
        ['Nombre', election.name],
        ['Fecha de Inicio', election.start_date.strftime('%d/%m/%Y %H:%M')],
        ['Fecha de Fin', election.end_date.strftime('%d/%m/%Y %H:%M')],
        ['Estado', 'Activa' if election.is_active() else ('Finalizada' if election.end_date < now else 'Pendiente')],
        ['Creada por', str(election.created_by) if election.created_by else 'N/A'],
    ]
    
    info_table = Table(election_info, colWidths=[150, 300])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 25))
    
    # === ESTADÍSTICAS DE PARTICIPACIÓN ===
    elements.append(Paragraph("ESTADÍSTICAS DE PARTICIPACIÓN", subtitle_style))
    
    eligible_voters = Voter.objects.filter(is_eligible=True).count()
    total_votes = OnChainRecord.objects.filter(election=election).count() or Vote.objects.filter(election=election).count()
    participation = round((total_votes / eligible_voters) * 100, 2) if eligible_voters > 0 else 0
    voters_who_voted = Voter.objects.filter(has_voted=True).count()
    
    stats_data = [
        ['Métrica', 'Valor'],
        ['Votantes Elegibles', str(eligible_voters)],
        ['Total de Votos Registrados', str(total_votes)],
        ['Votantes que han Votado', str(voters_who_voted)],
        ['Participación', f'{participation}%'],
    ]
    
    stats_table = Table(stats_data, colWidths=[250, 200])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38a169')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff4')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c6f6d5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 25))
    
    # === RESULTADOS POR CANDIDATO ===
    elements.append(Paragraph("RESULTADOS POR CANDIDATO/PLANILLA", subtitle_style))
    
    candidates = Candidate.objects.filter(election=election).order_by('-votes_count')
    
    # Estilo para las celdas con texto largo
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
    )
    
    if candidates.exists():
        # Usar Paragraph para permitir saltos de línea automáticos
        results_data = [[
            Paragraph('<b>#</b>', cell_style),
            Paragraph('<b>Planilla/Candidato</b>', cell_style),
            Paragraph('<b>Nombre</b>', cell_style),
            Paragraph('<b>Votos</b>', cell_style),
            Paragraph('<b>% del Total</b>', cell_style)
        ]]
        
        for idx, candidate in enumerate(candidates, 1):
            # Obtener conteo de votos (preferir blockchain)
            vote_count = OnChainRecord.objects.filter(candidate=candidate).count() or candidate.votes_count
            percentage = round((vote_count / total_votes) * 100, 2) if total_votes > 0 else 0
            
            results_data.append([
                Paragraph(str(idx), cell_style),
                Paragraph(candidate.list_name or 'N/A', cell_style),
                Paragraph(candidate.name, cell_style),
                Paragraph(str(vote_count), cell_style),
                Paragraph(f'{percentage}%', cell_style)
            ])
        
        results_table = Table(results_data, colWidths=[30, 150, 180, 50, 60])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#805ad5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#faf5ff')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e9d8fd')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            # Resaltar el ganador (primera fila de datos)
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d6bcfa')),
        ]))
        elements.append(results_table)
    else:
        elements.append(Paragraph("No hay candidatos registrados para esta elección.", normal_style))
    
    elements.append(Spacer(1, 25))
    
    # === REGISTROS EN BLOCKCHAIN ===
    elements.append(Paragraph("REGISTROS EN BLOCKCHAIN (Últimos 20)", subtitle_style))
    
    onchain_records = OnChainRecord.objects.filter(election=election).order_by('-timestamp')[:20]
    
    # Estilo para celdas de blockchain
    blockchain_cell_style = ParagraphStyle(
        'BlockchainCellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
    )
    
    if onchain_records.exists():
        blockchain_data = [[
            Paragraph('<b>TxID (parcial)</b>', blockchain_cell_style),
            Paragraph('<b>Planilla</b>', blockchain_cell_style),
            Paragraph('<b>Fecha/Hora</b>', blockchain_cell_style)
        ]]
        
        for record in onchain_records:
            # Mostrar solo los primeros 20 caracteres del txid para el PDF
            txid_short = record.txid[:20] + '...' if len(record.txid) > 20 else record.txid
            # Mostrar solo el nombre de la planilla (name), no el eslogan (list_name)
            planilla_name = record.candidate.name if record.candidate else 'N/A'
            blockchain_data.append([
                Paragraph(txid_short, blockchain_cell_style),
                Paragraph(planilla_name, blockchain_cell_style),
                Paragraph(record.timestamp.strftime('%d/%m/%Y %H:%M:%S'), blockchain_cell_style)
            ])
        
        blockchain_table = Table(blockchain_data, colWidths=[150, 170, 130])
        blockchain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#edf2f7')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(blockchain_table)
    else:
        elements.append(Paragraph("No hay registros en blockchain para esta elección.", normal_style))
    
    elements.append(Spacer(1, 30))
    
    # === PIE DE PÁGINA / FIRMA ===
    elements.append(Paragraph("_" * 60, ParagraphStyle('Line', alignment=TA_CENTER)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Este documento fue generado automáticamente por el Sistema de Votación CESA.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.gray)
    ))
    elements.append(Paragraph(
        f"Fecha de generación: {now.strftime('%d de %B de %Y')}",
        ParagraphStyle('FooterDate', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.gray)
    ))
    
    # Construir el PDF
    doc.build(elements)
    
    # Preparar respuesta
    buffer.seek(0)
    filename = f"reporte_electoral_{election.id}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Guardar en historial
    from django.core.files.base import ContentFile
    from .models import PDFReport
    
    # Crear una copia del buffer para guardar
    pdf_content = buffer.getvalue()
    pdf_report = PDFReport(
        election=election,
        filename=filename,
        total_votes=total_votes,
        participation=participation,
        generated_by=request.user if request.user.is_authenticated else None
    )
    pdf_report.pdf_file.save(filename, ContentFile(pdf_content), save=True)
    
    # Mostrar en navegador (inline) en lugar de descargar
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response


@staff_required
def pdf_history_view(request, election_id=None):
    """
    Muestra el historial de reportes PDF generados.
    """
    from django.utils import timezone
    
    elections = Election.objects.all().order_by('-end_date')
    
    if election_id:
        election = get_object_or_404(Election, pk=election_id)
        reports = PDFReport.objects.filter(election=election).order_by('-generated_at')
    else:
        election = None
        reports = PDFReport.objects.all().order_by('-generated_at')
    
    context = {
        'elections': elections,
        'selected_election': election,
        'reports': reports,
    }
    
    return render(request, 'manage/pdf_history.html', context)


@staff_required
def view_pdf_report(request, report_id):
    """
    Visualiza un reporte PDF del historial.
    """
    report = get_object_or_404(PDFReport, pk=report_id)
    
    # Leer el archivo PDF guardado
    pdf_file = report.pdf_file
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{report.filename}"'
    
    return response
