#!/usr/bin/env python3
"""
Script rápido de validación del sistema CACHE-PRECALENTAMIENTO-DASHBOARD
Ejecutar diariamente para verificar salud del sistema
"""

import os
import sys
import pickle
import json
from datetime import datetime

# Colores
OK = '\033[92m✅\033[0m'
WARN = '\033[93m⚠️\033[0m'
ERROR = '\033[91m❌\033[0m'
INFO = '\033[94mℹ️\033[0m'

def check_cache():
    """Verificar estado del cache"""
    cache_dir = '/var/cache/portal_energetico_cache'
    pkl_count = len([f for f in os.listdir(cache_dir) if f.endswith('.pkl')])
    
    if pkl_count >= 15:
        print(f"{OK} Cache: {pkl_count} archivos")
        return True
    else:
        print(f"{ERROR} Cache: solo {pkl_count} archivos (esperado 15+)")
        return False

def check_conversions():
    """Verificar conversiones"""
    cache_dir = '/var/cache/portal_energetico_cache'
    metadata_dir = os.path.join(cache_dir, 'metadata')
    
    validaciones = {
        'VoluUtilDiarEner': 100,
        'CapaUtilDiarEner': 100,
        'AporEner': 1000
    }
    
    errores = 0
    
    for pkl_file in os.listdir(cache_dir):
        if not pkl_file.endswith('.pkl'):
            continue
        
        cache_key = pkl_file.replace('.pkl', '')
        meta_path = os.path.join(metadata_dir, f'{cache_key}.json')
        
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            metric_name = meta.get('metric_name', '')
            
            with open(os.path.join(cache_dir, pkl_file), 'rb') as f:
                data = pickle.load(f)
            
            df = data[0] if isinstance(data, tuple) else data
            
            if 'Value' not in df.columns:
                continue
            
            max_val = df['Value'].max()
            
            for metrica, max_esperado in validaciones.items():
                if metrica in metric_name and max_val >= max_esperado:
                    errores += 1
        except:
            pass
    
    if errores == 0:
        print(f"{OK} Conversiones: correctas")
        return True
    else:
        print(f"{ERROR} Conversiones: {errores} errores")
        return False

def check_cron_log():
    """Verificar última ejecución del cron"""
    log_file = '/var/log/dashboard_mme_cache.log'
    
    if not os.path.exists(log_file):
        print(f"{WARN} Cron: log no encontrado")
        return False
    
    with open(log_file, 'r') as f:
        lines = f.readlines()[-50:]
    
    # Buscar línea con métricas pobladas
    for line in reversed(lines):
        if 'Métricas pobladas:' in line:
            if '17/17' in line:
                print(f"{OK} Cron: ejecutando 17/17 métricas")
                return True
            elif '6/6' in line:
                print(f"{WARN} Cron: ejecutando 6/6 métricas (esperado 17/17)")
                return False
    
    print(f"{WARN} Cron: no se encontró registro reciente")
    return False

def check_dashboard():
    """Verificar estado del dashboard"""
    result = os.system('systemctl is-active dashboard-mme.service > /dev/null 2>&1')
    
    if result == 0:
        print(f"{OK} Dashboard: activo")
        return True
    else:
        print(f"{ERROR} Dashboard: inactivo")
        return False

def main():
    print("\n" + "="*50)
    print(f"🔍 VALIDACIÓN RÁPIDA - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*50 + "\n")
    
    checks = [
        check_cache(),
        check_conversions(),
        check_cron_log(),
        check_dashboard()
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"\n{'='*50}")
    
    if passed == total:
        print(f"{OK} Sistema: {passed}/{total} checks OK")
        return 0
    elif passed >= total - 1:
        print(f"{WARN} Sistema: {passed}/{total} checks OK (advertencias)")
        return 1
    else:
        print(f"{ERROR} Sistema: {passed}/{total} checks OK (errores)")
        return 2

if __name__ == '__main__':
    sys.exit(main())
