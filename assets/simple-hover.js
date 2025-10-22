// Simple hover effects for homepage - SIN CUADROS ROJOS
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎨 Iniciando efectos hover simples SIN CUADROS ROJOS...');
    
    // Función para limpiar agresivamente cualquier borde rojo
    function cleanRedBorders(element) {
        if (!element) return;
        
        // Limpiar el elemento principal
        element.style.border = 'none';
        element.style.outline = 'none';
        element.style.boxShadow = 'none';
        element.style.backgroundColor = 'transparent';
        element.style.background = 'transparent';
        
        // Limpiar todos los hijos también
        const children = element.querySelectorAll('*');
        children.forEach(child => {
            child.style.border = 'none';
            child.style.outline = 'none';
            child.style.boxShadow = 'none';
            child.style.backgroundColor = 'transparent';
            child.style.background = 'transparent';
        });
    }
    
    setTimeout(function() {
        const modules = document.querySelectorAll('.custom-module');
        const svg = document.getElementById('background-svg');
        const pageBackground = document.getElementById('page-background');
        
        console.log('✨ Configurando', modules.length, 'módulos SIN CUADROS ROJOS');
        console.log('🎨 Fondo de página encontrado:', !!pageBackground);
        
        // Limpiar todos los módulos inicialmente
        modules.forEach(module => {
            cleanRedBorders(module);
        });
        
        modules.forEach(function(module) {
            const moduleId = module.id.replace('module-', '');
            const tooltip = document.getElementById('tooltip-' + moduleId);
            
            // Limpiar también inicialmente
            cleanRedBorders(module);
            
            module.addEventListener('mouseenter', function() {
                console.log('🌟 Hover SIN CUADROS ROJOS en:', moduleId);
                
                // LIMPIAR AGRESIVAMENTE ANTES DE CUALQUIER EFECTO
                cleanRedBorders(module);
                
                // Oscurecer SVG, fondo de página Y otros módulos AL MISMO NIVEL
                if (svg) {
                    svg.style.filter = 'brightness(0.25) saturate(0.4)';
                    svg.style.transition = 'filter 0.6s ease';
                }
                
                // Oscurecer fondo de página AL MISMO NIVEL que el SVG (brightness 0.25)
                if (pageBackground) {
                    // Color calculado exacto: #FCF3D6 * 0.25 = cada canal RGB multiplicado por 0.25
                    // FC = 252 * 0.25 = 63 = 3F
                    // F3 = 243 * 0.25 = 60.75 = 3D  
                    // D6 = 214 * 0.25 = 53.5 = 35
                    pageBackground.style.background = '#3F3D35'; 
                    pageBackground.style.transition = 'background 0.6s ease';
                }
                
                // Oscurecer otros módulos AL MISMO NIVEL que el SVG (brightness 0.25)
                modules.forEach(function(other) {
                    if (other !== module) {
                        cleanRedBorders(other); // Limpiar antes de aplicar efectos
                        other.style.filter = 'brightness(0.25) saturate(0.4)'; // MISMO que SVG
                        other.style.opacity = '0.3';
                        other.style.transform = 'scale(0.95)';
                        other.style.transition = 'all 0.6s ease';
                    }
                });
                
                // Iluminar módulo actual con sombras amarillas - SIN BORDES
                cleanRedBorders(module); // Limpiar antes de iluminar
                module.style.filter = 'brightness(1.2) saturate(1.3) drop-shadow(0 0 30px rgba(255,193,7,0.7)) drop-shadow(0 8px 20px rgba(255, 193, 7, 0.5))';
                module.style.transform = 'scale(1.06)';
                module.style.transition = 'all 0.6s ease';
                module.style.zIndex = '50';
                
                // Asegurar que NO hay bordes después de los efectos
                cleanRedBorders(module);
                
                // Mostrar tooltip
                if (tooltip) {
                    tooltip.style.opacity = '1';
                    tooltip.style.visibility = 'visible';
                    tooltip.style.transform = 'translate(-50%, -50%) scale(1)';
                }
            });
            
            module.addEventListener('mouseleave', function() {
                console.log('🌙 Restaurando SIN CUADROS ROJOS:', moduleId);
                
                // Restaurar SVG al estado original
                if (svg) {
                    svg.style.filter = 'none';
                }
                
                // Restaurar fondo de página al color original (mismo que SVG)
                if (pageBackground) {
                    pageBackground.style.background = '#FCF3D6'; // Color EXACTO del SVG
                    pageBackground.style.transition = 'background 0.6s ease';
                }
                
                // Restaurar todos los módulos
                modules.forEach(function(other) {
                    cleanRedBorders(other); // Limpiar antes de restaurar
                    other.style.filter = '';
                    other.style.opacity = '1';
                    other.style.transform = 'scale(1)';
                    other.style.transition = 'all 0.6s ease';
                    other.style.zIndex = '10';
                    
                    // Asegurar que NO hay bordes después de restaurar
                    cleanRedBorders(other);
                });
                
                // Ocultar tooltip
                if (tooltip) {
                    tooltip.style.opacity = '0';
                    tooltip.style.visibility = 'hidden';
                    tooltip.style.transform = 'translate(-50%, -50%) scale(0.9)';
                }
            });
        });
        
        console.log('🎉 Efectos hover configurados SIN CUADROS ROJOS');
        
        // Configurar botón de información
        const infoButton = document.getElementById('info-button');
        const infoModal = document.getElementById('info-modal');
        const closeInfoButton = document.getElementById('close-info-button');
        
        if (infoButton && infoModal && closeInfoButton) {
            console.log('📋 Configurando botón de información...');
            
            // Abrir modal al hacer clic en el botón de información
            infoButton.addEventListener('click', function() {
                console.log('📋 Abriendo modal de información');
                infoModal.style.display = 'flex';
            });
            
            // Cerrar modal al hacer clic en el botón cerrar
            closeInfoButton.addEventListener('click', function() {
                console.log('📋 Cerrando modal de información');
                infoModal.style.display = 'none';
            });
            
            // Cerrar modal al hacer clic fuera del contenido
            infoModal.addEventListener('click', function(e) {
                if (e.target === infoModal) {
                    console.log('📋 Cerrando modal por clic fuera');
                    infoModal.style.display = 'none';
                }
            });
            
            // Efecto hover en el botón de información
            infoButton.addEventListener('mouseenter', function() {
                infoButton.style.backgroundColor = '#E6B800';
                infoButton.style.transform = 'scale(1.1)';
            });
            
            infoButton.addEventListener('mouseleave', function() {
                infoButton.style.backgroundColor = '#F2C330';
                infoButton.style.transform = 'scale(1)';
            });
            
            console.log('📋 Botón de información configurado correctamente');
        }
    }, 500);
});