# 🗳️ Sistema de Votación CESA

Sistema de votación electrónica segura basado en blockchain Algorand para el Centro de Estudiantes (CESA). Desarrollado con Django 5.2 y desplegado con verificación de votos en la red Algorand.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-5.2+-green.svg)
![Algorand](https://img.shields.io/badge/Blockchain-Algorand-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Tecnologías](#-tecnologías)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API Endpoints](#-api-endpoints)
- [Contratos Inteligentes](#-contratos-inteligentes)
- [Generación de Reportes PDF](#-generación-de-reportes-pdf)
- [Desarrollo](#-desarrollo)
- [Testing](#-testing)
- [Despliegue](#-despliegue)
- [Seguridad](#-seguridad)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

---

## ✨ Características

### 🔐 Seguridad y Transparencia
- **Blockchain Algorand**: Cada voto se registra inmutablemente en la blockchain
- **Verificación Criptográfica**: Transacciones verificables públicamente
- **Anonimato**: Preservación de la privacidad del votante mientras se mantiene la integridad

### 📊 Gestión Electoral
- **Múltiples Elecciones**: Soporte para diferentes procesos electorales simultáneos
- **Gestión de Candidatos/Planillas**: Creación de candidatos con integrantes y propuestas
- **Control de Votantes**: Sistema de números de control únicos para elegibilidad

### 📈 Visualización y Reportes
- **Dashboard en Tiempo Real**: Estadísticas de participación y resultados actualizados
- **Explorador de Blockchain**: Visualización de transacciones verificadas
- **Reportes PDF**: Generación automática de reportes detallados con historial
- **Gráficos Interactivos**: Visualización de resultados por candidato

### 👥 Roles de Usuario
- **Votantes**: Pueden votar una vez por elección verificando su identidad
- **Administradores**: Gestión completa del sistema (usuarios, candidatos, elecciones)
- **Panel de Admin**: Interfaz administrativa completa de Django

### 🎨 Interfaz de Usuario
- **Diseño Responsive**: Compatible con dispositivos móviles y desktop
- **Bootstrap 5**: Interfaz moderna y accesible
- **Navegación Intuitiva**: Flujo de votación simple y claro

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│   Frontend      │
│   (Bootstrap)   │
└────────┬────────┘
         │
┌────────▼────────┐
│   Django App    │
│   - Views       │
│   - Models      │
│   - Forms       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────────┐
│SQLite│  │ Algorand  │
│  DB  │  │Blockchain │
└──────┘  └───────────┘
```

### Flujo de Votación

1. **Autenticación**: Usuario inicia sesión con credenciales
2. **Verificación**: Sistema verifica elegibilidad y que no haya votado
3. **Selección**: Usuario revisa candidatos y selecciona uno
4. **Confirmación**: Modal de confirmación con detalles del candidato
5. **Registro Local**: Voto se registra en base de datos Django
6. **Blockchain**: Transacción se envía a Algorand para verificación inmutable
7. **OnChainRecord**: Se crea registro blockchain sin datos identificables del votante
8. **Confirmación**: Usuario recibe confirmación con TxID de blockchain

---

## 🛠️ Tecnologías

### Backend
- **Django 5.2.7**: Framework web principal
- **Python 3.10+**: Lenguaje de programación
- **SQLite**: Base de datos (desarrollo)
- **Django Admin**: Panel administrativo

### Blockchain
- **Algorand SDK (py-algorand-sdk)**: Integración con blockchain Algorand
- **Smart Contracts (TEAL)**: Contratos inteligentes en Algorand
- **Algorand TestNet/MainNet**: Red blockchain

### Frontend
- **Bootstrap 5.3.3**: Framework CSS
- **Bootstrap Icons**: Iconografía
- **JavaScript Vanilla**: Interactividad del cliente
- **HTML5/CSS3**: Marcado y estilos

### Reportes
- **ReportLab 4.0+**: Generación de PDFs profesionales
- **Pillow**: Procesamiento de imágenes

### Otros
- **python-dotenv**: Gestión de variables de entorno
- **Git**: Control de versiones

---

## 📦 Requisitos

### Software
- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Git
- Navegador web moderno (Chrome, Firefox, Edge, Safari)

### Opcional (para desarrollo con blockchain local)
- Docker Desktop
- WSL2 (Windows Subsystem for Linux) - Windows
- Algorand Sandbox

---

## 🚀 Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/jessusgarciar/VotacionCESA.git
cd VotacionCESA
```

### 2. Crear Entorno Virtual (Recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Django
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Algorand (TestNet ejemplo)
ALGOD_ADDRESS=https://testnet-algorand.api.purestake.io/ps2
ALGOD_TOKEN=tu-token-de-purestake
ALGORAND_APP_ID=12345678

# Base de datos (opcional, usa SQLite por defecto)
DATABASE_URL=sqlite:///db.sqlite3
```

### 5. Aplicar Migraciones

```bash
cd VotacionCESA
python manage.py migrate
```

### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

Sigue las instrucciones para crear tu cuenta de administrador.

### 7. Cargar Datos Iniciales (Opcional)

```bash
# Importar votantes desde CSV
python manage.py import_voters voters_sample.csv
```

### 8. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

Accede a: **http://127.0.0.1:8000/**

---

## ⚙️ Configuración

### Configuración de Algorand

#### Opción 1: Sandbox Local (Desarrollo)

1. Instalar Algorand Sandbox (requiere Docker y WSL2 en Windows):

```bash
git clone https://github.com/algorand/sandbox.git
cd sandbox
./sandbox up testnet
```

2. Obtener configuración del sandbox:

```bash
./sandbox goal node status
```

3. Configurar variables de entorno:

```env
ALGOD_ADDRESS=http://localhost:4001
ALGOD_TOKEN=token-del-sandbox
```

#### Opción 2: PureStake API (TestNet/MainNet)

1. Crear cuenta en [PureStake](https://www.purestake.com/)
2. Obtener API Key
3. Configurar:

```env
ALGOD_ADDRESS=https://testnet-algorand.api.purestake.io/ps2
ALGOD_TOKEN=tu-api-key-aqui
PURESTAKE_APIKEY=tu-api-key-aqui
```

### Desplegar Contrato Inteligente

```bash
# Verificar entorno
python env_check.py

# Desplegar contrato
python deploy_contract.py

# Verificar contrato desplegado
python verify_contracts.py
```

### Configurar Media Files

Asegúrate de que las carpetas para archivos subidos existan:

```bash
mkdir -p VotacionCESA/media/candidates
mkdir -p VotacionCESA/media/reports
```

---

## 📖 Uso

### Panel de Administración

Accede a **http://127.0.0.1:8000/admin/**

#### Gestionar Elecciones
1. Ir a **Elections** en el admin
2. Crear nueva elección con fechas de inicio y fin
3. Asignar candidatos a la elección

#### Crear Candidatos/Planillas
1. **Manage → Crear Planilla** o vía admin
2. Completar información:
   - Nombre de la planilla
   - Eslogan
   - Imagen (opcional)
   - Manifiesto/Propuestas
3. Agregar integrantes (Presidente, Vicepresidente, etc.)

#### Gestionar Votantes
1. **Manage → Agregar Votante**
2. Vincular con usuario existente o crear nuevo
3. Asignar número de control único
4. Marcar como elegible

#### Importar Votantes Masivamente
Desde el admin:
1. Ir a **Voters**
2. Click en **Import voters from CSV**
3. Subir archivo CSV con formato:

```csv
username,email,control_number,is_eligible
voter1,voter1@example.com,CTRL001,True
voter2,voter2@example.com,CTRL002,True
```

### Interfaz de Votante

#### Votar
1. Iniciar sesión con credenciales
2. Ver lista de candidatos/planillas
3. Click en **"Votar"** o **"Ver Detalles"**
4. Revisar propuestas e integrantes
5. Confirmar voto
6. Recibir confirmación con TxID de blockchain

#### Ver Resultados
- **Pestaña "Resultados"**: Ver conteo en tiempo real
- **Pestaña "Blockchain"**: Explorar transacciones verificadas

### Generación de Reportes PDF

#### Desde Blockchain (Staff)
1. Ir a página de **Blockchain**
2. Click en **"Generar PDF"** (solo visible para administradores)
3. El PDF se abre en el navegador

#### Ver Historial de PDFs
1. Click en **"Historial"** junto a "Generar PDF"
2. Filtrar por elección
3. Ver o descargar reportes anteriores

#### Desde Admin
1. En lista de **Elections**, click en botón **📄 PDF** por elección
2. O en botón **📋 Historial** para ver todos los reportes

---

## 📁 Estructura del Proyecto

```
VotacionCESA/
├── VotacionCESA/                 # Proyecto Django principal
│   ├── manage.py                 # Script de gestión Django
│   ├── db.sqlite3                # Base de datos SQLite
│   ├── VotacionCESA/             # Configuración del proyecto
│   │   ├── settings.py           # Configuración Django
│   │   ├── urls.py               # URLs principales
│   │   ├── wsgi.py               # WSGI para despliegue
│   │   └── templates/            # Templates base
│   │       ├── base.html         # Template base con navbar
│   │       ├── home.html         # Página de votación
│   │       ├── resultados.html   # Página de resultados
│   │       └── blockchain.html   # Explorador blockchain
│   ├── votaciones/               # App principal
│   │   ├── models.py             # Modelos (Candidate, Voter, Vote, etc.)
│   │   ├── views.py              # Vistas y lógica
│   │   ├── urls.py               # URLs de la app
│   │   ├── forms.py              # Formularios
│   │   ├── admin.py              # Configuración admin
│   │   ├── algorand_integration.py  # Integración Algorand
│   │   ├── algorand_reader.py    # Lectura de blockchain
│   │   ├── utils.py              # Utilidades
│   │   ├── migrations/           # Migraciones de BD
│   │   ├── management/           # Comandos personalizados
│   │   │   └── commands/
│   │   │       └── import_voters.py
│   │   └── templates/            # Templates de la app
│   │       ├── admin/            # Templates admin customizados
│   │       ├── manage/           # Templates gestión
│   │       │   ├── create_user.html
│   │       │   ├── create_voter.html
│   │       │   ├── create_candidate.html
│   │       │   └── pdf_history.html
│   │       └── registration/
│   │           └── login.html
│   └── media/                    # Archivos subidos
│       ├── candidates/           # Imágenes de candidatos
│       └── reports/              # PDFs generados
├── approval.teal                 # Smart contract Algorand
├── clear.teal                    # Clear state program
├── deploy_contract.py            # Script de despliegue
├── verify_contracts.py           # Verificación de contratos
├── env_check.py                  # Verificación de entorno
├── check_address.py              # Verificar opt-in
├── requirements.txt              # Dependencias Python
├── .env                          # Variables de entorno (no versionado)
├── .gitignore                    # Archivos ignorados por Git
├── SANDBOX.md                    # Guía Algorand Sandbox
└── README.md                     # Este archivo
```

---

## 🔌 API Endpoints

### Endpoints Públicos

#### `GET /api/candidates/`
Obtiene lista de candidatos con votos.

**Query Parameters:**
- `election_id` (opcional): Filtrar por elección

**Respuesta:**
```json
{
  "candidates": [
    {
      "id": 1,
      "name": "Example Group",
      "list_name": "Eslogan de la Planilla",
      "image_url": "/media/candidates/example.jpg",
      "manifesto": "Propuestas...",
      "votes_count": 42,
      "members": [
        {
          "full_name": "Juan Pérez",
          "role": "Presidente"
        }
      ]
    }
  ]
}
```

#### `POST /api/vote/`
Registra un voto (requiere autenticación).

**Body (form-data):**
- `candidate_id`: ID del candidato
- `election_id` (opcional): ID de la elección

**Respuesta:**
```json
{
  "status": "ok",
  "vote_id": 123,
  "candidate_votes": 43,
  "total_votes": 150,
  "txid": "ALGORAND_TRANSACTION_ID"
}
```

#### `GET /api/elections/`
Lista todas las elecciones.

**Respuesta:**
```json
{
  "elections": [
    {
      "id": 1,
      "name": "Elecciones CESA 2025",
      "start_date": "2025-11-01T00:00:00",
      "end_date": "2025-11-30T23:59:59",
      "is_active": true
    }
  ]
}
```

#### `GET /api/stats/`
Estadísticas de participación.

**Query Parameters:**
- `election_id` (opcional): Estadísticas de elección específica

**Respuesta:**
```json
{
  "total_votes": 150,
  "eligible_voters": 200,
  "participation": 75.0
}
```

#### `GET /api/blockchain-records/`
Registros recientes en blockchain.

**Respuesta:**
```json
{
  "records": [
    {
      "txid": "ALGORAND_TX_ID",
      "candidate": "Example Group",
      "election": "Elecciones CESA 2025",
      "timestamp": "2025-11-19T14:30:00",
      "status": "verified"
    }
  ]
}
```

### Endpoints de Gestión (Staff)

#### `GET /votaciones/report/pdf/`
Genera PDF de elección activa.

#### `GET /votaciones/report/pdf/<election_id>/`
Genera PDF de elección específica.

#### `GET /votaciones/report/history/`
Historial de todos los reportes PDF.

#### `GET /votaciones/report/history/<election_id>/`
Historial filtrado por elección.

#### `GET /votaciones/report/view/<report_id>/`
Visualiza un PDF del historial.

---

## 📜 Contratos Inteligentes

### Archivo: `approval.teal`

Smart contract en TEAL (Transaction Execution Approval Language) para Algorand.

#### Funcionalidades

**1. Creación (Creation)**
- Inicializa la aplicación en blockchain
- Configura parámetros globales

**2. Registro (OptIn)**
- Permite a votantes registrarse en el contrato
- Requiere período de registro (RegBegin - RegEnd)
- Almacena estado local: `Voted = 0`

**3. Votación**
- Verifica que votante haya hecho OptIn
- Comprueba que no haya votado antes (`Voted == 0`)
- Valida período de votación (VoteBegin - VoteEnd)
- Registra voto: `Voted = 1`
- No almacena por quién votó (privacidad)

**4. Actualización (Update)**
- Solo creator puede actualizar
- Permite modificar fechas de elección

**5. Eliminación (Delete)**
- Solo creator puede eliminar
- Destruye la aplicación

#### Estados Globales
- `RegBegin`: Timestamp inicio registro
- `RegEnd`: Timestamp fin registro
- `VoteBegin`: Timestamp inicio votación
- `VoteEnd`: Timestamp fin votación

#### Estados Locales (por votante)
- `Voted`: Booleano (0 = no votado, 1 = votado)

### Despliegue del Contrato

```bash
# Compilar y desplegar
python deploy_contract.py

# Verificar
python verify_contracts.py

# Asignar candidatos al contrato
python assign_candidates.py
```

---

## 📄 Generación de Reportes PDF

### Características de los Reportes

Los PDFs generados incluyen:

#### 1. Información de la Elección
- Nombre de la elección
- Fechas de inicio y fin
- Estado (activa/finalizada/pendiente)
- Usuario creador

#### 2. Estadísticas de Participación
- Votantes elegibles
- Total de votos registrados
- Votantes que han votado
- Porcentaje de participación

#### 3. Resultados por Candidato
- Ranking de candidatos por votos
- Nombre de planilla
- Conteo de votos
- Porcentaje del total
- Ganador resaltado

#### 4. Registros en Blockchain
- Últimas 20 transacciones
- TxID (parcial)
- Candidato asociado
- Fecha y hora

#### 5. Metadatos
- Fecha de generación
- Usuario que generó
- Firma automática del sistema

### Modelo PDFReport

```python
class PDFReport(models.Model):
    election = models.ForeignKey(Election)
    filename = models.CharField(max_length=255)
    pdf_file = models.FileField(upload_to='reports/')
    total_votes = models.PositiveIntegerField()
    participation = models.FloatField()
    generated_by = models.ForeignKey(User)
    generated_at = models.DateTimeField(auto_now_add=True)
```

### Visualización de PDFs

Los PDFs se abren **inline** en el navegador (no se descargan automáticamente), permitiendo:
- Visualización inmediata
- Impresión desde el navegador
- Descarga opcional

---

## 🧪 Testing

### Preparar Entorno de Testing

```bash
# Crear base de datos de test
python manage.py test --keepdb
```

### Ejecutar Tests

```bash
# Todos los tests
python manage.py test votaciones

# Tests específicos
python manage.py test votaciones.tests.test_api
python manage.py test votaciones.tests.test_import_voters
```

### Tests Disponibles

**`test_api.py`**
- Test de endpoints API
- Validación de autenticación
- Test de votación

**`test_import_voters.py`**
- Importación masiva de votantes
- Validación de CSV
- Manejo de duplicados

### Testing Manual con cURL

```bash
# Obtener candidatos
curl http://127.0.0.1:8000/api/candidates/

# Obtener estadísticas
curl http://127.0.0.1:8000/api/stats/?election_id=1

# Votar (requiere sesión)
curl -X POST http://127.0.0.1:8000/api/vote/ \
  -H "X-CSRFToken: TOKEN" \
  -d "candidate_id=1"
```

---

## 🚢 Despliegue

### Preparación para Producción

1. **Configurar settings.py**:

```python
DEBUG = False
ALLOWED_HOSTS = ['tudominio.com', 'www.tudominio.com']
SECRET_KEY = os.environ.get('SECRET_KEY')

# Base de datos PostgreSQL (recomendado)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': '5432',
    }
}
```

2. **Configurar archivos estáticos**:

```bash
python manage.py collectstatic
```

3. **Usar servidor WSGI**:
   - Gunicorn
   - uWSGI
   - Daphne

### Ejemplo con Gunicorn

```bash
# Instalar
pip install gunicorn

# Ejecutar
gunicorn VotacionCESA.wsgi:application --bind 0.0.0.0:8000
```

### Opciones de Hosting

#### Plataformas PaaS
- **Heroku**: Deploy con Git
- **Railway**: Deploy automático desde GitHub
- **Render**: Servicios web gratuitos
- **PythonAnywhere**: Hosting Python especializado

#### Servidores VPS
- **DigitalOcean**: Droplets con Ubuntu
- **Linode**: Servidores Linux
- **AWS EC2**: Instancias escalables
- **Google Cloud**: Compute Engine

### Docker (Opcional)

Crear `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "VotacionCESA.wsgi:application", "--bind", "0.0.0.0:8000"]
```

Ejecutar:

```bash
docker build -t votacion-cesa .
docker run -p 8000:8000 votacion-cesa
```

---

## 🔒 Seguridad

### Mejores Prácticas Implementadas

✅ **CSRF Protection**: Django CSRF tokens en todos los formularios
✅ **SQL Injection**: Django ORM previene inyecciones SQL
✅ **XSS Protection**: Escape automático de templates
✅ **Password Hashing**: Django usa PBKDF2 por defecto
✅ **Blockchain Verification**: Votos inmutables en Algorand
✅ **Anonymity**: OnChainRecord no vincula votante con voto

### Recomendaciones Adicionales

🔐 **HTTPS Obligatorio**: Usar SSL/TLS en producción
🔐 **Secret Key**: Generar clave secreta única y segura
🔐 **Rate Limiting**: Implementar para prevenir abuso
🔐 **Backup Regular**: Respaldar base de datos periódicamente
🔐 **Monitoreo**: Logs de actividad sospechosa
🔐 **Auditoría**: Revisar registros blockchain regularmente

### Generación de Secret Key Segura

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

---

## 🤝 Contribución

### Cómo Contribuir

1. **Fork** el repositorio
2. Crea una **rama** para tu feature:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```
3. **Commit** tus cambios:
   ```bash
   git commit -m "Agregar nueva funcionalidad"
   ```
4. **Push** a la rama:
   ```bash
   git push origin feature/nueva-funcionalidad
   ```
5. Abre un **Pull Request**

### Guía de Estilo

- **Python**: Seguir PEP 8
- **JavaScript**: Usar camelCase
- **HTML**: Indentación de 2 espacios
- **CSS**: BEM naming convention (cuando sea posible)
- **Commits**: Mensajes descriptivos en español

### Reportar Bugs

Usar GitHub Issues con la siguiente información:
- Descripción del bug
- Pasos para reproducir
- Comportamiento esperado vs actual
- Screenshots (si aplica)
- Entorno (OS, Python version, etc.)

---

## 📝 Changelog

### Version 1.0.0 (2025-12-02)
- ✨ Sistema de votación completo
- ✨ Integración con blockchain Algorand
- ✨ Panel administrativo Django
- ✨ Generación de reportes PDF
- ✨ Historial de reportes PDF
- ✨ Explorador de blockchain
- ✨ API REST para votación
- ✨ Sistema de autenticación
- ✨ Gestión de elecciones múltiples
- ✨ Importación masiva de votantes
- ✨ Interfaz responsive con Bootstrap 5

---

## 📞 Soporte

### Contacto

- **GitHub**: [jessusgarciar/VotacionCESA](https://github.com/jessusgarciar/VotacionCESA)
- **Issues**: [Reportar problema](https://github.com/jessusgarciar/VotacionCESA/issues)
- **Email**: soporte@cesa.edu

### Recursos

- [Documentación Django](https://docs.djangoproject.com/)
- [Algorand Developer Portal](https://developer.algorand.org/)
- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)
- [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)

---

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

```
MIT License

Copyright (c) 2025 CESA - Centro de Estudiantes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Agradecimientos

- **Algorand Foundation**: Por la infraestructura blockchain
- **Django Software Foundation**: Por el excelente framework
- **Bootstrap Team**: Por el framework CSS
- **Comunidad Open Source**: Por las librerías y herramientas

---

## 🗺️ Roadmap

### Próximas Funcionalidades

- [ ] **Notificaciones por Email**: Confirmaciones de voto
- [ ] **Multi-idioma**: Soporte i18n (español/inglés)
- [ ] **Autenticación 2FA**: Seguridad adicional
- [ ] **Dashboard Analytics**: Gráficos avanzados
- [ ] **Mobile App**: Aplicación nativa iOS/Android
- [ ] **API GraphQL**: Alternativa a REST
- [ ] **Exportación de Datos**: CSV, Excel, JSON
- [ ] **Integración con LDAP**: Autenticación universitaria
- [ ] **Votación Delegada**: Proxy voting
- [ ] **Preguntas Personalizadas**: Encuestas adicionales

### Mejoras Técnicas

- [ ] Redis Cache para performance
- [ ] Celery para tareas asíncronas
- [ ] Websockets para updates en tiempo real
- [ ] Tests de integración completos
- [ ] CI/CD con GitHub Actions
- [ ] Documentación API con Swagger
- [ ] Monitoreo con Prometheus/Grafana
- [ ] Containerización con Docker Compose

---

<div align="center">

**⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub ⭐**

Hecho con ❤️ por el equipo de CESA

</div>
