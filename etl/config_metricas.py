"""
Configuración de Métricas para ETL
Portal Energético MME
"""

# Métricas a poblar en la base de datos
METRICAS_CONFIG = {
    # Indicadores principales página Generación
    'indicadores_generacion': [
        {
            'metric': 'VoluUtilDiarEner',
            'entity': 'Embalse',
            'conversion': 'kWh_a_GWh',  # API devuelve en kWh
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch
        },
        {
            'metric': 'CapaUtilDiarEner',
            'entity': 'Embalse',
            'conversion': 'kWh_a_GWh',  # API devuelve en kWh
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch
        },
        {
            'metric': 'AporEner',
            'entity': 'Sistema',
            'conversion': 'Wh_a_GWh',  # API devuelve en Wh
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch
        },
        {
            'metric': 'AporEnerMediHist',
            'entity': 'Sistema',
            'conversion': 'Wh_a_GWh',  # API devuelve en Wh
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch
        },
        {
            'metric': 'Gene',
            'entity': 'Sistema',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch
        }
    ],
    
    # Generación por fuentes
    'generacion_fuentes': [
        {
            'metric': 'Gene',
            'entity': 'Recurso',
            'conversion': 'horas_a_diario',
            'dias_history': 1826,  # 5 años (2020-2025)
            'batch_size': 30  # 30 días por batch para 5 años
        }
    ],
    
    # Métricas de Hidrología
    'metricas_hidrologia': [
        {
            'metric': 'ListadoEmbalses',
            'entity': 'Sistema',
            'conversion': None,
            'dias_history': 2
        },
        {
            'metric': 'ListadoRios',
            'entity': 'Sistema',
            'conversion': None,
            'dias_history': 2
        },
        {
            'metric': 'AporEner',
            'entity': 'Rio',
            'conversion': 'Wh_a_GWh',
            'dias_history': 365,  # 1 año para análisis histórico
            'batch_size': 15  # 15 días por batch
        },
        {
            'metric': 'AporEnerMediHist',
            'entity': 'Rio',
            'conversion': 'Wh_a_GWh',
            'dias_history': 365,  # 1 año
            'batch_size': 15  # 15 días por batch
        },
        {
            'metric': 'AporCaudal',
            'entity': 'Rio',
            'conversion': None,  # Ya en m³/s
            'dias_history': 30,  # Aumentado de 7 a 30 días
            'batch_size': 10
        },
        {
            'metric': 'PorcApor',
            'entity': 'Rio',
            'conversion': None,  # Porcentajes
            'dias_history': 365,  # 1 año
            'batch_size': 15  # 15 días por batch
        }
    ],
    
    # Métricas de Distribución
    'metricas_distribucion': [
        {
            'metric': 'DemaCome',
            'entity': 'Sistema',
            'conversion': 'horas_a_diario',
            'dias_history': 1826,  # 5 años (igual que generación)
            'batch_size': 30
        },
        {
            'metric': 'DemaCome',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años (2020-2025) - ACTUALIZADO
            'batch_size': 7  # 7 días por batch (muchos agentes)
        },
        {
            'metric': 'DemaReal',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años (2020-2025) - ACTUALIZADO
            'batch_size': 7  # 7 días por batch (muchos agentes)
        },
        {
            'metric': 'DemaRealReg',
            'entity': 'Sistema',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años
            'batch_size': 30
        },
        {
            'metric': 'DemaRealReg',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años
            'batch_size': 7
        },
        {
            'metric': 'DemaRealNoReg',
            'entity': 'Sistema',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años
            'batch_size': 30
        },
        {
            'metric': 'DemaRealNoReg',
            'entity': 'Agente',
            'conversion': 'horas_a_diario',  # Values_Hour* en kWh, sumar → GWh
            'dias_history': 1826,  # 5 años
            'batch_size': 7
        },
        {
            'metric': 'DemaNoAtenProg',
            'entity': 'Area',
            'conversion': 'horas_a_diario',  # Suma 24 horas → GWh
            'dias_history': 30,
            'batch_size': 7
        }
    ],
    
    # Listados de sistema
    'listados_sistema': [
        {
            'metric': 'ListadoRecursos',
            'entity': 'Sistema',
            'conversion': None,
            'dias_history': 7
        },
        {
            'metric': 'ListadoAgentes',
            'entity': 'Sistema',
            'conversion': None,
            'dias_history': 7
        }
    ]
}
