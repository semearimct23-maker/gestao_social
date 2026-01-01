from django.db import models

# Create your models here.
from django.db import models

class Noticia(models.Model):
    titulo = models.CharField(max_length=200)
    subtitulo = models.CharField(max_length=300, blank=True)
    conteudo = models.TextField()
    imagem = models.ImageField(upload_to='noticias/')
    data_publicacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

class Evento(models.Model):
    titulo = models.CharField(max_length=200)
    data_evento = models.DateTimeField()
    local = models.CharField(max_length=200)
    descricao = models.TextField()
    imagem = models.ImageField(upload_to='eventos/', blank=True, null=True)

    def __str__(self):
        return self.titulo