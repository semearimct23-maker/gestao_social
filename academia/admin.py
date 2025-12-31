from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import (
    Professor, Curso, Aluno, Presenca, Pagamento, 
    Matricula, MensagemPadrao, Doacao, PagamentoProfessor
)
from .resources import AlunoResource, MatriculaResource

# --- CONFIGURAÇÕES DE IMPORTAÇÃO ---

class AlunoAdminImport(ImportExportModelAdmin):
    resource_class = AlunoResource
    # Mostra a tabela de matrículas dentro do cadastro do aluno
    class MatriculaInline(admin.TabularInline):
        model = Matricula
        extra = 1
    inlines = [MatriculaInline]
    
    list_display = ('user', 'telefone', 'criado_por_admin')
    search_fields = ('user__username', 'user__first_name', 'telefone')

class MatriculaAdminImport(ImportExportModelAdmin):
    resource_class = MatriculaResource
    list_display = ('aluno', 'curso', 'ativo')
    list_filter = ('ativo', 'curso')
    search_fields = ('aluno__user__username', 'curso__nome')

# --- REGISTROS NO PAINEL ---

admin.site.register(Aluno, AlunoAdminImport)      # Usa a versão com importação
admin.site.register(Matricula, MatriculaAdminImport) # Usa a versão com importação

admin.site.register(Professor)
admin.site.register(Curso)
admin.site.register(Presenca)
admin.site.register(Pagamento)
admin.site.register(PagamentoProfessor)
admin.site.register(MensagemPadrao)
admin.site.register(Doacao)