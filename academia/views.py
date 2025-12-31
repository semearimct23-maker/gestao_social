from django.shortcuts import render, redirect, get_object_or_404
import datetime
from django.utils import timezone # Import importante para o fuso horário
from django.contrib.auth import login
from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from unidecode import unidecode
from django.utils.dateparse import parse_date
from django.contrib import messages
# IMPORTAÇÃO DOS MODELOS
from .models import Curso, Presenca, Matricula, Pagamento, Aluno, Professor, PagamentoProfessor,Doacao, Despesa
# IMPORTAÇÃO DOS FORMULÁRIOS
from .forms import (
    UserForm, AlunoForm, PagamentoForm, PagamentoAdminForm, 
    CursoForm, AlunoAdminEditarForm, ProfessorForm, ProfessorEditarForm, 
    RelatorioAlunoForm, HorarioForm, MensagemPadraoForm, NovoAgendamentoForm, MatriculaAvulsaForm,DoacaoForm, DespesaForm, AlunoSecretariaForm
)
from .models import MensagemPadrao # Importando MensagemPadrao que faltava na lista acima

# --- HOME ---
def home(request):
    cursos = Curso.objects.filter(ativo=True)
    matriculas_aluno = []
    ids_cursos_matriculados = []
    
    if request.user.is_authenticated:
        # Se for professor, redireciona para o dashboard dele
        if hasattr(request.user, 'professor'):
             return redirect('dashboard_professor')

        try:
            aluno = request.user.aluno
            matriculas_aluno = Matricula.objects.filter(aluno=aluno, ativo=True)
            ids_cursos_matriculados = [m.curso.id for m in matriculas_aluno]
        except:
            pass 

    context = {
        'lista_de_cursos': cursos,
        'matriculas_aluno': matriculas_aluno,
        'ids_cursos_matriculados': ids_cursos_matriculados
    }
    return render(request, 'academia/home.html', context)

# --- ALUNOS (REGISTRO) ---
def registrar_aluno(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        aluno_form = AlunoForm(request.POST, request.FILES)

        if user_form.is_valid() and aluno_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()

            aluno = aluno_form.save(commit=False)
            aluno.user = user
            aluno.save()

            # Cria matrícula se o curso foi selecionado
            if 'curso' in aluno_form.cleaned_data:
                curso_selecionado = aluno_form.cleaned_data.get('curso')
                if curso_selecionado:
                    Matricula.objects.create(aluno=aluno, curso=curso_selecionado, ativo=True)

            login(request, user)
            return redirect('home')
    else:
        user_form = UserForm()
        aluno_form = AlunoForm()

    return render(request, 'academia/registrar.html', {'user_form': user_form, 'aluno_form': aluno_form})

def verificar_usuario_ajax(request):
    username = request.GET.get('username', None)
    data = {
        'existe': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)

@login_required
def meus_pagamentos(request):
    try:
        aluno = request.user.aluno
    except:
        return redirect('home')

    if request.method == 'POST':
        form = PagamentoForm(request.POST, request.FILES)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.aluno = aluno
            pagamento.save()
            return redirect('meus_pagamentos')
    else:
        form = PagamentoForm()
        form.fields['curso'].queryset = Curso.objects.filter(matricula__aluno=aluno, matricula__ativo=True)

    historico = Pagamento.objects.filter(aluno=aluno).order_by('-data_pagamento')
    return render(request, 'academia/meus_pagamentos.html', {'form': form, 'historico': historico})

@login_required
def registrar_pagamento(request):
    # 1. Verifica se é um ALUNO
    try:
        aluno = request.user.aluno
    except:
        return redirect('home')

    if request.method == 'POST':
        form = PagamentoForm(request.POST, request.FILES)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.aluno = aluno
            pagamento.save()
            return redirect('home')
    else:
        form = PagamentoForm()

    context = {
        'form': form
    }
    return render(request, 'academia/registrar_pagamento.html', context)

@login_required
def inscrever_curso(request, curso_id):
    try:
        aluno = request.user.aluno
    except:
        return redirect('home')
        
    curso = get_object_or_404(Curso, id=curso_id)
    
    # Cria nova matrícula (Permite múltiplas)
    Matricula.objects.create(
        aluno=aluno, 
        curso=curso, 
        ativo=True,
        hora_aula="A definir" # Valor padrão
    )
        
    return redirect('home')

@login_required
def desligar_curso(request, curso_id):
    try:
        aluno = request.user.aluno
    except:
        return redirect('home')
        
    curso = get_object_or_404(Curso, id=curso_id)
    
    matricula = Matricula.objects.filter(aluno=aluno, curso=curso, ativo=True).first()
    
    if matricula:
        matricula.ativo = False
        matricula.data_saida = timezone.now()
        matricula.save()
        
    return redirect('home')

# --- PROFESSOR ---
@login_required
def dashboard_professor(request):
    try:
        professor = request.user.professor
    except:
        return redirect('home')

    data_filtro = request.GET.get('data_filtro', timezone.localdate().strftime('%Y-%m-%d'))
    cursos = Curso.objects.filter(professor=professor)
    
    # CORREÇÃO AQUI: O filtro agora funciona porque 'matricula' existe no model Presenca
    presencas_do_dia = Presenca.objects.filter(
        matricula__curso__in=cursos,
        data_aula=data_filtro
    ) 
    
    # Isso aqui cria um dicionário: ID DA MATRÍCULA -> STATUS (True/False)
    # Como cada matrícula tem um ID único (mesmo que seja o mesmo aluno), 
    # isso resolve o problema de marcar duplicado.
    mapa_presenca = {p.matricula.id: p.presente for p in presencas_do_dia}

    for curso in cursos:
        curso.lista_alunos = curso.matricula_set.filter(ativo=True)
        for matricula in curso.lista_alunos:
            # Verifica o ID da matrícula específica
            if matricula.id in mapa_presenca:
                matricula.status_hoje = mapa_presenca[matricula.id]
            else:
                matricula.status_hoje = None

    context = {'professor': professor, 'cursos': cursos, 'data_filtro': data_filtro}
    return render(request, 'academia/dashboard_professor.html', context)

@login_required
def marcar_presenca(request, matricula_id, status, data_aula):
    try:
        request.user.professor
    except:
        return redirect('home')

    matricula = get_object_or_404(Matricula, id=matricula_id)

    # Segurança: só o professor da turma pode marcar
    if matricula.curso.professor != request.user.professor:
        return redirect('home')

    is_presente = True if status == 1 else False

    # CORREÇÃO AQUI: Usamos 'matricula' em vez de 'aluno' e 'curso'
    Presenca.objects.update_or_create(
        matricula=matricula,  # <-- Mudança principal
        data_aula=data_aula,
        defaults={'presente': is_presente}
    )

    return redirect(f'/dashboard/?data_filtro={data_aula}')

@login_required
def ver_relatorio(request, curso_id):
    try:
        professor = request.user.professor
    except:
        return redirect('home')
        
    curso = Curso.objects.get(id=curso_id)
    hoje = timezone.localdate()
    mes_filtro = int(request.GET.get('mes', hoje.month))
    ano_filtro = int(request.GET.get('ano', hoje.year))

    presencas = Presenca.objects.filter(
        matricula__curso=curso,  # <-- Ajuste aqui: matricula__curso
        data_aula__month=mes_filtro,
        data_aula__year=ano_filtro
    ).order_by('data_aula', 'matricula__aluno__user__username') # <-- Ajuste na ordenação
    
    context = {'curso': curso, 'presencas': presencas, 'mes_atual': mes_filtro, 'ano_atual': ano_filtro}
    return render(request, 'academia/relatorio.html', context)

@login_required
def definir_horario(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    
    autorizado = False
    if request.user.is_staff:
        autorizado = True
    elif hasattr(request.user, 'professor'):
        if matricula.curso.professor == request.user.professor:
            autorizado = True
            
    if not autorizado:
        return redirect('home')

    if request.method == 'POST':
        form = HorarioForm(request.POST, instance=matricula)
        if form.is_valid():
            form.save()
            if request.user.is_staff:
                # Se for Admin, volta para a Ficha do Aluno específica
                return redirect('detalhes_aluno', aluno_id=matricula.aluno.id)
            else:
                # Se for Professor, volta para o Dashboard dele (pois ele não acessa a ficha completa)
                return redirect('dashboard_professor')
                
    else:
        form = HorarioForm(instance=matricula)

    return render(request, 'academia/definir_horario.html', {'form': form, 'matricula': matricula})
@staff_member_required
def gerenciar_chamada_adm(request):
    # 1. Filtros (Pega da URL ou usa padrão)
    hoje = timezone.localdate()
    data_filtro = request.GET.get('data', hoje.strftime('%Y-%m-%d'))
    curso_id = request.GET.get('curso')
    
    # 2. Dados Iniciais
    todos_cursos = Curso.objects.filter(ativo=True)
    matriculas = []
    curso_selecionado = None

    # 3. Se tiver curso selecionado, busca os alunos
    if curso_id:
        curso_selecionado = get_object_or_404(Curso, id=curso_id)
        
        # Busca alunos matriculados nesse curso
        matriculas = Matricula.objects.filter(curso=curso_selecionado, ativo=True).order_by('aluno__user__first_name')
        
        # Busca as presenças já marcadas para essa data e curso
        presencas = Presenca.objects.filter(
            matricula__curso=curso_selecionado,
            data_aula=data_filtro
        )
        
        # Cria um "Mapa" para saber quem veio (ID Matricula -> True/False)
        mapa_presenca = {p.matricula.id: p.presente for p in presencas}
        
        # Cruza os dados: Preenche o objeto matrícula com o status atual
        for matricula in matriculas:
            matricula.status_hoje = mapa_presenca.get(matricula.id, None) # None = Não marcado ainda

    context = {
        'todos_cursos': todos_cursos,
        'curso_selecionado': curso_selecionado,
        'matriculas': matriculas,
        'data_filtro': data_filtro,
    }
    
    return render(request, 'academia/gerenciar_chamada_adm.html', context)

@staff_member_required
def marcar_presenca_adm_action(request, matricula_id, status, data_aula):
    # Lógica idêntica ao professor, mas redireciona para o ADM
    matricula = get_object_or_404(Matricula, id=matricula_id)
    is_presente = True if status == 1 else False

    Presenca.objects.update_or_create(
        matricula=matricula,
        data_aula=data_aula,
        defaults={'presente': is_presente}
    )
    
    # Redireciona mantendo os filtros (Data e Curso)
    return redirect(f'/adm/chamada/?curso={matricula.curso.id}&data={data_aula}')


# --- ADMINISTRAÇÃO ---
# Em academia/views.py

@staff_member_required
def dashboard_adm(request):
    # 1. Definição de Datas
    hoje = timezone.localdate()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))

    # 2. Totais Básicos
    total_alunos_ativos = Matricula.objects.filter(ativo=True).count()
    
    # 3. Financeiro (Receita do Mês Selecionado)
    receita_mensalidades = Pagamento.objects.filter(
        confirmado=True, 
        data_pagamento__month=mes_atual, 
        data_pagamento__year=ano_atual
    ).aggregate(Sum('valor'))['valor__sum'] or 0
    
    receita_doacoes = Doacao.objects.filter(
        data_doacao__month=mes_atual,
        data_doacao__year=ano_atual
    ).aggregate(Sum('valor'))['valor__sum'] or 0

    receita_mes = receita_mensalidades + receita_doacoes

    # 4. Inadimplentes (Pendentes)
    # Filtra alunos ativos que não pagaram o mês selecionado
    # Lógica simplificada para performance
    alunos_com_matricula = Aluno.objects.filter(matricula__ativo=True).distinct()
    pagaram_este_mes = Pagamento.objects.filter(
        mes=str(mes_atual).zfill(2), 
        ano=ano_atual, 
        confirmado=True
    ).values_list('aluno_id', flat=True)
    
    total_inadimplentes = alunos_com_matricula.exclude(id__in=pagaram_este_mes).count()

    # 5. Risco de Evasão (Alunos com 2 ou mais faltas no mês)
    lista_risco = []
    matriculas_ativas = Matricula.objects.filter(ativo=True).select_related('aluno', 'curso')
    
    for mat in matriculas_ativas:
        # Conta faltas usando a nova relação com 'matricula'
        qtd_faltas = Presenca.objects.filter(
            matricula=mat,
            presente=False,
            data_aula__month=mes_atual,
            data_aula__year=ano_atual
        ).count()
        
        if qtd_faltas >= 2:
            telefone_bruto = str(mat.aluno.telefone or "")
            fone_limpo = ''.join(filter(str.isdigit, telefone_bruto))
            
            lista_risco.append({
                'nome_aluno': mat.aluno.user.first_name or mat.aluno.user.username,
                'nome_curso': mat.curso.nome,
                'qtd_faltas': qtd_faltas,
                'nome_responsavel': mat.aluno.nome_responsavel,
                'link_zap': f"55{fone_limpo}" if fone_limpo else None
            })
    
    total_risco = len(lista_risco)

    # 6. Pagamento de Professores (CORRIGIDO com a nova lógica de Presença)
    professores = Professor.objects.all()
    lista_pagamento_prof = []
    
    for prof in professores:
        cursos_prof = Curso.objects.filter(professor=prof)
        
        # AQUI estava o erro antigo: mudamos para matricula__curso__in
        qtd_alunos_presentes = Presenca.objects.filter(
            matricula__curso__in=cursos_prof, 
            presente=True, 
            data_aula__month=mes_atual, 
            data_aula__year=ano_atual
        ).values('matricula__aluno').distinct().count()
        
        if qtd_alunos_presentes > 0:
            lista_pagamento_prof.append({
                'nome': prof.user.username,
                'valor': qtd_alunos_presentes * 35.00
            })

    # 7. Dados para os Gráficos (Iteramos 12 meses para gerar as listas)
    grafico_receita = []
    grafico_novos_alunos = []
    meses_label = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for m in range(1, 13):
        # Gráfico 1: Receita por mês
        val = Pagamento.objects.filter(
            confirmado=True, 
            data_pagamento__month=m, 
            data_pagamento__year=ano_atual
        ).aggregate(Sum('valor'))['valor__sum'] or 0
        grafico_receita.append(float(val))
        
        # Gráfico 2: Novos Alunos (Protegido contra datas nulas)
        # O filtro data_inicio__month=m ignora automaticamente campos NULL, evitando o erro NoneType
        novos = Matricula.objects.filter(
            data_inicio__month=m, 
            data_inicio__year=ano_atual
        ).count()
        grafico_novos_alunos.append(novos)

    # 8. Aulas de Hoje
    dias_semana = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
    dia_codigo = dias_semana[hoje.weekday()]
    
    # Agrupamento manual para exibir bonito na tabela
    aulas_hoje = Matricula.objects.filter(ativo=True, dia_semana=dia_codigo).values('curso__nome', 'hora_aula').distinct()
    
    # Processa para contar alunos por horário
    lista_cursos_hoje = []
    # Dicionário auxiliar para agrupar
    aux_aulas = {} 
    
    mt_hoje = Matricula.objects.filter(ativo=True, dia_semana=dia_codigo)
    for m in mt_hoje:
        chave = (m.curso.nome, m.hora_aula)
        if chave not in aux_aulas:
            aux_aulas[chave] = 0
        aux_aulas[chave] += 1
        
    # Transforma em lista ordenada
    for (nome_curso, hora), qtd in aux_aulas.items():
        lista_cursos_hoje.append({
            'nome': nome_curso,
            'inicio': hora,
            'fim': hora, # Se quiser calcular fim, precisaria de lógica extra, deixei igual inicio
            'total_alunos': qtd
        })
    
    # Ordena por horário
    lista_cursos_hoje.sort(key=lambda x: x['inicio'] or "23:59")

    context = {
        'mes_atual': mes_atual, 'ano_atual': ano_atual,
        'total_ativos': total_alunos_ativos,
        'receita_mes': receita_mes,
        'total_inadimplentes': total_inadimplentes,
        'lista_pagamento_prof': lista_pagamento_prof,
        'lista_cursos_hoje': lista_cursos_hoje,
        # Novos campos para o HTML atualizado
        'total_risco': total_risco,
        'lista_risco': lista_risco,
        'grafico_receita': grafico_receita,
        'grafico_novos_alunos': grafico_novos_alunos,
        'meses_label': meses_label,
    }
    
    return render(request, 'academia/dashboard_adm.html', context)

@staff_member_required
def pagamento_manual(request):
    # Se for salvar (POST)
    if request.method == 'POST':
        form = PagamentoAdminForm(request.POST, request.FILES)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.confirmado = True
            pagamento.save()
                    # --- MENSAGEM DE SUCESSO ---
            nome_aluno = pagamento.aluno.user.first_name
            messages.success(request, f"Pagamento de {nome_aluno} registrado com sucesso!")
            #
            # --- ALTERAÇÃO AQUI ---
            # Redireciona de volta para a lista de alunos
            return redirect('listar_alunos')
            # ----------------------

    # Se for abrir a tela (GET)
    else:
        dados_iniciais = {}
        hoje = timezone.localdate()
        dados_iniciais['data_pagamento'] = hoje
        dados_iniciais['mes'] = str(hoje.month).zfill(2)
        dados_iniciais['ano'] = hoje.year
        dados_iniciais['valor'] = 40.00
        
        aluno_id_url = request.GET.get('aluno')
        
        if aluno_id_url:
            aluno = Aluno.objects.filter(id=aluno_id_url).first()
            if aluno:
                dados_iniciais['aluno'] = aluno
                # dados_iniciais['nome_pagante'] = aluno.user.first_name # (Opcional)

                matriculas_ativas = Matricula.objects.filter(aluno=aluno, ativo=True)
                if matriculas_ativas.count() == 1:
                    dados_iniciais['curso'] = matriculas_ativas.first().curso

        form = PagamentoAdminForm(initial=dados_iniciais)

    return render(request, 'academia/lancamento_pagamento.html', {'form': form})

@staff_member_required
def relatorio_financeiro_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    pagamentos = Pagamento.objects.filter(aluno=aluno).order_by('-ano', '-mes', '-data_pagamento')
    total_pago = pagamentos.filter(confirmado=True).aggregate(Sum('valor'))['valor__sum'] or 0
    return render(request, 'academia/relatorio_financeiro_aluno.html', {'aluno': aluno, 'pagamentos': pagamentos, 'total_pago': total_pago})

@staff_member_required
def financeiro_professores(request):
    hoje = timezone.localdate()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    folha = PagamentoProfessor.objects.filter(mes=mes_atual, ano=ano_atual)
    return render(request, 'academia/financeiro_professores.html', {'mes_atual': mes_atual, 'ano_atual': ano_atual, 'folha': folha})

@staff_member_required
def gerar_folha(request):
    mes = int(request.GET.get('mes'))
    ano = int(request.GET.get('ano'))
    professores = Professor.objects.all()
    
    for prof in professores:
        cursos_prof = Curso.objects.filter(professor=prof)
        qtd_alunos_presentes = Presenca.objects.filter(
            matricula__curso__in=cursos_prof, presente=True, data_aula__month=mes, data_aula__year=ano
        ).values('matricula__aluno').distinct().count()
        
        valor = qtd_alunos_presentes * 35.00
        pgto, created = PagamentoProfessor.objects.get_or_create(
            professor=prof, mes=mes, ano=ano,
            defaults={'valor_total': valor, 'qtd_alunos': qtd_alunos_presentes}
        )
        if not pgto.pago:
            pgto.valor_total = valor
            pgto.qtd_alunos = qtd_alunos_presentes
            pgto.save()
    return redirect(f'/financeiro-professores/?mes={mes}&ano={ano}')

@staff_member_required
def confirmar_pagamento_prof(request, pagamento_id):
    pagamento = get_object_or_404(PagamentoProfessor, id=pagamento_id)
    pagamento.pago = True
    pagamento.data_pagamento_realizado = timezone.now()
    pagamento.save()
    return redirect(f'/financeiro-professores/?mes={pagamento.mes}&ano={pagamento.ano}')

# --- CADASTROS E GESTÃO ---

@staff_member_required
def area_cobranca(request):
    hoje = timezone.localdate()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    
    # Busca alunos ativos
    alunos_ativos = Aluno.objects.filter(
        matricula__ativo=True
    ).exclude(
        matricula__dia_semana__isnull=True
    ).exclude(
        matricula__dia_semana=''
    ).distinct()
    
    lista_inadimplentes = []
    
    for aluno in alunos_ativos:
        # Verifica se pagou
        pagou = Pagamento.objects.filter(aluno=aluno, mes=str(mes_atual).zfill(2), ano=ano_atual, confirmado=True).exists()
        
        if not pagou:
            # 1. Prepara telefone
            telefone_bruto = str(aluno.telefone or "")
            fone_limpo = ''.join(filter(str.isdigit, telefone_bruto))
            link_zap = f"55{fone_limpo}" if fone_limpo else ""

            # 2. Define o Nome de Tratamento ([NOME])
            # Se tiver responsável, usa ele. Se não, usa o próprio aluno.
            nome_tratamento = aluno.nome_responsavel if aluno.nome_responsavel else (aluno.user.first_name or aluno.user.username)
            
            # 3. Define o Nome do Aluno ([ALUNO])
            nome_real_aluno = aluno.user.first_name or aluno.user.username

            # 4. Define o Curso ([CURSO])
            # Pega todos os cursos ativos desse aluno e junta com vírgula (Ex: "Violão, Bateria")
            matriculas = Matricula.objects.filter(aluno=aluno, ativo=True)
            lista_cursos = [m.curso.nome for m in matriculas]
            nome_cursos = ", ".join(lista_cursos)

            lista_inadimplentes.append({
                'id': aluno.id,
                'nome': nome_real_aluno,       # Nome para exibir na tabela
                'nome_tratamento': nome_tratamento, # Para a variável [NOME]
                'nome_aluno_msg': nome_real_aluno,  # Para a variável [ALUNO]
                'nome_cursos': nome_cursos,         # Para a variável [CURSO]
                'telefone': aluno.telefone,
                'fone_link': link_zap,
            })

    mensagens = MensagemPadrao.objects.all()
    context = {
        'lista_inadimplentes': lista_inadimplentes, 
        'mensagens': mensagens, 
        'mes_atual': mes_atual, 
        'ano_atual': ano_atual
    }
    return render(request, 'academia/area_cobranca.html', context)

@staff_member_required
def gerenciar_mensagens(request):
    if request.method == 'POST':
        form = MensagemPadraoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gerenciar_mensagens')
    else:
        form = MensagemPadraoForm()
    mensagens = MensagemPadrao.objects.all()
    return render(request, 'academia/gerenciar_mensagens.html', {'form': form, 'mensagens': mensagens})

@staff_member_required
def editar_mensagem(request, mensagem_id):
    msg = get_object_or_404(MensagemPadrao, id=mensagem_id)
    if request.method == 'POST':
        form = MensagemPadraoForm(request.POST, instance=msg)
        if form.is_valid():
            form.save()
            return redirect('gerenciar_mensagens')
    else:
        form = MensagemPadraoForm(instance=msg)
    return render(request, 'academia/editar_mensagem.html', {'form': form})

@staff_member_required
def deletar_mensagem(request, mensagem_id):
    msg = get_object_or_404(MensagemPadrao, id=mensagem_id)
    msg.delete()
    return redirect('gerenciar_mensagens')

@staff_member_required
def agenda_geral(request):
    data_filtro = request.GET.get('data', timezone.localdate().strftime('%Y-%m-%d'))
    data_obj = datetime.datetime.strptime(data_filtro, '%Y-%m-%d').date()
    dias_semana = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB', 'DOM']
    dia_codigo = dias_semana[data_obj.weekday()]
    
    aulas = Matricula.objects.filter(ativo=True, dia_semana=dia_codigo).order_by('hora_aula', 'curso__nome')
    return render(request, 'academia/agenda_geral.html', {'data_filtro': data_filtro, 'dia_codigo': dia_codigo, 'aulas': aulas, 'total_aulas': aulas.count()})

@staff_member_required
def novo_agendamento(request):
    if request.method == 'POST':
        form = NovoAgendamentoForm(request.POST)
        if form.is_valid():
            matricula_escolhida = form.cleaned_data['matricula']
            matricula_escolhida.dia_semana = form.cleaned_data['dia_semana']
            matricula_escolhida.hora_aula = form.cleaned_data['hora_aula']
            matricula_escolhida.save()
            return redirect('agenda_geral')
    else:
        form = NovoAgendamentoForm()
    return render(request, 'academia/novo_agendamento.html', {'form': form})

# --- CRUDS ADMIN ---
@staff_member_required
def adicionar_curso(request):
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            return redirect('dashboard_adm')
    else:
        form = CursoForm()
    return render(request, 'academia/adicionar_curso.html', {'form': form})

@staff_member_required
def editar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES, instance=curso)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = CursoForm(instance=curso)
    return render(request, 'academia/editar_curso.html', {'form': form, 'curso': curso})

@staff_member_required
def listar_alunos(request):
    termo_pesquisa = request.GET.get('q', '')
    filtro_curso = request.GET.get('curso', '')
    filtro_sexo = request.GET.get('sexo', '')
    filtro_igreja = request.GET.get('igreja', '')
    ordem = request.GET.get('ordem', 'nome')

    alunos = Aluno.objects.all()

    if termo_pesquisa:
        # 1. Remove espaços invisíveis do final e do começo
        termo_limpo = termo_pesquisa.strip()
        
        # 2. SUBSTITUI O "ESPAÇO FANTASMA" (NBSP) POR ESPAÇO COMUM
        # O Excel adora colocar esse caractere \xa0
        termo_limpo = termo_limpo.replace('\xa0', ' ')
        
        # 3. Remove o %
        termo_limpo = termo_limpo.replace('%', '')
        
        # 4. Normaliza (tira acento e põe minúsculo)
        termo_limpo = unidecode(termo_limpo).lower()

        alunos = alunos.filter(busca_normalizada__contains=termo_limpo)
        #alunos = alunos.filter(Q(user__username__icontains=termo_pesquisa) | Q(telefone__icontains=termo_pesquisa) | Q(user__first_name__icontains=termo_pesquisa))

    if filtro_curso:
        if filtro_curso == 'ativos':
            # Se escolheu "Somente Ativos", filtra quem tem matrícula ativa em QUALQUER curso
            alunos = alunos.filter(matricula__ativo=True)
        else:
            # Se escolheu um curso específico (ID numérico)
            alunos = alunos.filter(matricula__curso_id=filtro_curso, matricula__ativo=True)
    if filtro_sexo:
        alunos = alunos.filter(sexo=filtro_sexo)
    if filtro_igreja == 'metodista':
        alunos = alunos.filter(membro_metodista=True)
    elif filtro_igreja == 'outra':
        alunos = alunos.filter(membro_metodista=False)

    if ordem == 'curso':
        alunos = alunos.order_by('matricula__curso__nome')
    else:
        alunos = alunos.order_by('user__username')

    alunos = alunos.distinct()
    total_encontrados = alunos.count()


    todos_cursos = Curso.objects.all()
    

    
# Lógica para evitar o erro do int('ativos')
    valor_filtro_ctx = ''
    if filtro_curso:
        if filtro_curso == 'ativos':
            valor_filtro_ctx = 'ativos'
        else:
            try:
                valor_filtro_ctx = int(filtro_curso)
            except:
                valor_filtro_ctx = ''

    context = {
        'alunos': alunos, 
        'total_encontrados': total_encontrados,
        'todos_cursos': todos_cursos, 
        'termo_pesquisa': termo_pesquisa, 
       # USE A VARIÁVEL QUE CRIAMOS ACIMA EM VEZ DE TENTAR CONVERTER DIRETO:
        'filtro_curso': valor_filtro_ctx, 
        'filtro_sexo': filtro_sexo, 
        'filtro_igreja': filtro_igreja, 
        'ordem_atual': ordem
    }
    
    return render(request, 'academia/listar_alunos.html', context)

@staff_member_required
def editar_aluno_adm(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    if request.method == 'POST':
        form = AlunoAdminEditarForm(request.POST, request.FILES, instance=aluno)
        if form.is_valid():
            form.save()
            return redirect('detalhes_aluno', aluno_id=aluno.id) 
    else:
        form = AlunoAdminEditarForm(instance=aluno)
    
    return render(request, 'academia/editar_aluno.html', {'form': form, 'aluno': aluno})

@staff_member_required
def listar_professores(request):
    professores = Professor.objects.all().order_by('user__username')
    return render(request, 'academia/listar_professores.html', {'professores': professores})

@staff_member_required
def adicionar_professor(request):
    if request.method == 'POST':
        form = ProfessorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_professores')
    else:
        form = ProfessorForm()
    return render(request, 'academia/adicionar_professor.html', {'form': form})

@staff_member_required
def editar_professor(request, professor_id):
    professor = get_object_or_404(Professor, id=professor_id)
    if request.method == 'POST':
        form = ProfessorEditarForm(request.POST, instance=professor)
        if form.is_valid():
            form.save()
            return redirect('listar_professores')
    else:
        form = ProfessorEditarForm(instance=professor)
    return render(request, 'academia/editar_professor.html', {'form': form, 'professor': professor})

@staff_member_required
def adicionar_aluno_adm(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        aluno_form = AlunoSecretariaForm(request.POST, request.FILES)
        if user_form.is_valid() and aluno_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            aluno = aluno_form.save(commit=False)
            aluno.user = user
            aluno.criado_por_admin = True
            aluno.save()
            if 'curso' in aluno_form.cleaned_data:
                curso_selecionado = aluno_form.cleaned_data.get('curso')
                if curso_selecionado:
                    Matricula.objects.create(aluno=aluno, curso=curso_selecionado, ativo=True)
            return redirect('listar_alunos')
    else:
        user_form = UserForm()
        aluno_form = AlunoSecretariaForm()
    return render(request, 'academia/adicionar_aluno_adm.html', {'user_form': user_form, 'aluno_form': aluno_form})

@staff_member_required
def gerar_relatorio_alunos(request):
    form = RelatorioAlunoForm(request.GET)
    alunos = Aluno.objects.all().order_by('user__username')
    if form.is_valid():
        curso = form.cleaned_data.get('curso')
        origem = form.cleaned_data.get('origem')
        if curso:
            alunos = alunos.filter(matricula__curso=curso, matricula__ativo=True)
        if origem == 'secretaria':
            alunos = alunos.filter(criado_por_admin=True)
        elif origem == 'site':
            alunos = alunos.filter(criado_por_admin=False)
        
        context = {'alunos': alunos.distinct(), 'form': form, 'modo_impressao': 'imprimir' in request.GET}
        if 'imprimir' in request.GET:
            return render(request, 'academia/relatorio_imprimir.html', context)
    return render(request, 'academia/relatorio_opcoes.html', {'form': form})

@staff_member_required
def toggle_status_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    user = aluno.user
    user.is_active = not user.is_active
    user.save()
    return redirect('listar_alunos')

@staff_member_required
def resetar_senha_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    user = aluno.user
    user.set_password('123456')
    user.save()
    return redirect('listar_alunos')

@staff_member_required
def desligar_matricula_adm(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    aluno_id = matricula.aluno.id
    
    # Lógica de desligamento
    matricula.ativo = False
    matricula.data_saida = timezone.now() # ou datetime.datetime.now()
    
    # --- CORREÇÃO DO ERRO ---
    # Verifica se a data de início está vazia (problema de migração)
    # Se estiver vazia, preenche com a data de hoje para não dar erro
    if not matricula.data_inicio:
        matricula.data_inicio = timezone.localdate() 
    # ------------------------

    matricula.save()
    
    # Redireciona de volta (sugiro mandar para detalhes, mas mantive o seu original se preferir)
    return redirect('detalhes_aluno', aluno_id=aluno_id)

@staff_member_required
def detalhes_aluno(request, aluno_id):
    # 1. Busca o Aluno
    aluno = get_object_or_404(Aluno, id=aluno_id)
    
    # 2. Busca todas as matrículas (Ativas primeiro)
    matriculas = Matricula.objects.filter(aluno=aluno).order_by('-ativo', '-data_inicio')
    
    # 3. Busca histórico financeiro
    pagamentos = Pagamento.objects.filter(aluno=aluno).order_by('-data_pagamento')
    
    context = {
        'aluno': aluno,
        'matriculas': matriculas,
        'pagamentos': pagamentos,
    }
    return render(request, 'academia/detalhes_aluno.html', context)
# Importe o form no topo: MatriculaAvulsaForm

@staff_member_required
def retomar_matricula_adm(request, matricula_id):
    matricula = get_object_or_404(Matricula, id=matricula_id)
    matricula.ativo = True
    matricula.data_saida = None # Limpa a data de saída
    matricula.save()
    return redirect('detalhes_aluno', aluno_id=matricula.aluno.id)

@staff_member_required
def adicionar_matricula_extra(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    
    if request.method == 'POST':
        form = MatriculaAvulsaForm(request.POST)
        if form.is_valid():
            Matricula.objects.create(
                aluno=aluno,
                curso=form.cleaned_data['curso'],
                ativo=True,
                dia_semana=form.cleaned_data['dia_semana'],
                hora_aula=form.cleaned_data['hora_aula']
            )
            return redirect('detalhes_aluno', aluno_id=aluno.id)
    else:
        form = MatriculaAvulsaForm()
    
    return render(request, 'academia/adicionar_matricula_extra.html', {'form': form, 'aluno': aluno})



@staff_member_required
def registrar_doacao(request):
    if request.method == 'POST':
        form = DoacaoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('dashboard_adm')
    else:
        form = DoacaoForm()
    
    return render(request, 'academia/registrar_doacao.html', {'form': form})

@staff_member_required
def relatorio_financeiro(request):
    hoje = timezone.localdate()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))

    # --- ENTRADAS ---
    entradas_alunos = Pagamento.objects.filter(confirmado=True, data_pagamento__month=mes_atual, data_pagamento__year=ano_atual)
    total_alunos = entradas_alunos.aggregate(Sum('valor'))['valor__sum'] or 0

    entradas_doacoes = Doacao.objects.filter(data_doacao__month=mes_atual, data_doacao__year=ano_atual)
    total_doacoes = entradas_doacoes.aggregate(Sum('valor'))['valor__sum'] or 0
    
    total_receitas = total_alunos + total_doacoes

    # --- SAÍDAS ---
    # 1. Pagamento de Professores (Só o que já foi pago/confirmado)
    saidas_professores = PagamentoProfessor.objects.filter(pago=True, data_pagamento_realizado__month=mes_atual, data_pagamento_realizado__year=ano_atual)
    total_professores = saidas_professores.aggregate(Sum('valor_total'))['valor_total__sum'] or 0

    # 2. Despesas Extras
    saidas_despesas = Despesa.objects.filter(data_despesa__month=mes_atual, data_despesa__year=ano_atual)
    total_despesas = saidas_despesas.aggregate(Sum('valor'))['valor__sum'] or 0

    total_saidas = total_professores + total_despesas

    # --- BALANÇO ---
    saldo_final = total_receitas - total_saidas
    cor_saldo = "text-success" if saldo_final >= 0 else "text-danger"

    # Formulário para lançar despesa rápida nesta tela
    if request.method == 'POST':
        form = DespesaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect(f'/financeiro/relatorio/?mes={mes_atual}&ano={ano_atual}')
    else:
        form = DespesaForm()

    context = {
        'mes_atual': mes_atual, 'ano_atual': ano_atual,
        'entradas_alunos': entradas_alunos, 'total_alunos': total_alunos,
        'entradas_doacoes': entradas_doacoes, 'total_doacoes': total_doacoes,
        'saidas_professores': saidas_professores, 'total_professores': total_professores,
        'saidas_despesas': saidas_despesas, 'total_despesas': total_despesas,
        'total_receitas': total_receitas, 'total_saidas': total_saidas,
        'saldo_final': saldo_final, 'cor_saldo': cor_saldo,
        'form': form
    }
    return render(request, 'academia/relatorio_financeiro.html', context)

def ficha_aluno(request, aluno_id):
    # Busca o aluno pelo ID ou dá erro 404 se não existir
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    
    # Busca as matrículas desse aluno para exibir na tabela
    matriculas = Matricula.objects.filter(aluno=aluno)
    
    # Busca os pagamentos desse aluno (ordenados do mais recente para o antigo)
    pagamentos = Pagamento.objects.filter(aluno=aluno).order_by('-data_pagamento') # ou '-data', verifique seu model

    context = {
        'aluno': aluno,
        'matriculas': matriculas,
        'pagamentos': pagamentos,
    }
    
    # ATENÇÃO: Verifique se o nome do arquivo HTML abaixo é o mesmo que você salvou
    return render(request, 'detalhe_aluno.html', context)
# Adicione esta função
def atualizar_foto_aluno(request, aluno_id):
    if request.method == 'POST':
        aluno = get_object_or_404(Aluno, id=aluno_id)
        
        # Verifica se enviaram uma foto
        if 'foto' in request.FILES:
            aluno.foto = request.FILES['foto']
            aluno.save()
            
    # Redireciona de volta para a ficha do aluno
    return redirect('detalhes_aluno', aluno_id=aluno_id)

@staff_member_required
def editar_pagamento(request, pagamento_id):
    pagamento = get_object_or_404(Pagamento, id=pagamento_id)
    
    # Captura a URL de origem para redirecionar de volta corretamente
    next_url = request.GET.get('next')

    if request.method == 'POST':
        # Usa o mesmo formulário de Admin que já criamos
        form = PagamentoAdminForm(request.POST, request.FILES, instance=pagamento)
        if form.is_valid():
            pagamento_salvo = form.save()
            
            messages.success(request, "Pagamento atualizado com sucesso!")
            
            # Se tiver uma URL de retorno definida, volta para ela
            if next_url:
                return redirect(next_url)
            
            # Padrão: volta para os detalhes do aluno
            return redirect('detalhes_aluno', aluno_id=pagamento_salvo.aluno.id)
    else:
        form = PagamentoAdminForm(instance=pagamento)

    return render(request, 'academia/editar_pagamento.html', {
        'form': form, 
        'pagamento': pagamento,
        'next_url': next_url # Passa para o template manter no formulário
    })