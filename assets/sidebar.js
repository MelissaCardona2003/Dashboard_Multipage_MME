// Funcionalidad del sidebar desplegable
document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarClose = document.getElementById('sidebar-close');
    const sidebarContent = document.getElementById('sidebar-content');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mainContent = document.querySelector('.main-content');

    // Función para abrir sidebar
    function openSidebar() {
        sidebarContent.classList.add('sidebar-open');
        sidebarOverlay.classList.add('show');
        if (mainContent) {
            mainContent.classList.add('main-content-shifted');
        }
    }

    // Función para cerrar sidebar
    function closeSidebar() {
        sidebarContent.classList.remove('sidebar-open');
        sidebarOverlay.classList.remove('show');
        if (mainContent) {
            mainContent.classList.remove('main-content-shifted');
        }
    }

    // Event listeners
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', openSidebar);
    }

    if (sidebarClose) {
        sidebarClose.addEventListener('click', closeSidebar);
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    // Cerrar sidebar con tecla Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });

    // Funcionalidad para acordeones del sidebar
    function initAccordions() {
        // Manejar clics en los acordeones
        const accordionButtons = document.querySelectorAll('.accordion-button');
        
        accordionButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Permitir que Bootstrap maneje el acordeón naturalmente
                setTimeout(() => {
                    // Ajustar la altura del sidebar si es necesario
                    const sidebarContent = document.getElementById('sidebar-content');
                    if (sidebarContent) {
                        // Recalcular altura si es necesario
                        sidebarContent.style.overflowY = 'auto';
                    }
                }, 300);
            });
        });
    }

    // Inicializar acordeones después de que se cargue el contenido
    setTimeout(initAccordions, 500);
    
    // Reinicializar acordeones cuando se navegue entre páginas
    window.addEventListener('load', initAccordions);
});

// Agregar estilos CSS dinámicos para el sidebar abierto
const sidebarStyles = `
.sidebar-open {
    left: 0 !important;
}

.sidebar-overlay.show {
    display: block !important;
}

.main-content-shifted {
    margin-left: 300px !important;
}

@media (max-width: 768px) {
    .main-content-shifted {
        margin-left: 0 !important;
    }
}
`;

// Insertar estilos en el head
const styleSheet = document.createElement('style');
styleSheet.type = 'text/css';
styleSheet.innerText = sidebarStyles;
document.head.appendChild(styleSheet);
