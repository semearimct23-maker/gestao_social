from import_export import resources, fields, widgets
from django.contrib.auth.models import User
from .models import Aluno, Curso, Matricula

class AlunoResource(resources.ModelResource):
    # Campos auxiliares (lidos do CSV)
    username = fields.Field(column_name='username')
    first_name = fields.Field(column_name='first_name')
    password = fields.Field(column_name='password')
    
    # CORREÇÃO 1: Definimos o campo user explicitamente para aceitar um ID
    user = fields.Field(column_name='user', attribute='user', widget=widgets.ForeignKeyWidget(User, 'id'))

    class Meta:
        model = Aluno
        # CORREÇÃO 2: Adicionamos 'user' nesta lista. Sem isso, ele não salva!
        fields = (
            'id', 'username', 'first_name', 'password', 'user', 
            'telefone', 'data_nascimento', 
            'logradouro', 'bairro', 'cidade', 'eh_bolsista', 
            'nome_responsavel', 'contato_responsavel', 'membro_metodista', 'outra_igreja',
            'sexo'
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = False
    
    def before_import_row(self, row, **kwargs):
        # 1. Cria ou recupera o User
        # Garantimos que os dados venham como string para evitar erros
        uname = str(row['username']).strip()
        fname = str(row.get('first_name', '')).strip()
        pwd = str(row.get('password', '123456')).strip()

        user, created = User.objects.get_or_create(
            username=uname,
            defaults={
                'first_name': fname,
                'is_active': True
            }
        )
        
        # 2. Define a senha se for novo
        if created:
            user.set_password(pwd)
            user.save()
            
        # 3. Passa o ID do User para o campo que definimos lá em cima
        row['user'] = user.id
        
        return super().before_import_row(row, **kwargs)

    # (Opcional) Para exportação
    def dehydrate_username(self, aluno):
        return aluno.user.username if aluno.user else ''

    def dehydrate_first_name(self, aluno):
        return aluno.user.first_name if aluno.user else ''


# --- RECURSO DE MATRÍCULA ---
class MatriculaResource(resources.ModelResource):
    aluno_username = fields.Field(column_name='username')
    nome_curso = fields.Field(column_name='curso')

    class Meta:
        model = Matricula
        fields = ('id', 'aluno', 'curso', 'ativo')
        import_id_fields = ('aluno', 'curso')
        skip_unchanged = True
        report_skipped = False

    def before_import_row(self, row, **kwargs):
        username = str(row.get('username', '')).strip()
        
        # Busca Aluno
        try:
            aluno = Aluno.objects.get(user__username=username)
            row['aluno'] = aluno.id
        except Aluno.DoesNotExist:
            pass # Se não achar o aluno, essa linha falha ou é pulada

        # Busca Curso
        nome_curso_csv = str(row.get('curso', '')).strip()
        if nome_curso_csv:
            try:
                curso = Curso.objects.get(nome__iexact=nome_curso_csv)
                row['curso'] = curso.id
            except Curso.DoesNotExist:
                # Cria o curso se não existir (Opcional, mas útil na primeira vez)
                curso = Curso.objects.create(nome=nome_curso_csv)
                row['curso'] = curso.id
        
        row['ativo'] = True