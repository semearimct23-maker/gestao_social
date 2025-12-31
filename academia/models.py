from django.db import models
from django.contrib.auth.models import User
from unidecode import unidecode
import datetime

# =======================================================
# 1. MODELOS BASE (INDEPENDENTES)
# =======================================================

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.user.username 

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20, verbose_name="WhatsApp (apenas números)", default="")
    
    # DADOS PESSOAIS
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], null=True, blank=True)
    
    # --- ENDEREÇO DETALHADO ---
    logradouro = models.CharField(max_length=150, verbose_name="Rua/Av/Logradouro", null=True, blank=True)
    bairro = models.CharField(max_length=100, verbose_name="Bairro", null=True, blank=True)
    cidade = models.CharField(max_length=100, verbose_name="Cidade", default="Tanguá") # Pode mudar o padrão
    
    # DADOS SOCIAIS
    eh_bolsista = models.BooleanField(default=False, verbose_name="É Bolsista? (Isento de Mensalidade)")
    
    # Responsável e Igreja
    nome_responsavel = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome do Responsável")
    contato_responsavel = models.CharField(max_length=20, blank=True, null=True, verbose_name="Zap do Responsável")
    membro_metodista = models.BooleanField(default=False, verbose_name="É membro da Igreja Metodista Central de Tanguá?")
    outra_igreja = models.CharField(max_length=100, blank=True, null=True, verbose_name="Se não, qual igreja?")
    
    foto = models.ImageField(upload_to='fotos_alunos/', blank=True, null=True, verbose_name="Foto do Aluno")
    criado_por_admin = models.BooleanField(default=False, verbose_name="Criado pela Secretaria?")
    data_matricula = models.DateField(default=datetime.date.today, verbose_name="Data de Matrícula")
    busca_normalizada = models.TextField(blank=True, null=True, db_index=True)

    def save(self, *args, **kwargs):
        # 1. Pega os dados que queremos buscar (Nome, User, Telefone)
        nome = self.user.first_name if self.user else ""
        usuario = self.user.username if self.user else ""
        fone = self.telefone if self.telefone else ""
        
        # 2. Junta tudo numa string só
        texto_completo = f"{nome} {usuario} {fone}"
        
        # 3. Limpa os acentos e deixa minúsculo (Ex: "João" vira "joao")
        self.busca_normalizada = unidecode(texto_completo).lower()
        
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.user.username

# =======================================================
# 2. MODELOS INTERMEDIÁRIOS (DEPENDEM DOS DE CIMA)
# =======================================================

class Curso(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    imagem = models.ImageField(upload_to='cursos/', blank=True, null=True, verbose_name="Imagem do Card")
    
    professor = models.ForeignKey(
        Professor, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ativo = models.BooleanField(default=True, verbose_name="Curso Ativo? (Aceita novas matrículas)")
    def __str__(self):
        return self.nome

# =======================================================
# 3. MODELOS FINAIS (DEPENDEM DE ALUNO E CURSO)
# =======================================================

class Matricula(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    data_inicio = models.DateField(default=datetime.date.today, verbose_name="Data da Matrícula")
    data_saida = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    
    # --- NOVOS CAMPOS DE HORÁRIO ---
    DIAS_CHOICES = [
        ('SEG', 'Segunda-feira'),
        ('TER', 'Terça-feira'),
        ('QUA', 'Quarta-feira'),
        ('QUI', 'Quinta-feira'),
        ('SEX', 'Sexta-feira'),
        ('SAB', 'Sábado'),
    ]
    
    HORAS_CHOICES = [
        ('07:00', '07:00'), ('07:30', '07:30'),
        ('08:00', '08:00'), ('08:30', '08:30'),
        ('09:00', '09:00'), ('09:30', '09:30'),
        ('10:00', '10:00'), ('10:30', '10:30'),
        ('11:00', '11:00'), ('11:30', '11:30'),
        ('12:00', '12:00'), ('12:30', '12:30'),
        ('13:00', '13:00'), ('13:30', '13:30'),
        ('14:00', '14:00'), ('14:30', '14:30'),
        ('15:00', '15:00'), ('15:30', '15:30'),
        ('16:00', '16:00'), ('16:30', '16:30'),
        ('17:00', '17:00'), ('17:30', '17:30'),
        ('18:00', '18:00'), ('18:30', '18:30'),
        ('19:00', '19:00'), ('19:30', '19:30'),
        ('20:00', '20:00'), ('20:30', '20:30'),
        ('21:00', '21:00'), ('21:30', '21:30'),
        ('22:00', '22:00'),
    ]

    dia_semana = models.CharField(max_length=3, choices=DIAS_CHOICES, null=True, blank=True, verbose_name="Dia")
    hora_aula = models.CharField(max_length=5, choices=HORAS_CHOICES, null=True, blank=True, verbose_name="Hora")

    def __str__(self):
        status = "ATIVO" if self.ativo else "INATIVO"
        return f"{self.aluno} - {self.curso} ({status})"
    
class Presenca(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE)
    
    data_aula = models.DateField(default=datetime.date.today)
    presente = models.BooleanField(default=False)

    def __str__(self):
        # Ajustamos o __str__ para usar os dados que vêm da matrícula
        return f"{self.matricula.aluno} - {self.data_aula} - {'Presente' if self.presente else 'Falta'}"
    
class Pagamento(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True, blank=True)
    nome_pagante = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome do Pagante (Quem pagou?)")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações") 
    MESES_CHOICES = [
        ('01', 'Janeiro'), ('02', 'Fevereiro'), ('03', 'Março'),
        ('04', 'Abril'), ('05', 'Maio'), ('06', 'Junho'),
        ('07', 'Julho'), ('08', 'Agosto'), ('09', 'Setembro'),
        ('10', 'Outubro'), ('11', 'Novembro'), ('12', 'Dezembro'),
    ]
    ANOS_CHOICES = [
        (2025, '2025'), (2026, '2026'), (2027, '2027'),
    ]
    METODOS_CHOICES = [
        ('PIX', 'Pix'),
        ('CC', 'Cartão de Crédito'),
        ('CD', 'Cartão de Débito'),
        ('DIN', 'Dinheiro'),
    ]

    mes = models.CharField(max_length=2, choices=MESES_CHOICES, default='01', verbose_name="Mês")
    ano = models.IntegerField(choices=ANOS_CHOICES, default=2025, verbose_name="Ano")
    metodo = models.CharField(max_length=3, choices=METODOS_CHOICES, default='PIX', verbose_name="Forma de Pagamento")
    
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    # default=datetime.now deixa pré-preenchido com hoje, mas permite mudar
    data_pagamento = models.DateField(default=datetime.date.today, verbose_name="Data do Pagamento")
    comprovante = models.ImageField(upload_to='comprovantes/', blank=True, null=True)
    confirmado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_mes_display()}/{self.ano} - {self.aluno}"

class PagamentoProfessor(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    mes = models.IntegerField(verbose_name="Mês")
    ano = models.IntegerField(verbose_name="Ano")
    qtd_alunos = models.IntegerField(verbose_name="Qtd. Alunos Computados", default=0)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor a Pagar")
    pago = models.BooleanField(default=False)
    data_pagamento_realizado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "PAGO" if self.pago else "PENDENTE"
        return f"{self.professor} - {self.mes}/{self.ano} - R$ {self.valor_total} ({status})"

# 8. MENSAGENS PADRÃO PARA WHATSAPP
class MensagemPadrao(models.Model):
    titulo = models.CharField(max_length=50, verbose_name="Título (Ex: Cobrança Leve)")
    texto = models.TextField(verbose_name="Texto da Mensagem")
    
    def __str__(self):
        return self.titulo
# 9. CONTROLE DE DOAÇÕES
class Doacao(models.Model):
    nome_doador = models.CharField(max_length=100, verbose_name="Nome do Doador")
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Contato")
    
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor da Doação")
    data_doacao = models.DateField(default=datetime.date.today, verbose_name="Data")
    
    METODOS_CHOICES = [
        ('PIX', 'Pix'), ('DIN', 'Dinheiro'), ('TRA', 'Transferência'),
    ]
    metodo = models.CharField(max_length=3, choices=METODOS_CHOICES, default='PIX')
    
    descricao = models.CharField(max_length=200, blank=True, null=True, verbose_name="Motivo/Obs")
    comprovante = models.ImageField(upload_to='doacoes/', blank=True, null=True)

    def __str__(self):
        return f"Doação de {self.nome_doador} - R$ {self.valor}"
# 10. CONTROLE DE DESPESAS EXTRAS
class Despesa(models.Model):
    descricao = models.CharField(max_length=100, verbose_name="Descrição (Ex: Conta de Luz)")
    categoria = models.CharField(max_length=50, choices=[
        ('FIXA', 'Despesa Fixa'),
        ('VAR', 'Despesa Variável'),
        ('MAN', 'Manutenção/Material'),
    ], default='FIXA')
    
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_despesa = models.DateField(default=datetime.date.today, verbose_name="Data do Pagamento")
    comprovante = models.ImageField(upload_to='despesas/', blank=True, null=True)

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"