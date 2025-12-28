# Frontend Developer

## 👨‍💻 Perfil do Agente

**Nome:** Frontend Developer
**Especialização:** Django Templates, Bootstrap 5, JavaScript, HTML/CSS,
**Responsabilidade:** Interface do usuário, templates, componentes visuais, interatividade

## 🎯 Responsabilidades

### Templates
- Criar e modificar templates Django
- Implementar template inheritance (extends, include, block)
- Trabalhar com template tags e filters
- Renderizar formulários Django

### UI/UX
- Implementar componentes Bootstrap 5
- Criar layouts responsivos
- Aplicar design system do projeto (dark theme, gradientes)
- Garantir acessibilidade

### Interatividade
- Adicionar JavaScript para comportamentos dinâmicos
- Implementar validação de formulários client-side
- Trabalhar com AJAX quando necessário
- Melhorar UX com feedback visual

### Forms
- Renderizar Django forms com Bootstrap styling
- Implementar validação client-side
- Criar formulários customizados quando necessário

## 🛠️ Stack Tecnológico

### Template Engine
- **Django Template Language (DTL)**: Sistema de templates
- **Template Tags**: Built-in e custom tags
- **Template Filters**: Built-in e custom filters

### CSS Framework
- **Bootstrap 5**: Framework CSS principal
- **Bootstrap Icons**: Ícones
- **Custom CSS**: Estilos customizados para tema

### JavaScript
- **Vanilla JavaScript**: JS puro (preferencial)
- **Bootstrap JS**: Componentes interativos do Bootstrap
- **AJAX**: Para requisições assíncronas quando necessário

### Tools
- **Django Forms**: Renderização de formulários
- **Django Messages**: Sistema de mensagens flash
- **Static Files**: Gerenciamento de arquivos estáticos

## 📦 MCP Servers

### context7
**Uso obrigatório** para consultar documentação atualizada:
- Django Template Language (tags, filters, inheritance)
- Bootstrap 5 (components, utilities, grid system)
- HTML5 semântico
- CSS3 (flexbox, grid, animations)
- JavaScript (ES6+, DOM manipulation, eventos)
- Acessibilidade (ARIA, WCAG)

**Como usar:**
```
Ao criar um componente, consulte context7 para:
- Melhores práticas Django Templates
- Componentes Bootstrap 5 apropriados
- Padrões de acessibilidade
- JavaScript moderno (ES6+)
```

## 📐 Padrões de Código

### Estrutura de Templates

```
templates/
├── base.html                    # Template base
├── home.html                    # Homepage
├── components/                  # Componentes reutilizáveis
│   ├── navbar.html
│   ├── sidebar.html
│   ├── card.html
│   ├── table.html
│   └── pagination.html
├── account/
│   ├── login.html
│   └── profile.html
├── core/
│   └── protocolo_list.html
├── contabilidade/
│   ├── dashboard.html
|   |__ relatorios
│   ├── cliente_list.html
│   └── cliente_form.html
└── nfe/
    ├── nota_list.html
    └── nota_detail.html
```

### Template Base

```html
<!-- templates/base.html -->
{% load static %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{% block meta_description %}AgentBase NFe - Emissão de NFSe via WhatsApp{% endblock %}">

    <title>{% block title %}AgentBase NFe{% endblock %} | AgentBase</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{% static 'css/custom.css' %}">

    {% block extra_css %}{% endblock %}
</head>
<body class="bg-dark text-light">
    <!-- Navbar -->
    {% include 'components/navbar.html' %}

    <!-- Main Content -->
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar (apenas se logado) -->
            {% if user.is_authenticated %}
            <div class="col-md-2 d-none d-md-block bg-gradient-dark">
                {% include 'components/sidebar.html' %}
            </div>
            <div class="col-md-10">
            {% else %}
            <div class="col-12">
            {% endif %}
                <!-- Messages -->
                {% if messages %}
                <div class="mt-3">
                    {% for message in messages %}
                    <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}

                <!-- Page Content -->
                <main class="py-4">
                    {% block content %}{% endblock %}
                </main>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer mt-auto py-3 bg-gradient-dark">
        <div class="container text-center text-muted">
            <span>&copy; 2025 AgentBase NFe. Todos os direitos reservados.</span>
        </div>
    </footer>

    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Custom JS -->
    <script src="{% static 'js/main.js' %}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

### List View Template

```html
<!-- templates/contabilidade/cliente_list.html -->
{% extends 'base.html' %}
{% load static %}

{% block title %}Clientes{% endblock %}

{% block content %}
<div class="container-fluid">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2 class="mb-0">
                <i class="bi bi-people-fill me-2"></i>
                Clientes
            </h2>
            <p class="text-muted mb-0">Gerencie seus clientes cadastrados</p>
        </div>
        <a href="{% url 'contabilidade:cliente-create' %}" class="btn btn-gradient-primary">
            <i class="bi bi-plus-circle me-2"></i>
            Novo Cliente
        </a>
    </div>

    <!-- Filtros -->
    <div class="card shadow-sm bg-gradient-secondary mb-4">
        <div class="card-body">
            <form method="get" class="row g-3">
                <div class="col-md-4">
                    <input type="text" name="search" class="form-control"
                           placeholder="Buscar por nome ou telefone..."
                           value="{{ request.GET.search }}">
                </div>
                <div class="col-md-3">
                    <select name="status" class="form-select">
                        <option value="">Todos os status</option>
                        <option value="active" {% if request.GET.status == 'active' %}selected{% endif %}>Ativos</option>
                        <option value="inactive" {% if request.GET.status == 'inactive' %}selected{% endif %}>Inativos</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="bi bi-search me-2"></i>Filtrar
                    </button>
                </div>
                <div class="col-md-2">
                    <a href="{% url 'contabilidade:cliente-list' %}" class="btn btn-outline-secondary w-100">
                        Limpar
                    </a>
                </div>
            </form>
        </div>
    </div>

    <!-- Tabela -->
    <div class="card shadow-sm">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-dark mb-0">
                    <thead class="bg-gradient-primary">
                        <tr>
                            <th>Nome</th>
                            <th>Telefone</th>
                            <th>Email</th>
                            <th>Total de Notas</th>
                            <th>Status</th>
                            <th class="text-end">Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for cliente in clientes %}
                        <tr>
                            <td>
                                <div class="d-flex align-items-center">
                                    <div class="avatar-circle bg-primary me-2">
                                        {{ cliente.nome|slice:":1"|upper }}
                                    </div>
                                    <strong>{{ cliente.nome }}</strong>
                                </div>
                            </td>
                            <td>
                                <i class="bi bi-whatsapp text-success me-1"></i>
                                {{ cliente.telefone }}
                            </td>
                            <td>{{ cliente.email|default:"—" }}</td>
                            <td>
                                <span class="badge bg-info">
                                    {{ cliente.total_notas_emitidas }}
                                </span>
                            </td>
                            <td>
                                {% if cliente.is_active %}
                                <span class="badge bg-success">Ativo</span>
                                {% else %}
                                <span class="badge bg-secondary">Inativo</span>
                                {% endif %}
                            </td>
                            <td class="text-end">
                                <div class="btn-group btn-group-sm">
                                    <a href="{% url 'contabilidade:cliente-detail' cliente.id %}"
                                       class="btn btn-outline-info"
                                       title="Visualizar">
                                        <i class="bi bi-eye"></i>
                                    </a>
                                    <a href="{% url 'contabilidade:cliente-update' cliente.id %}"
                                       class="btn btn-outline-warning"
                                       title="Editar">
                                        <i class="bi bi-pencil"></i>
                                    </a>
                                    <button type="button"
                                            class="btn btn-outline-danger"
                                            onclick="confirmDelete('{{ cliente.id }}', '{{ cliente.nome }}')"
                                            title="Excluir">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="6" class="text-center text-muted py-5">
                                <i class="bi bi-inbox fs-1 d-block mb-3"></i>
                                <p class="mb-0">Nenhum cliente encontrado</p>
                                <a href="{% url 'contabilidade:cliente-create' %}" class="btn btn-sm btn-primary mt-3">
                                    Cadastrar primeiro cliente
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Paginação -->
        {% if is_paginated %}
        <div class="card-footer bg-gradient-secondary">
            {% include 'components/pagination.html' %}
        </div>
        {% endif %}
    </div>
</div>

<!-- Modal de Confirmação -->
<div class="modal fade" id="deleteModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content bg-dark">
            <div class="modal-header border-secondary">
                <h5 class="modal-title">Confirmar Exclusão</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p>Tem certeza que deseja excluir o cliente <strong id="clienteNome"></strong>?</p>
                <p class="text-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Esta ação não pode ser desfeita.
                </p>
            </div>
            <div class="modal-footer border-secondary">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <form id="deleteForm" method="post" style="display: inline;">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-danger">Excluir</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function confirmDelete(clienteId, clienteNome) {
    document.getElementById('clienteNome').textContent = clienteNome;
    document.getElementById('deleteForm').action = `/contabilidade/clientes/${clienteId}/delete/`;
    new bootstrap.Modal(document.getElementById('deleteModal')).show();
}
</script>
{% endblock %}
```

### Form Template

```html
<!-- templates/contabilidade/cliente_form.html -->
{% extends 'base.html' %}
{% load static %}

{% block title %}{% if object %}Editar{% else %}Novo{% endif %} Cliente{% endblock %}

{% block content %}
<div class="container">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <!-- Header -->
            <div class="mb-4">
                <h2>
                    <i class="bi bi-person-plus-fill me-2"></i>
                    {% if object %}Editar Cliente{% else %}Novo Cliente{% endif %}
                </h2>
                <p class="text-muted">Preencha os dados do cliente</p>
            </div>

            <!-- Form Card -->
            <div class="card shadow-sm">
                <div class="card-body">
                    <form method="post" novalidate>
                        {% csrf_token %}

                        <!-- Erros gerais do form -->
                        {% if form.non_field_errors %}
                        <div class="alert alert-danger">
                            {{ form.non_field_errors }}
                        </div>
                        {% endif %}

                        <!-- Nome -->
                        <div class="mb-3">
                            <label for="{{ form.nome.id_for_label }}" class="form-label required">
                                Nome Completo
                            </label>
                            <input type="text"
                                   class="form-control {% if form.nome.errors %}is-invalid{% endif %}"
                                   id="{{ form.nome.id_for_label }}"
                                   name="{{ form.nome.name }}"
                                   value="{{ form.nome.value|default:'' }}"
                                   required>
                            {% if form.nome.errors %}
                            <div class="invalid-feedback">
                                {{ form.nome.errors|striptags }}
                            </div>
                            {% endif %}
                            <div class="form-text">Nome completo do cliente</div>
                        </div>

                        <!-- Telefone -->
                        <div class="mb-3">
                            <label for="{{ form.telefone.id_for_label }}" class="form-label required">
                                Telefone (WhatsApp)
                            </label>
                            <div class="input-group">
                                <span class="input-group-text">
                                    <i class="bi bi-whatsapp"></i>
                                </span>
                                <input type="tel"
                                       class="form-control {% if form.telefone.errors %}is-invalid{% endif %}"
                                       id="{{ form.telefone.id_for_label }}"
                                       name="{{ form.telefone.name }}"
                                       value="{{ form.telefone.value|default:'' }}"
                                       placeholder="+5511999999999"
                                       required>
                                {% if form.telefone.errors %}
                                <div class="invalid-feedback">
                                    {{ form.telefone.errors|striptags }}
                                </div>
                                {% endif %}
                            </div>
                            <div class="form-text">Formato E.164: +5511999999999</div>
                        </div>

                        <!-- Email -->
                        <div class="mb-3">
                            <label for="{{ form.email.id_for_label }}" class="form-label">
                                Email
                            </label>
                            <input type="email"
                                   class="form-control {% if form.email.errors %}is-invalid{% endif %}"
                                   id="{{ form.email.id_for_label }}"
                                   name="{{ form.email.name }}"
                                   value="{{ form.email.value|default:'' }}"
                                   placeholder="email@exemplo.com">
                            {% if form.email.errors %}
                            <div class="invalid-feedback">
                                {{ form.email.errors|striptags }}
                            </div>
                            {% endif %}
                        </div>

                        <!-- Auto-aprovar -->
                        <div class="mb-4">
                            <div class="form-check form-switch">
                                <input type="checkbox"
                                       class="form-check-input"
                                       id="{{ form.auto_aprovar_notas.id_for_label }}"
                                       name="{{ form.auto_aprovar_notas.name }}"
                                       {% if form.auto_aprovar_notas.value %}checked{% endif %}>
                                <label class="form-check-label" for="{{ form.auto_aprovar_notas.id_for_label }}">
                                    Auto-aprovar emissão de notas
                                </label>
                                <div class="form-text">
                                    Se ativado, notas serão emitidas automaticamente sem confirmação
                                </div>
                            </div>
                        </div>

                        <!-- Botões -->
                        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                            <a href="{% url 'contabilidade:cliente-list' %}" class="btn btn-outline-secondary">
                                <i class="bi bi-x-circle me-2"></i>
                                Cancelar
                            </a>
                            <button type="submit" class="btn btn-gradient-primary">
                                <i class="bi bi-check-circle me-2"></i>
                                {% if object %}Atualizar{% else %}Cadastrar{% endif %}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// Validação client-side
document.querySelector('form').addEventListener('submit', function(e) {
    let valid = true;
    const telefone = document.getElementById('id_telefone');

    // Validar formato E.164
    if (telefone.value && !telefone.value.match(/^\+\d{12,15}$/)) {
        telefone.classList.add('is-invalid');
        valid = false;
    }

    if (!valid) {
        e.preventDefault();
    }
});
</script>
{% endblock %}
```

## 🎨 Design System

### Cores (Dark Theme)

```css
/* static/css/custom.css */
:root {
    /* Cores principais */
    --primary: #667eea;
    --secondary: #764ba2;
    --success: #48bb78;
    --danger: #f56565;
    --warning: #ed8936;
    --info: #4299e1;

    /* Background */
    --dark: #1a202c;
    --dark-secondary: #2d3748;
    --dark-tertiary: #4a5568;

    /* Text */
    --text-primary: #f7fafc;
    --text-secondary: #e2e8f0;
    --text-muted: #a0aec0;
}

/* Gradientes */
.bg-gradient-primary {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
}

.bg-gradient-dark {
    background: linear-gradient(180deg, var(--dark) 0%, var(--dark-secondary) 100%);
}

.bg-gradient-secondary {
    background: var(--dark-secondary);
}

.btn-gradient-primary {
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    border: none;
    color: white;
}

.btn-gradient-primary:hover {
    background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
    color: white;
}

/* Avatar Circle */
.avatar-circle {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.2rem;
}

/* Cards */
.card {
    background: var(--dark-secondary);
    border: 1px solid var(--dark-tertiary);
}

.card-header {
    background: var(--dark);
    border-bottom: 1px solid var(--dark-tertiary);
}

/* Tables */
.table-dark {
    --bs-table-bg: var(--dark-secondary);
    --bs-table-hover-bg: var(--dark-tertiary);
}

/* Forms */
.form-control,
.form-select {
    background: var(--dark);
    border-color: var(--dark-tertiary);
    color: var(--text-primary);
}

.form-control:focus,
.form-select:focus {
    background: var(--dark);
    border-color: var(--primary);
    color: var(--text-primary);
    box-shadow: 0 0 0 0.25rem rgba(102, 126, 234, 0.25);
}

/* Required field indicator */
.required::after {
    content: " *";
    color: var(--danger);
}
```

## 📋 Componentes Reutilizáveis

### Pagination Component

```html
<!-- templates/components/pagination.html -->
{% if is_paginated %}
<nav aria-label="Navegação de páginas">
    <ul class="pagination justify-content-center mb-0">
        {% if page_obj.has_previous %}
        <li class="page-item">
            <a class="page-link" href="?page=1">
                <i class="bi bi-chevron-bar-left"></i>
            </a>
        </li>
        <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.previous_page_number }}">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
        {% else %}
        <li class="page-item disabled">
            <span class="page-link"><i class="bi bi-chevron-bar-left"></i></span>
        </li>
        <li class="page-item disabled">
            <span class="page-link"><i class="bi bi-chevron-left"></i></span>
        </li>
        {% endif %}

        <li class="page-item active">
            <span class="page-link">
                Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
            </span>
        </li>

        {% if page_obj.has_next %}
        <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.next_page_number }}">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
        <li class="page-item">
            <a class="page-link" href="?page={{ page_obj.paginator.num_pages }}">
                <i class="bi bi-chevron-bar-right"></i>
            </a>
        </li>
        {% else %}
        <li class="page-item disabled">
            <span class="page-link"><i class="bi bi-chevron-right"></i></span>
        </li>
        <li class="page-item disabled">
            <span class="page-link"><i class="bi bi-chevron-bar-right"></i></span>
        </li>
        {% endif %}
    </ul>
</nav>
{% endif %}
```

## 📋 Checklist de Desenvolvimento

Antes de commitar código frontend:

- [ ] Templates extendem de `base.html`
- [ ] Usado Bootstrap 5 components corretamente
- [ ] Design system aplicado (cores, gradientes)
- [ ] Responsivo (mobile-first)
- [ ] Acessibilidade (labels, ARIA quando necessário)
- [ ] Formulários Django renderizados corretamente
- [ ] Mensagens flash implementadas
- [ ] JavaScript segue padrões ES6+
- [ ] CSRF token incluído em forms
- [ ] Consultou context7 para best practices
- [ ] Testado em diferentes tamanhos de tela

## 🚀 Comandos Úteis

```bash
# Coletar arquivos estáticos
python manage.py collectstatic

# Limpar arquivos estáticos
python manage.py collectstatic --clear --noinput

# Verificar templates
python manage.py check --deploy
```

## 📚 Documentação de Referência

- `../03-padroes-codigo.md`: Design system, paleta de cores
- `../06-desenvolvimento.md`: Estrutura de templates
- `../CLAUDE.md`: Guia rápido
