# Dashboard Multipage - Ministerio de Minas y Energía

**Sistema Integral de Análisis Energético para el Sector Eléctrico Colombiano**

## 📋 Descripción

Dashboard interactivo desarrollado en Python/Dash para el análisis integral y visualización avanzada de métricas del sector energético colombiano. Utiliza datos oficiales de XM (Operador del Sistema Eléctrico) y proporciona herramientas especializadas para el monitoreo, análisis y toma de decisiones en el sector energético nacional.

## ✨ Características Principales

- 🎯 **Dashboard Multipage**: Navegación intuitiva entre 8 módulos especializados
- 📊 **Visualizaciones Interactivas**: Más de 50 tipos de gráficos dinámicos con Plotly
- 🗺️ **Análisis Geoespacial**: Mapas interactivos con cálculos de proximidad automáticos
- 📈 **190+ Métricas XM**: Acceso completo a datos oficiales en tiempo real
- 💧 **Análisis Hidrológico**: Monitoreo integral de recursos hídricos y embalses
- 🎨 **Interfaz Moderna**: Diseño responsive con sidebar desplegable estilo VSCode
- ⚡ **Tiempo Real**: Indicadores de carga y datos sincronizados automáticamente
- 🔍 **Filtros Avanzados**: Sistema de consultas por región, río, fechas y métricas
- 📋 **KPI Cards Inteligentes**: Tarjetas métricas centradas con datos de participación porcentual
- 🔄 **Filtros Sincronizados**: Sistema completo de filtros dinámicos en tiempo real

## 🆕 Últimas Mejoras (Septiembre 2025)

### 💧 Mejoras en Análisis Hidrológico
- ✅ **KPI Cards Optimizadas**: Implementación de tarjetas "Aportes % por Sistema" centradas y responsivas
- ✅ **Filtros Dinámicos**: Sistema completo de filtros por región, río y fechas que se sincronizan en todas las vistas
- ✅ **Simplificación de UI**: Eliminación de tarjetas redundantes para mejor claridad visual
- ✅ **Debugging Mejorado**: Sistema de logs detallado para diagnóstico de datos de la API XM
- ✅ **Manejo de Errores**: Mensajes informativos cuando ríos no tienen datos disponibles
- ✅ **Validación de Datos**: Verificación automática de columnas y estructura de datos de PorcApor

### 🔧 Mejoras Técnicas
- ✅ **API Integration**: Integración mejorada con la API oficial de XM para datos de PorcApor
- ✅ **Error Handling**: Manejo robusto de errores de conectividad y datos faltantes
- ✅ **Performance**: Optimización de consultas y carga de datos hidrológicos
- ✅ **UX/UI**: Diseño centrado y consistente en todas las vistas de gráficos de línea

## 🚀 Funcionalidades Detalladas

### 🏠 Página Principal (Inicio)
- **Dashboard de Control**: Panel central con estadísticas del sistema
- **Navegación Intuitiva**: Acceso rápido a todos los módulos especializados
- **Estadísticas en Vivo**: Contador de módulos activos y métricas disponibles
- **Información del Sistema**: Estado actual y última sincronización con XM

### 📍 Análisis de Coordenadas
- **Mapas Interactivos**: Visualización geoespacial de granjas solares y comunidades energéticas
- **Cálculo de Proximidad**: Algoritmo automático de distancias euclidianas
- **Filtros Geográficos**: Selección por departamento, municipio y tipo de proyecto
- **Reportes de Viabilidad**: Identificación automática de postulaciones factibles
- **Exportación de Datos**: Descarga de reportes de proximidad en múltiples formatos
- **Estadísticas Detalladas**: Análisis de distancias promedio, mínimas y máximas

### 📈 Métricas del Sistema Eléctrico
- **190+ Métricas XM**: Acceso completo al catálogo oficial de métricas
- **Consultas Dinámicas**: Filtros por métrica, entidad, rango de fechas
- **Visualizaciones Múltiples**: Gráficos de líneas, barras, torta y dispersión
- **Datos en Tiempo Real**: Sincronización automática con la API de XM
- **Análisis Comparativo**: Comparación entre múltiples métricas y entidades
- **Indicadores de Carga**: Spinner visual durante consultas de datos

### 💧 Análisis Hidrológico Integral
- **Monitoreo de Caudales**: Seguimiento en tiempo real de ríos y afluentes con datos de XM
- **Gestión de Embalses**: Niveles, capacidades útiles y porcentajes de llenado por región
- **Análisis de Aportes**: Caudales de entrada y participación porcentual por sistema
- **Filtros Especializados**: Por región hidrológica, río específico y rangos de fecha
- **Visualizaciones Hídricas**: Gráficos especializados con líneas temporales interactivas
- **Tablas Dinámicas**: Información detallada de embalses con formateo condicional
- **KPI Cards Inteligentes**: Tarjetas métricas con "Aportes % por Sistema" centradas y responsivas
- **Datos Filtrados**: Sistema completo de filtros que se sincroniza entre todas las vistas
- **Vista Nacional**: Panorámica completa con desglose por regiones hidrológicas
- **Vista Regional**: Análisis específico con datos agregados por región
- **Vista Individual**: Seguimiento detallado de ríos específicos con métricas de participación
- **Predicciones Hídricas**: Análisis de disponibilidad futura de recursos hídricos

### 🌱 Dashboards Especializados por Fuente

#### ☀️ Generación Solar
- **Radiación Solar**: Monitoreo en tiempo real por regiones
- **Eficiencia de Plantas**: Análisis de rendimiento de instalaciones fotovoltaicas
- **Potencial Solar**: Mapas de irradiación y viabilidad por zonas
- **Producción Regional**: Seguimiento de generación por departamentos

#### � Generación Eólica  
- **Velocidades de Viento**: Monitoreo meteorológico especializado
- **Rendimiento de Turbinas**: Análisis de eficiencia de aerogeneradores
- **Patrones Estacionales**: Análisis de variabilidad temporal del recurso eólico
- **Potencial Eólico**: Mapas de zonificación y viabilidad

#### 🌾 Generación por Biomasa
- **Disponibilidad de Biomasa**: Seguimiento de residuos agrícolas y forestales
- **Plantas de Cogeneración**: Monitoreo de eficiencia y producción
- **Gestión Sostenible**: Análisis de impacto ambiental y sostenibilidad

#### 🌊 Generación Hidráulica
- **Centrales Hidroeléctricas**: Monitoreo operativo de todas las plantas
- **Optimización de Turbinado**: Análisis de eficiencia hidráulica
- **Gestión de Embalses**: Coordinación de recursos hídricos

#### 📊 Análisis de Demanda
- **Patrones de Consumo**: Análisis temporal y geográfico de la demanda
- **Proyecciones**: Modelos predictivos de demanda futura
- **Picos y Valles**: Identificación de patrones críticos
- **Segmentación**: Análisis por sectores industriales y residenciales

## 🛠️ Tecnologías y Arquitectura

### Backend y Core
- **Python 3.10+**: Lenguaje principal de desarrollo
- **Dash 2.x**: Framework web reactivo para aplicaciones analíticas
- **Plotly**: Librería de visualización interactiva
- **Pandas**: Manipulación y análisis de datos
- **NumPy**: Computación científica y operaciones matriciales

### Integración de Datos
- **pydataxm**: Cliente oficial para la API de XM
- **Requests**: Manejo de peticiones HTTP y APIs REST  
- **Geopy**: Cálculos geoespaciales y geocodificación
- **Folium**: Generación de mapas interactivos

### Frontend y UI
- **Dash Bootstrap Components**: Componentes UI modernos
- **CSS3 + Bootstrap 5**: Estilos responsive y adaptables
- **Font Awesome**: Iconografía profesional
- **JavaScript**: Interactividad avanzada del lado cliente

### Persistencia y Datos
- **CSV Files**: Almacenamiento local de datos base
- **API XM**: Conexión en tiempo real con datos oficiales
- **Cache Inteligente**: Optimización de consultas repetitivas

## 📦 Instalación y Configuración

### Prerrequisitos
```bash
# Python 3.10 o superior
python --version

# Git para clonación del repositorio
git --version
```

### Instalación Paso a Paso

1. **Clonar el Repositorio**:
```bash
git clone https://github.com/MelissaCardona2003/Dashboard_Multipage_MME.git
cd Dashboard_Multipage_MME
```

2. **Crear Entorno Virtual** (Recomendado):
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

3. **Instalar Dependencias**:
```bash
pip install -r requirements.txt
```

4. **Verificar Instalación**:
```bash
python -c "import dash, plotly, pandas; print('✅ Dependencias instaladas correctamente')"
```

5. **Ejecutar la Aplicación**:
```bash
python app.py
```

6. **Acceder al Dashboard**:
   - Abrir navegador en: `http://127.0.0.1:8053/`
   - La aplicación estará disponible con todas las funcionalidades

### Configuración Avanzada

#### Variables de Entorno (Opcional)
```bash
# Crear archivo .env en la raíz del proyecto
DASH_DEBUG=True
DASH_PORT=8053
XM_API_TIMEOUT=30
```

#### Configuración de Proxy (Si aplica)
```python
# En config.py, ajustar configuraciones de red si es necesario
PROXY_SETTINGS = {
    'http': 'http://proxy.empresa.com:8080',
    'https': 'https://proxy.empresa.com:8080'
}
```

## 📁 Estructura Detallada del Proyecto

```
Dashboard_Multipage_MME/
├── 📄 app.py                              # Aplicación principal y configuración del servidor
├── 📄 requirements.txt                    # Dependencias de Python
├── 📄 README.md                          # Documentación del proyecto
│
├── 📁 assets/                            # Recursos estáticos del frontend
│   ├── 🎨 styles.css                    # Estilos CSS personalizados y temas
│   └── 📜 sidebar.js                    # JavaScript para funcionalidad del sidebar
│
└── 📁 pages/                            # Módulos y páginas del dashboard
    ├── 🏠 index.py                      # Página principal e información general
    ├── ⚙️ components.py                 # Componentes reutilizables (header, sidebar, navbar)
    ├── 🔧 config.py                     # Configuración global (colores, constantes, APIs)
    ├── 📊 data_loader.py                # Cargador universal de datos y cache
    │
    ├── 📍 coordenadas.py                # Análisis geoespacial y proximidad
    ├── 📈 metricas.py                   # Dashboard de métricas XM
    ├── 💧 hidrologia.py                 # Análisis hidrológico integral
    │
    ├── 📄 Base granjas_actualizada.csv   # Base de datos de granjas solares
    ├── 📄 Base comunidades energéticas.csv # Base de datos de comunidades energéticas
    ├── 📄 estadisticas_distancias.csv   # Estadísticas precalculadas de proximidad
    ├── 📄 resumen_detallado_proximidades.csv # Reportes detallados de viabilidad
    │
    └── 📁 __pycache__/                  # Cache de Python (generado automáticamente)
        ├── components.cpython-310.pyc
        ├── config.cpython-310.pyc
        ├── coordenadas.cpython-310.pyc
        ├── data_loader.cpython-310.pyc
        ├── hidrologia.cpython-310.pyc
        ├── index.cpython-310.pyc
        └── metricas.cpython-310.pyc
```

### Descripción de Archivos Principales

#### 🏗️ Archivos de Configuración
- **`app.py`**: Punto de entrada principal, configuración del servidor Dash, registro de páginas y callbacks globales
- **`config.py`**: Configuración centralizada de colores, APIs, constantes y parámetros del sistema
- **`requirements.txt`**: Lista de dependencias de Python con versiones específicas

#### 🧩 Componentes Core
- **`components.py`**: Componentes reutilizables como header universal, sidebar, navbar y elementos comunes
- **`data_loader.py`**: Sistema centralizado de carga de datos con cache inteligente y conexión a APIs

#### 📊 Páginas Funcionales
- **`index.py`**: Dashboard principal con información general y navegación a módulos especializados
- **`coordenadas.py`**: Análisis geoespacial con mapas interactivos y cálculos de proximidad
- **`metricas.py`**: Interfaz para consulta y visualización de las 190+ métricas de XM
- **`hidrologia.py`**: Dashboard especializado en recursos hídricos, embalses y análisis hidrológico

#### 💾 Bases de Datos
- **CSV Files**: Almacenamiento local de datos base para granjas solares, comunidades energéticas y estadísticas precalculadas

## 🔧 Configuración Avanzada

### Personalización de Temas
```python
# En config.py - Personalizar colores del dashboard
COLORS = {
    'primary': '#your_primary_color',
    'secondary': '#your_secondary_color',
    'success': '#your_success_color',
    # ... más configuraciones
}
```

### Configuración de APIs
```python
# En config.py - Configurar conexiones externas
XM_API_CONFIG = {
    'base_url': 'https://api.xm.com.co',
    'timeout': 30,
    'retry_attempts': 3
}
```

### Optimización de Rendimiento
```python
# En data_loader.py - Configurar cache
CACHE_CONFIG = {
    'enable_cache': True,
    'cache_timeout': 3600,  # 1 hora
    'max_cache_size': 100   # MB
}
```

## 📊 Fuentes de Datos y APIs

### Datos Oficiales XM
- **API Principal**: Acceso directo a la API oficial de XM (Operador del Mercado)
- **Métricas Disponibles**: 190+ indicadores del sistema eléctrico nacional
- **Frecuencia de Actualización**: Datos en tiempo real y históricos
- **Cobertura**: Todo el Sistema Interconectado Nacional (SIN)

### Categorías de Métricas XM
- **Generación**: Producción por fuente energética (hidráulica, térmica, solar, eólica)
- **Demanda**: Consumo nacional, regional y sectorial
- **Comercialización**: Transacciones en bolsa y contratos bilaterales
- **Transmisión**: Flujos de energía en el STN (Sistema de Transmisión Nacional)
- **Calidad**: Indicadores de confiabilidad y calidad del servicio
- **Precios**: Precio de bolsa, costos de confiabilidad y reconciliación

### Datos Hidrológicos
- **Aportes Hídricos**: Caudales de ríos y afluentes principales
- **Embalses**: Niveles, volúmenes útiles y capacidades de almacenamiento
- **Predicciones**: Modelos de disponibilidad hídrica
- **Series Históricas**: Datos históricos para análisis de tendencias

### Datos Geoespaciales
- **Coordenadas Geográficas**: Ubicación precisa de granjas solares y comunidades energéticas
- **Cálculos de Proximidad**: Distancias euclidianas automáticas
- **Mapas Base**: Integración con OpenStreetMap y servicios cartográficos

## 🚦 Guía de Uso

### Navegación General
1. **Inicio**: Use el sidebar desplegable (botón ☰) para navegar entre módulos
2. **Búsqueda Rápida**: Los módulos están organizados por categorías en la página principal
3. **Filtros**: Cada página incluye filtros específicos para refinar consultas
4. **Indicadores de Carga**: Los spinners indican cuándo se están cargando datos

### Análisis de Coordenadas
1. **Seleccionar Filtros**: Elija departamento, municipio o tipo de proyecto
2. **Visualizar Mapa**: Los marcadores muestran ubicaciones de granjas y comunidades
3. **Analizar Proximidad**: La tabla muestra distancias automáticamente calculadas
4. **Exportar Resultados**: Descargue reportes en formato CSV o Excel

### Consulta de Métricas XM
1. **Seleccionar Métrica**: Elija entre las 190+ métricas disponibles
2. **Filtrar por Entidad**: Seleccione plantas, regiones o agentes específicos
3. **Definir Período**: Configure el rango de fechas para la consulta
4. **Visualizar Datos**: Los gráficos se actualizan automáticamente
5. **Interpretar Resultados**: Use las herramientas de zoom y filtro de Plotly

### Análisis Hidrológico
1. **Filtros Regionales**: Seleccione región hidrológica o río específico
2. **Período de Análisis**: Configure fechas para análisis temporal
3. **Consultar Datos**: Use el botón "Consultar" y espere el indicador de carga
4. **Interpretar Visualizaciones**: Analice gráficos de caudales y niveles de embalses
5. **Tablas Detalladas**: Revise información específica de cada embalse

## 🛡️ Seguridad y Buenas Prácticas

### Seguridad de Datos
- **Conexiones HTTPS**: Todas las comunicaciones con APIs externas son seguras
- **No Almacenamiento Sensible**: No se almacenan credenciales en el código
- **Validación de Entrada**: Todos los inputs del usuario son validados
- **Límites de Consulta**: Protección contra consultas excesivas a APIs

### Buenas Prácticas de Uso
- **Consultas Eficientes**: Use filtros específicos para evitar consultas masivas
- **Períodos Razonables**: Limite rangos de fechas para mejorar rendimiento
- **Cache Inteligente**: El sistema cache consultas frecuentes automáticamente
- **Monitoreo de Rendimiento**: Observe los indicadores de carga para optimizar uso

## 🔧 Mantenimiento y Troubleshooting

### Problemas Comunes

#### Error de Conexión a XM
```bash
# Verificar conectividad
python -c "
from pydataxm.pydataxm import ReadDB
api = ReadDB()
print('✅ Conexión exitosa' if api.get_collections() is not None else '❌ Error de conexión')
"
```

#### Rendimiento Lento
- **Causa**: Consultas de grandes períodos de tiempo
- **Solución**: Reducir rangos de fechas o usar filtros más específicos
- **Monitoreo**: Observar indicadores de carga y tiempo de respuesta

#### Errores de Memoria
- **Causa**: Visualización de datasets muy grandes
- **Solución**: Implementar paginación o muestreo de datos
- **Prevención**: Usar límites en consultas automáticamente

### Logs y Debugging
```bash
# Habilitar modo debug
export DASH_DEBUG=True
python app.py

# Verificar logs en consola para diagnóstico
```

### Actualizaciones
```bash
# Actualizar dependencias
pip install --upgrade -r requirements.txt

# Verificar compatibilidad
python -c "import dash, plotly; print(f'Dash: {dash.__version__}, Plotly: {plotly.__version__}')"
```

## 🤝 Contribución y Desarrollo

### Guía para Contribuidores

#### Preparación del Entorno de Desarrollo
```bash
# Clonar y configurar entorno
git clone https://github.com/MelissaCardona2003/Dashboard_Multipage_MME.git
cd Dashboard_Multipage_MME
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

#### Estándares de Código
- **PEP 8**: Seguir convenciones de estilo de Python
- **Documentación**: Documentar funciones y clases complejas
- **Type Hints**: Usar anotaciones de tipo cuando sea apropiado
- **Testing**: Incluir pruebas para nuevas funcionalidades

#### Estructura de Commits
```bash
# Formato de commits
git commit -m "tipo(scope): descripción breve

Descripción detallada del cambio (opcional)

Resolves #issue-number"

# Ejemplos:
git commit -m "feat(hidrologia): agregar análisis de embalses"
git commit -m "fix(metricas): corregir filtro de fechas"
git commit -m "docs(readme): actualizar guía de instalación"
```

#### Proceso de Contribución
1. **Fork del Repositorio**: Crear fork personal del proyecto
2. **Crear Rama**: `git checkout -b feature/nueva-funcionalidad`
3. **Desarrollar**: Implementar cambios siguiendo estándares
4. **Testing**: Verificar que todo funciona correctamente
5. **Commit**: Hacer commits descriptivos y atómicos
6. **Push**: `git push origin feature/nueva-funcionalidad`
7. **Pull Request**: Crear PR con descripción detallada

#### Áreas de Contribución
- 🆕 **Nuevas Funcionalidades**: Módulos adicionales de análisis
- 🐛 **Corrección de Bugs**: Identificación y solución de errores
- 📊 **Visualizaciones**: Nuevos tipos de gráficos y dashboards
- 🎨 **UI/UX**: Mejoras en diseño e interfaz de usuario
- 📚 **Documentación**: Mejoras en documentación y guías
- ⚡ **Optimización**: Mejoras de rendimiento y eficiencia

### Roadmap de Desarrollo

#### 🎯 Próximas Funcionalidades (Q1 2025)
- [ ] **Dashboard de Pronósticos**: Predicciones de demanda y generación
- [ ] **Análisis de Mercado**: Módulo de precios y transacciones
- [ ] **Alertas Inteligentes**: Sistema de notificaciones automáticas
- [ ] **API REST**: Endpoint para integración con sistemas externos
- [ ] **Exportación Avanzada**: Reportes en PDF y PowerPoint

#### 🔮 Funcionalidades Futuras (Q2-Q3 2025)
- [ ] **Machine Learning**: Modelos predictivos avanzados
- [ ] **Análisis de Confiabilidad**: Métricas de calidad del servicio
- [ ] **Dashboard Móvil**: Versión optimizada para dispositivos móviles
- [ ] **Integración IoT**: Conexión con sensores y dispositivos en tiempo real
- [ ] **Análisis de Sostenibilidad**: Métricas ambientales y de emisiones

#### 💡 Ideas en Evaluación
- [ ] **Chat IA**: Asistente conversacional para consultas de datos
- [ ] **Realidad Aumentada**: Visualización 3D de infraestructura energética
- [ ] **Blockchain**: Trazabilidad de certificados de energía renovable
- [ ] **Gemelos Digitales**: Modelos virtuales de plantas de generación

## 📄 Licencia y Términos

### Licencia MIT
```
MIT License

Copyright (c) 2024 Melissa Cardona - Ministerio de Minas y Energía

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

### Términos de Uso
- **Datos XM**: Los datos de XM están sujetos a sus propios términos de uso
- **Uso Comercial**: Permitido bajo licencia MIT
- **Atribución**: Se requiere mención del autor original
- **Responsabilidad**: El software se proporciona "tal como está"

### Disclaimer
- Los datos mostrados provienen de fuentes oficiales pero pueden tener demoras
- Este sistema es una herramienta de análisis, no un sistema de control operativo
- Las decisiones operativas deben basarse en sistemas oficiales de XM y otras entidades

## 👨‍💻 Equipo de Desarrollo

### Autor Principal
**Melissa Cardona**
- 🏢 **Afiliación**: Ministerio de Minas y Energía de Colombia
- 💻 **GitHub**: [@MelissaCardona2003](https://github.com/MelissaCardona2003)
- 📧 **Email**: [contacto disponible en GitHub]
- 🔧 **Especialidad**: Desarrollo Full-Stack, Análisis de Datos Energéticos

### Colaboradores
- Agradecimientos especiales a la comunidad de desarrolladores de Dash
- Reconocimiento al equipo de XM por proporcionar APIs públicas
- Contribuciones de la comunidad energética colombiana

## 🙏 Agradecimientos y Referencias

### Instituciones
- **Ministerio de Minas y Energía**: Apoyo institucional y requerimientos del sector
- **XM S.A. E.S.P.**: Provisión de datos oficiales del sector eléctrico
- **UPME**: Unidad de Planeación Minero Energética - Datos de planeación
- **CREG**: Comisión de Regulación de Energía y Gas - Marco regulatorio

### Tecnologías y Librerías
- **Plotly Team**: Por la excelente librería de visualización
- **Dash Community**: Por el framework de aplicaciones analíticas
- **Python Software Foundation**: Por el lenguaje Python
- **Bootstrap Team**: Por el framework CSS

### Datos y Fuentes
- **OpenStreetMap**: Mapas base para visualizaciones geoespaciales
- **pydataxm**: Librería oficial para acceso a datos de XM
- **Comunidad Open Source**: Por las múltiples librerías utilizadas

### Inspiración
- Dashboards energéticos internacionales de ENTSO-E, ISO New England, CAISO
- Comunidad de análisis energético de IRENA y IEA
- Proyectos open source de visualización de datos energéticos

---

## 📞 Soporte y Contacto

### Reportar Problemas
- **GitHub Issues**: [Crear nuevo issue](https://github.com/MelissaCardona2003/Dashboard_Multipage_MME/issues)
- **Categorías**: Bug report, Feature request, Question, Documentation

### Solicitar Funcionalidades
- Use GitHub Discussions para propuestas de nuevas funcionalidades
- Incluya casos de uso específicos y beneficios esperados
- Considere contribuir con la implementación

### Comunidad
- **Discussions**: Foro de discusión en GitHub
- **Wiki**: Documentación colaborativa
- **Releases**: Anuncios de nuevas versiones

---

**🚀 Dashboard Multipage MME - Impulsando el Futuro Energético de Colombia**

*Última actualización: Septiembre 2025 | Versión: 2.1.0*

### 📊 Changelog Reciente
- **v2.1.0 (Sep 2025)**: Mejoras en análisis hidrológico con KPI cards optimizadas y filtros dinámicos
- **v2.0.0 (Sep 2024)**: Lanzamiento de dashboard multipage con 8 módulos especializados
- **v1.5.0 (Ago 2024)**: Integración completa con API XM y 190+ métricas
- **v1.0.0 (Jul 2024)**: Primera versión estable con análisis geoespacial
