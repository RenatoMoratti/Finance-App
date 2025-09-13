/**
 * Modern Finance App - Enhanced UI/UX JavaScript
 * Provides modern interactions, animations, and improved user experience
 */

class ModernFinanceApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupAnimations();
        this.setupInteractions();
        this.setupCounters();
        this.setupTooltips();
        this.setupNotifications();
        this.setupProgressBars();
        this.initializeOnLoad();
    }

    // Initialize everything when DOM is loaded
    initializeOnLoad() {
        document.addEventListener('DOMContentLoaded', () => {
            this.animateStatsCards();
            this.setupSmoothScrolling();
            this.initializeCharts();
        });
    }

    // Setup animations for page elements
    setupAnimations() {
        // Intersection Observer for fade-in animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe all animatable elements
        document.querySelectorAll('.stat-card, .modern-card, .status-card').forEach(el => {
            observer.observe(el);
        });
    }

    // Setup interactive elements
    setupInteractions() {
        // Enhanced button hover effects
        document.addEventListener('mouseover', (e) => {
            if (e.target.matches('.modern-btn, .stat-card, .modern-card')) {
                e.target.style.transform = 'translateY(-2px)';
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target.matches('.modern-btn, .stat-card, .modern-card')) {
                e.target.style.transform = '';
            }
        });

        // Enhanced sync button with loading state
        const syncButtons = document.querySelectorAll('[onclick*="syncAccount"]');
        syncButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                this.showSyncLoading(btn);
            });
        });

        // Enhanced form interactions
        this.setupFormEnhancements();
    }

    // Setup animated counters for statistics
    setupCounters() {
        const animateCounter = (element, target, duration = 2000) => {
            const start = 0;
            const increment = target / (duration / 16);
            let current = start;

            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    clearInterval(timer);
                    current = target;
                }
                
                // Format number based on type
                if (element.dataset.type === 'currency') {
                    element.textContent = this.formatCurrency(current);
                } else {
                    element.textContent = this.formatNumber(Math.floor(current));
                }
            }, 16);
        };

        // Find and animate stat numbers
        document.querySelectorAll('.stat-info h3').forEach(el => {
            const text = el.textContent.trim();
            const match = text.match(/[\d\.,]+/);
            if (match) {
                const number = parseFloat(match[0].replace(/[.,]/g, ''));
                if (!isNaN(number)) {
                    el.dataset.target = number;
                    if (text.includes('R$')) {
                        el.dataset.type = 'currency';
                    }
                }
            }
        });
    }

    // Animate stats cards on page load
    animateStatsCards() {
        const statCards = document.querySelectorAll('.stat-card');
        statCards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fade-in-up');
                
                // Animate the number
                const numberEl = card.querySelector('.stat-info h3');
                if (numberEl && numberEl.dataset.target) {
                    const target = parseFloat(numberEl.dataset.target);
                    this.animateNumber(numberEl, target, numberEl.dataset.type);
                }
            }, index * 150);
        });
    }

    // Enhanced number animation
    animateNumber(element, target, type, duration = 1500) {
        const start = 0;
        const startTime = performance.now();

        const updateNumber = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function for smooth animation
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = start + (target - start) * easeOut;

            if (type === 'currency') {
                element.textContent = this.formatCurrency(current);
            } else {
                element.textContent = this.formatNumber(Math.floor(current));
            }

            if (progress < 1) {
                requestAnimationFrame(updateNumber);
            }
        };

        requestAnimationFrame(updateNumber);
    }

    // Setup enhanced tooltips
    setupTooltips() {
        // Initialize Bootstrap tooltips with custom options
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                trigger: 'hover focus',
                delay: { show: 300, hide: 100 },
                customClass: 'modern-tooltip'
            });
        });
    }

    // Setup notification system
    setupNotifications() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
    }

    // Show modern notification
    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        notification.innerHTML = `
            <div class="notification-content">
                <i class="${icons[type]}"></i>
                <span>${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        container.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);

        // Auto remove
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    // Enhanced sync button loading state
    showSyncLoading(button) {
        const originalHTML = button.innerHTML;
        const originalDisabled = button.disabled;
        
        button.disabled = true;
        button.innerHTML = '<div class="loading-spinner"></div> Sincronizando...';
        
        // Mock the original sync function behavior
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.disabled = originalDisabled;
            this.showNotification('Sincronização concluída com sucesso!', 'success');
        }, 3000);
    }

    // Setup form enhancements
    setupFormEnhancements() {
        // Enhanced form field focus effects
        document.querySelectorAll('.modern-form-control').forEach(input => {
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });

            input.addEventListener('blur', () => {
                input.parentElement.classList.remove('focused');
                if (input.value.trim() !== '') {
                    input.parentElement.classList.add('has-value');
                } else {
                    input.parentElement.classList.remove('has-value');
                }
            });
        });

        // Enhanced currency input formatting
        document.querySelectorAll('input[name="amount"]').forEach(input => {
            input.addEventListener('input', (e) => {
                this.formatCurrencyInput(e.target);
            });
        });
    }

    // Setup progress bars for loading states
    setupProgressBars() {
        const createProgressBar = () => {
            const progress = document.createElement('div');
            progress.className = 'progress-bar';
            progress.innerHTML = '<div class="progress-fill"></div>';
            return progress;
        };

        // Add progress bars to loading states
        document.querySelectorAll('.loading-state').forEach(el => {
            el.appendChild(createProgressBar());
        });
    }

    // Initialize chart visualizations
    initializeCharts() {
        // Simple chart implementation using CSS and JavaScript
        this.createSpendingChart();
        this.createIncomeChart();
    }

    // Create simple spending visualization
    createSpendingChart() {
        const chartContainer = document.getElementById('spending-chart');
        if (!chartContainer) return;

        // Mock data for demo
        const categories = [
            { name: 'Alimentação', value: 1200, color: '#ef4444' },
            { name: 'Transporte', value: 800, color: '#3b82f6' },
            { name: 'Moradia', value: 2000, color: '#10b981' },
            { name: 'Lazer', value: 400, color: '#f59e0b' }
        ];

        const total = categories.reduce((sum, cat) => sum + cat.value, 0);
        
        chartContainer.innerHTML = categories.map(cat => {
            const percentage = (cat.value / total * 100).toFixed(1);
            return `
                <div class="chart-item" style="--percentage: ${percentage}%; --color: ${cat.color}">
                    <div class="chart-bar"></div>
                    <div class="chart-label">
                        <span class="chart-category">${cat.name}</span>
                        <span class="chart-value">${this.formatCurrency(cat.value)} (${percentage}%)</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Create simple income visualization
    createIncomeChart() {
        const chartContainer = document.getElementById('income-chart');
        if (!chartContainer) return;

        // Mock data for demo
        const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'];
        const income = [5000, 5200, 4800, 5500, 5100, 5300];
        const expenses = [4200, 4500, 4100, 4800, 4300, 4600];

        const maxValue = Math.max(...income, ...expenses);
        
        chartContainer.innerHTML = `
            <div class="chart-grid">
                ${months.map((month, index) => `
                    <div class="chart-column">
                        <div class="chart-bars">
                            <div class="chart-bar income" style="height: ${(income[index] / maxValue * 100)}%"></div>
                            <div class="chart-bar expense" style="height: ${(expenses[index] / maxValue * 100)}%"></div>
                        </div>
                        <div class="chart-month">${month}</div>
                    </div>
                `).join('')}
            </div>
            <div class="chart-legend">
                <div class="legend-item">
                    <div class="legend-color income"></div>
                    <span>Receitas</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color expense"></div>
                    <span>Despesas</span>
                </div>
            </div>
        `;
    }

    // Setup smooth scrolling
    setupSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Utility functions
    formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }

    formatNumber(value) {
        return new Intl.NumberFormat('pt-BR').format(value);
    }

    formatCurrencyInput(input) {
        let value = input.value.replace(/\D/g, '');
        value = (value / 100).toFixed(2);
        value = value.replace('.', ',');
        value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
        input.value = 'R$ ' + value;
    }

    // Add CSS styles for notifications and charts
    injectStyles() {
        const styles = `
            <style>
                /* Notification Styles */
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 1050;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .notification {
                    background: var(--bg-primary);
                    border: 1px solid var(--gray-200);
                    border-radius: var(--border-radius-lg);
                    box-shadow: var(--shadow-lg);
                    padding: var(--spacing-4);
                    min-width: 300px;
                    transform: translateX(100%);
                    transition: var(--transition-base);
                    opacity: 0;
                }

                .notification.show {
                    transform: translateX(0);
                    opacity: 1;
                }

                .notification-content {
                    display: flex;
                    align-items: center;
                    gap: var(--spacing-3);
                }

                .notification-success {
                    border-left: 4px solid var(--success-color);
                }

                .notification-error {
                    border-left: 4px solid var(--danger-color);
                }

                .notification-warning {
                    border-left: 4px solid var(--warning-color);
                }

                .notification-info {
                    border-left: 4px solid var(--info-color);
                }

                .notification-close {
                    background: none;
                    border: none;
                    color: var(--gray-500);
                    cursor: pointer;
                    margin-left: auto;
                    padding: var(--spacing-1);
                    border-radius: var(--border-radius-sm);
                }

                .notification-close:hover {
                    background: var(--gray-100);
                    color: var(--gray-700);
                }

                /* Chart Styles */
                .chart-item {
                    display: flex;
                    align-items: center;
                    margin-bottom: var(--spacing-3);
                    gap: var(--spacing-3);
                }

                .chart-bar {
                    height: 20px;
                    background: var(--color);
                    border-radius: var(--border-radius-sm);
                    width: var(--percentage);
                    min-width: 20px;
                    transition: width 1s ease-out;
                }

                .chart-label {
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-1);
                }

                .chart-category {
                    font-weight: 500;
                    color: var(--gray-800);
                    font-size: var(--font-size-sm);
                }

                .chart-value {
                    font-size: var(--font-size-xs);
                    color: var(--gray-600);
                }

                .chart-grid {
                    display: flex;
                    gap: var(--spacing-2);
                    align-items: flex-end;
                    height: 200px;
                    margin-bottom: var(--spacing-4);
                }

                .chart-column {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: var(--spacing-2);
                }

                .chart-bars {
                    display: flex;
                    gap: 2px;
                    align-items: flex-end;
                    height: 160px;
                }

                .chart-bar.income {
                    background: var(--success-color);
                    width: 20px;
                    border-radius: 2px 2px 0 0;
                    transition: height 1s ease-out;
                }

                .chart-bar.expense {
                    background: var(--danger-color);
                    width: 20px;
                    border-radius: 2px 2px 0 0;
                    transition: height 1s ease-out;
                }

                .chart-month {
                    font-size: var(--font-size-xs);
                    color: var(--gray-600);
                    font-weight: 500;
                }

                .chart-legend {
                    display: flex;
                    gap: var(--spacing-4);
                    justify-content: center;
                }

                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: var(--spacing-2);
                }

                .legend-color {
                    width: 12px;
                    height: 12px;
                    border-radius: 2px;
                }

                .legend-color.income {
                    background: var(--success-color);
                }

                .legend-color.expense {
                    background: var(--danger-color);
                }

                /* Animation Classes */
                .animate-in {
                    animation: slideInUp 0.6s ease-out forwards;
                }

                @keyframes slideInUp {
                    from {
                        opacity: 0;
                        transform: translateY(30px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /* Modern Tooltip */
                .modern-tooltip {
                    background: var(--gray-800);
                    color: var(--white);
                    border-radius: var(--border-radius-base);
                    padding: var(--spacing-2) var(--spacing-3);
                    font-size: var(--font-size-xs);
                    box-shadow: var(--shadow-lg);
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
}

// Initialize the modern finance app
document.addEventListener('DOMContentLoaded', () => {
    window.modernFinanceApp = new ModernFinanceApp();
    window.modernFinanceApp.injectStyles();
});

// Enhanced sync function to integrate with existing functionality
window.modernSyncAccount = function() {
    const app = window.modernFinanceApp;
    if (app) {
        app.showNotification('Iniciando sincronização...', 'info', 2000);
    }
    
    // Call the original sync function
    if (typeof syncAccount === 'function') {
        syncAccount();
    }
};

// Enhanced notification system for existing alerts
const originalAlert = window.alert;
window.alert = function(message) {
    const app = window.modernFinanceApp;
    if (app) {
        const type = message.toLowerCase().includes('erro') ? 'error' : 
                    message.toLowerCase().includes('sucesso') ? 'success' : 'info';
        app.showNotification(message, type);
    } else {
        originalAlert(message);
    }
};
