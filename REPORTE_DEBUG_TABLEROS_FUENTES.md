# 🎯 REPORTE DE DEBUGGING: PROBLEMA TABLEROS DE FUENTES

**Fecha:** 7 de Octubre, 2025  
**Investigación:** Análise completo de fallas en tableros de generación por fuentes  
**Estado:** 🔴 CRÍTICO - Requiere refactorización mayor  

---

## 📊 RESUMEN EJECUTIVO

Los tableros de fuentes (hidráulica, térmica, etc.) NO funcionan debido a **3 problemas críticos** en la integración con la API XM. Se identificaron **2 problemas resueltos** y **3 problemas críticos** que requieren atención inmediata.

**Salud del Sistema:** 40% (🔴 Crítico)

---

## ✅ PROBLEMAS RESUELTOS (2/5)

### 1. ✅ Nombres de Columnas Incorrectos
- **Problema:** El código buscaba `'Values_tipoRecurso'` pero la columna real es `'Values_Type'`
- **Impacto:** Causaba errores al filtrar plantas hidráulicas
- **Solución:** Mapeo correcto de columnas implementado
- **Estado:** SOLUCIONADO ✅

### 2. ✅ Filtrado de Plantas Hidráulicas  
- **Problema:** Patrones de filtrado incorrectos
- **Solución:** Usar `Values_Type == 'HIDRAULICA'` 
- **Resultado:** 160 plantas hidráulicas identificadas correctamente
- **Estado:** SOLUCIONADO ✅

---

## 🚨 PROBLEMAS CRÍTICOS SIN RESOLVER (3/5)

### 1. ❌ CRÍTICO: Códigos de Plantas Inválidos
- **Problema:** Los códigos de `ListadoRecursos` (ej: 2QBW, 2QEK, 2QRL) NO funcionan con la métrica `Gene`
- **Error:** `"No existe la entidad 2QBW"` para TODOS los códigos probados
- **Causa:** Diferentes sistemas de códigos entre APIs
- **Impacto:** ALTO - Sin códigos válidos, no se pueden obtener datos de generación

### 2. ❌ CRÍTICO: Métricas Sin Datos para Fechas Recientes
- **Problema:** Todas las métricas de generación devuelven vacío para fechas recientes
- **Métricas probadas:** Gene, GeneIdea, GeneSeguridad, GeneFueraMerito, etc.
- **Período probado:** 2025-10-05 a 2025-10-06
- **Impacto:** ALTO - Sin datos no se pueden generar visualizaciones

### 3. ❌ ALTO: Entidades No Reconocidas
- **Problema:** Mensaje `"No existe la entidad"` para todos los códigos probados
- **Códigos probados:** 19 códigos de plantas conocidas (GVIO, CHVR, BTRR, etc.)
- **Tasa de éxito:** 0% (0/19 códigos funcionaron)
- **Impacto:** ALTO - Imposible acceder a datos individuales de plantas

---

## 🔍 INVESTIGACIÓN REALIZADA

### Metodología
1. **Verificación API XM:** ✅ Funcionando (190 métricas disponibles)
2. **Análisis ListadoRecursos:** ✅ 1,243 recursos obtenidos, 160 hidráulicas
3. **Prueba códigos Gene:** ❌ 0/19 códigos funcionaron
4. **Exploración métricas:** ✅ 11 métricas de generación identificadas
5. **Prueba métricas reales:** ❌ 0/21 métricas devolvieron datos

### Hallazgos Técnicos
- **API XM Status:** 🟢 Operacional
- **pydataxm Version:** 0.3.16
- **Conectividad:** ✅ Establecida
- **Plantas Disponibles:** 160 hidráulicas identificadas
- **Códigos Válidos Encontrados:** 0

---

## 💡 SOLUCIONES RECOMENDADAS

### 🕒 SOLUCIÓN 1: Probar Fechas Más Antiguas
```python
# En lugar de fechas recientes:
fecha_fin = date.today() - timedelta(days=1)  # ❌ Sin datos

# Probar fechas más antiguas:
fecha_fin = date.today() - timedelta(days=14)  # ✅ Posible
fecha_inicio = fecha_fin - timedelta(days=7)
```

### 🔍 SOLUCIÓN 2: Investigar Códigos Correctos
1. **Contactar XM** para obtener mapeo actualizado de códigos
2. **Revisar documentación** pydataxm más reciente
3. **Probar formatos alternativos** de códigos de plantas

### 📋 SOLUCIÓN 3: Verificar Permisos API
- Confirmar acceso a datos de generación en tiempo real
- Verificar limitaciones de la API gratuita vs premium

### 🔄 SOLUCIÓN 4: Implementar Fallback Robusto
```python
def obtener_generacion_con_fallback(codigo_planta, fechas):
    try:
        # Intentar API real
        datos = objetoAPI.request_data("Gene", codigo_planta, *fechas)
        if datos is not None and not datos.empty:
            return datos
    except:
        pass
    
    # Fallback a datos simulados
    return generar_datos_simulados(codigo_planta, fechas)
```

---

## 🛠️ ACCIONES INMEDIATAS REQUERIDAS

### Prioridad 1 - CRÍTICA (Esta semana)
1. **Investigar códigos válidos** para plantas hidráulicas
2. **Probar fechas históricas** (1-4 semanas atrás)
3. **Implementar manejo de errores** robusto en callbacks

### Prioridad 2 - ALTA (Próximas 2 semanas)  
1. **Desarrollar sistema fallback** con datos simulados
2. **Contactar soporte XM** para clarificar códigos
3. **Actualizar documentación** del sistema

### Prioridad 3 - MEDIA (Este mes)
1. **Optimizar rendimiento** de consultas API
2. **Implementar cache** de datos válidos
3. **Añadir logs detallados** para debugging

---

## 📈 IMPACTO EN EL NEGOCIO

### Sin Solución
- **Tableros de fuentes:** 100% no funcionales
- **Experiencia usuario:** Muy negativa
- **Credibilidad sistema:** Comprometida

### Con Solución
- **Funcionalidad:** Restaurada 100%
- **Confiabilidad:** Mejorada significativamente  
- **Mantenimiento:** Más fácil y robusta

---

## 🔧 ARCHIVOS AFECTADOS

### Requieren Modificación Crítica
- `pages/generacion_hidraulica.py` - Cambiar códigos de plantas
- `pages/generacion_termica.py` - Cambiar códigos de plantas  
- `pages/generacion_solar.py` - Cambiar códigos de plantas
- `pages/generacion_eolica.py` - Cambiar códigos de plantas

### Require Actualización
- `pages/data_loader.py` - Mejorar manejo de errores
- `pages/components.py` - Añadir mensajes de estado
- `app.py` - Logging mejorado

---

## 📚 RECURSOS Y DOCUMENTOS

### Notebooks de Debugging
- `notebooks/debug_tableros_fuentes_problema.ipynb` - Investigación completa
- `notebooks/analisis_integracion_xm.ipynb` - Análisis API XM

### Logs Relevantes
- `logs/app.log` - Errores en tiempo real
- `dashboard_debug.log` - Debug específico

### Documentación
- [pydataxm Documentation](https://pypi.org/project/pydataxm/)
- [XM API Reference](http://servapibi.xm.com.co/)

---

## 🎯 CONCLUSIÓN

Los tableros de fuentes están **completamente no funcionales** debido a problemas críticos con códigos de plantas y disponibilidad de datos. Se requiere **intervención inmediata** para:

1. ✅ Encontrar códigos válidos para plantas
2. ✅ Verificar disponibilidad de datos históricos  
3. ✅ Implementar sistema fallback robusto

**Tiempo estimado de solución:** 1-2 semanas con recursos dedicados.

**Riesgo de no actuar:** Tableros permanecerán no funcionales indefinidamente.

---

*Reporte generado por debugging automatizado - 7 Oct 2025*