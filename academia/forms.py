from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Aluno, Curso, Pagamento, Professor, Matricula, MensagemPadrao,Doacao, Despesa

# =======================================================
# 1. USUÁRIOS E ALUNOS (CADASTRO INICIAL)
# =======================================================

class UserForm(forms.ModelForm):
    # --- CAMPO ARMADILHA (HONEYPOT) ---
    # Label vazio para não aparecer texto, e style display:none para sumir da tela
    validacao_spam = forms.CharField(
        required=False,
        label="", 
        widget=forms.TextInput(attrs={'style': 'display:none', 'autocomplete': 'off', 'tabindex': '-1'})
    )
    # ----------------------------------
    first_name = forms.CharField(label="Nome Completo", required=True)
    password = forms.CharField(widget=forms.PasswordInput(), label="Senha")
    
    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password']
    
    def clean_username(self):
        username = self.cleaned_data['username']
        # Verifica se existe algum User com esse username, EXCETO se for o próprio (no caso de edição)
        if User.objects.filter(username=username).exists():
            raise ValidationError("Este nome de usuário já está em uso. Por favor, escolha outro.")
        return username

class AlunoForm(forms.ModelForm):
    curso = forms.ModelChoiceField(queryset=Curso.objects.filter(ativo=True), required=True, label="Curso de Interesse")
    field_order = [
        'first_name', 'telefone', 
        'data_nascimento', 'sexo', 
        'logradouro', 'bairro', 'cidade', # Novos campos
        'nome_responsavel', 'contato_responsavel',
        'membro_metodista', 'outra_igreja', 'foto'
    ]
    class Meta:
        model = Aluno
        fields = [
            'telefone',
            'sexo',
            'nome_responsavel',
            'contato_responsavel',
            'membro_metodista', 
            'outra_igreja', 
            'logradouro',
            'bairro',
            'cidade',
            'foto','data_nascimento']
        # Widget para ativar a câmera no celular/upload
        widgets = {
            'foto': forms.FileInput(attrs={'accept': 'image/*', 'capture': 'user'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            
                    }



class AlunoSecretariaForm(AlunoForm):
    class Meta(AlunoForm.Meta):
        # Pega todos os campos do site + o campo de bolsista
        fields = [
            'eh_bolsista',  # <--- O CAMPO QUE FALTAVA
            'telefone',
            'sexo',
            'data_nascimento', # Lembra da correção da data? Ela vem junto aqui
            'nome_responsavel',
            'contato_responsavel',
            'membro_metodista',
            'outra_igreja',
            'logradouro',
            'bairro',
            'cidade',
            'foto'
        ]
# =======================================================
# 2. ALUNOS (EDIÇÃO PELO ADMIN)
# =======================================================

class AlunoAdminEditarForm(forms.ModelForm):
    # Campo extra (vem do User)
    first_name = forms.CharField(label="Nome Completo", required=True)

    field_order = [
        'first_name', 'telefone', 'eh_bolsista', # Bolsista em destaque
        'data_nascimento', 'sexo', 
        'logradouro', 'bairro', 'cidade', # Novos campos
        'nome_responsavel', 'contato_responsavel',
        'membro_metodista', 'outra_igreja', 'foto'
    ]

    class Meta:
        model = Aluno
        fields = [
            'data_matricula','telefone', 'data_nascimento', 'sexo', 
            'logradouro', 'bairro', 'cidade', 'eh_bolsista',
            'nome_responsavel', 'contato_responsavel',
            'membro_metodista', 'outra_igreja', 'foto'
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_matricula': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'foto': forms.FileInput(attrs={'accept': 'image/*', 'capture': 'user'}),
            
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name

    def save(self, commit=True):
        aluno = super().save(commit=False)
        user = aluno.user
        user.first_name = self.cleaned_data['first_name']
        if commit:
            user.save()
            aluno.save()
        return aluno

# =======================================================
# 3. PROFESSORES (CADASTRO E EDIÇÃO)
# =======================================================

class ProfessorForm(forms.ModelForm):
    username = forms.CharField(label="Nome de Usuário (Login)")
    first_name = forms.CharField(label="Nome Completo")
    email = forms.EmailField(label="E-mail", required=False)
    password = forms.CharField(widget=forms.PasswordInput(), label="Senha", required=False)

    class Meta:
        model = Professor
        fields = [] 

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name']
        )
        professor = super().save(commit=False)
        professor.user = user
        if commit:
            professor.save()
        return professor

class ProfessorEditarForm(forms.ModelForm):
    first_name = forms.CharField(label="Nome Completo")
    email = forms.EmailField(label="E-mail", required=False)

    class Meta:
        model = Professor
        fields = [] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        professor = super().save(commit=False)
        user = professor.user
        user.first_name = self.cleaned_data['first_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            professor.save()
        return professor

# =======================================================
# 4. FINANCEIRO E CURSOS
# =======================================================

class PagamentoForm(forms.ModelForm):
    # Formulário usado pelo ALUNO
    class Meta:
        model = Pagamento
        fields = ['curso', 'mes', 'ano', 'valor', 'comprovante']

class AlunoModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Aqui definimos o que aparece na lista
        # Ex: "João da Silva (Resp: Maria)"
        responsavel = f" - Resp: {obj.nome_responsavel}" if obj.nome_responsavel else ""
        return f"{obj.user.first_name} {responsavel}"

class PagamentoAdminForm(forms.ModelForm):
    # Substituímos o campo padrão pelo nosso personalizado
    aluno = AlunoModelChoiceField(
        queryset=Aluno.objects.all().order_by('user__first_name'), 
        label="Aluno",
        widget=forms.Select(attrs={'class': 'form-select select2'}) # Dica: Se usar select2, fica pesquisável
    )

    class Meta:
        model = Pagamento
        # Adicione 'nome_pagante' na lista de campos
        fields = ['aluno', 'nome_pagante', 'curso', 'mes', 'ano', 'data_pagamento', 'metodo', 'valor', 'observacao','comprovante']
        
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'},
            format='%Y-%m-%d' ), # <--- OBRIGATÓRIO PARA APARECER O VALOR INICIAL
           
            # 2. CONFIGURAÇÃO DO CAMPO OBSERVACAO
            'observacao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Ex: Pagamento referente a 2 matrículas, ou pago adiantado...'
            }),

            # Placeholder para ajudar a secretaria
            'nome_pagante': forms.TextInput(attrs={'placeholder': 'Ex: Mãe, Pai, ou deixe vazio se for o aluno'}),
        }

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nome', 'professor', 'descricao', 'imagem','ativo']

# Formulário para o Gerador de Relatórios
class RelatorioAlunoForm(forms.Form):
    # --- FILTROS (Quem vai aparecer?) ---
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), required=False, label="Filtrar por Curso")
    origem = forms.ChoiceField(choices=[('', 'Todos'), ('site', 'Pelo Site'), ('secretaria', 'Pela Secretaria')], required=False, label="Origem do Cadastro")
    
    # --- COLUNAS (O que vai aparecer?) ---
    mostrar_telefone = forms.BooleanField(required=False, initial=True, label="Mostrar Telefone")
    mostrar_endereco = forms.BooleanField(required=False, label="Mostrar Endereço")
    mostrar_nascimento = forms.BooleanField(required=False, label="Mostrar Data Nasc.")
    mostrar_responsavel = forms.BooleanField(required=False, label="Mostrar Responsável")
    mostrar_igreja = forms.BooleanField(required=False, label="Mostrar Igreja")
    mostrar_foto = forms.BooleanField(required=False, initial=True, label="Mostrar Foto")

class HorarioForm(forms.ModelForm):
    class Meta:
        model = Matricula
        fields = ['data_inicio','dia_semana', 'hora_aula']

        widgets = {
            # Formatamos para aparecer o calendário bonitinho
            'data_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),}
        
class MensagemPadraoForm(forms.ModelForm):
    class Meta:
        model = MensagemPadrao
        fields = ['titulo', 'texto']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ex: Olá, sua mensalidade venceu.'}),
        }
# Formulário para Agendamento Direto 
class NovoAgendamentoForm(forms.Form):
    
    # O dropdown vai mostrar "Joao - Violão", "Maria - Bateria", etc.
    matricula = forms.ModelChoiceField(
        queryset=Matricula.objects.filter(ativo=True).order_by('aluno__user__username'),
        label="Selecione a Matrícula (Aluno - Curso)",
        widget=forms.Select(attrs={'class': 'form-control select2'}) # Classe extra pra ficar bonito
    )
    
    # Campos de Dia e Hora (pegamos as opções do modelo)
    dia_semana = forms.ChoiceField(
        choices=Matricula.DIAS_CHOICES, 
        label="Dia da Semana"
    )
    hora_aula = forms.ChoiceField(
        choices=Matricula.HORAS_CHOICES, 
        label="Horário"
    )
# Formulário para o Admin adicionar matrícula direto na ficha
class MatriculaAvulsaForm(forms.ModelForm):
    curso = forms.ModelChoiceField(queryset=Curso.objects.filter(ativo=True), label="Curso")
    class Meta:
        model = Matricula
        fields = ['curso', 'dia_semana', 'hora_aula']
class DoacaoForm(forms.ModelForm):
    class Meta:
        model = Doacao
        fields = ['nome_doador', 'telefone', 'valor', 'data_doacao', 'metodo', 'descricao', 'comprovante']
        widgets = {
            'data_doacao': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex: Oferta voluntária para compra de instrumentos'}),
        }
# Importe Despesa no topo!

class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ['descricao', 'categoria', 'valor', 'data_despesa', 'comprovante']
        widgets = {
            'data_despesa': forms.DateInput(attrs={'type': 'date'}),
        }
