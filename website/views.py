from django.shortcuts import render
from .models import Noticia, Evento
from academia.models import Curso # Importamos os cursos do outro app!

def index(request):
    # Pega as 3 últimas notícias e eventos
    noticias = Noticia.objects.order_by('-data_publicacao')[:3]
    eventos = Evento.objects.order_by('data_evento')[:3]
    
    # Pega todos os cursos para mostrar na vitrine
    cursos = Curso.objects.all()

    return render(request, 'website/index.html', {
        'noticias': noticias,
        'eventos': eventos,
        'cursos': cursos,
    })

def doacao(request):
    return render(request, 'website/doacao.html')