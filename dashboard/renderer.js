console.log('Renderer.js loaded!');

const { ipcRenderer } = require('electron');

let currentView = 'dashboard';
let allTools = [];
let allComponents = [];
let projectData = {};
let categoryChart = null;
let languageChart = null;
let complexityChart = null;

// Initialize dashboard
async function init() {
    console.log('Initializing dashboard...');
    await loadDashboardData();
}

// Show different views
function showView(view) {
    console.log('Switching to view:', view);
    currentView = view;
    
    // Update navigation
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    document.querySelector(`nav a[onclick="showView('${view}')"]`).classList.add('active');
    
    // Show the selected view
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(view).classList.add('active');
    
    // Load data for the view
    switch(view) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'projects':
            loadProjectsView();
            break;
        case 'explorer':
            loadExplorerView();
            break;
        case 'insights':
            loadInsightsView();
            break;
    }
}

// Dashboard view functions
async function loadDashboardData() {
    console.log('Loading dashboard data...');
    try {
        // Get stats
        const stats = await ipcRenderer.invoke('api-call', '/api/stats');
        const tools = await ipcRenderer.invoke('api-call', '/api/tools');
        
        allTools = tools;
        
        // Update quick stats
        updateQuickStats(stats, tools);
        
        // Update recent activity
        updateRecentActivity(tools);
        
        // Update project summary
        updateProjectSummary(tools);
        
        // Draw technology stack chart
        drawTechStackChart(stats.languages);
        
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateQuickStats(stats, tools) {
    // Count unique projects
    const projects = new Set(tools.map(tool => tool.path.split('/')[0]));
    document.getElementById('totalProjects').textContent = projects.size;
    document.getElementById('totalFiles').textContent = stats.total_tools;
    
    // Estimate lines of code (you might want to add this to your scanner)
    const estimatedLoc = stats.total_tools * 100; // Rough estimate
    document.getElementById('totalLines').textContent = estimatedLoc.toLocaleString();
}

function updateRecentActivity(tools) {
    // Sort tools by last_modified
    const recentTools = tools
        .sort((a, b) => b.last_modified - a.last_modified)
        .slice(0, 5);
    
    const activityHtml = recentTools.map(tool => {
        const date = new Date(tool.last_modified);
        const timeAgo = getTimeAgo(date);
        return `
            <div class="activity-item" onclick="showFileDetails('${tool.path}')">
                <span class="activity-file">${tool.name}</span>
                <span class="activity-time">${timeAgo}</span>
                <div style="clear: both;"></div>
                <small>${tool.purpose || 'No description'}</small>
            </div>
        `;
    }).join('');
    
    document.getElementById('recentActivity').innerHTML = activityHtml;
}

function updateProjectSummary(tools) {
    // Group tools by project (first directory in path)
    const projects = {};
    tools.forEach(tool => {
        const project = tool.path.split('/')[0];
        if (!projects[project]) {
            projects[project] = {
                name: project,
                files: 0,
                languages: new Set(),
                categories: new Set()
            };
        }
        projects[project].files++;
        projects[project].languages.add(tool.language);
        if (tool.category) projects[project].categories.add(tool.category);
    });
    
    projectData = projects;
    
    const summaryHtml = Object.values(projects)
        .slice(0, 5)
        .map(project => `
            <div class="project-summary-item" onclick="showProjectDetails('${project.name}')">
                <strong>${project.name}</strong>
                <div>${project.files} files • ${Array.from(project.languages).join(', ')}</div>
            </div>
        `).join('');
    
    document.getElementById('projectSummary').innerHTML = summaryHtml;
}

function drawTechStackChart(languages) {
    const ctx = document.getElementById('techStackChart');
    if (!ctx) return;
    
    if (languageChart) {
        languageChart.destroy();
        languageChart = null;
    }
    
    const labels = Object.keys(languages);
    const data = Object.values(languages);
    
    languageChart = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#3498db', '#2ecc71', '#e74c3c', '#f39c12', 
                    '#9b59b6', '#1abc9c', '#34495e', '#e67e22'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Projects view functions
async function loadProjectsView() {
    const tools = allTools.length ? allTools : await ipcRenderer.invoke('api-call', '/api/tools');
    
    // Group by project
    const projects = {};
    tools.forEach(tool => {
        const projectName = tool.path.split('/')[0];
        if (!projects[projectName]) {
            projects[projectName] = {
                name: projectName,
                files: [],
                languages: new Set(),
                categories: new Set(),
                totalComplexity: 0
            };
        }
        projects[projectName].files.push(tool);
        projects[projectName].languages.add(tool.language);
        if (tool.category) projects[projectName].categories.add(tool.category);
        if (tool.complexity) {
            projects[projectName].totalComplexity += 
                tool.complexity === 'complex' ? 3 : 
                tool.complexity === 'moderate' ? 2 : 1;
        }
    });
    
    const projectsHtml = Object.values(projects).map(project => `
        <div class="project-card" onclick="showProjectDetails('${project.name}')">
            <h3>${project.name}</h3>
            <p>${project.files.length} files</p>
            <div class="project-meta">
                <span>${Array.from(project.languages).join(', ')}</span>
                <span>Complexity: ${getComplexityLabel(project.totalComplexity / project.files.length)}</span>
            </div>
            <div class="project-categories">
                ${Array.from(project.categories).map(cat => 
                    `<span class="category-tag">${cat}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
    
    document.getElementById('projectsList').innerHTML = projectsHtml;
}

// Explorer view functions
async function loadExplorerView() {
    const tools = allTools.length ? allTools : await ipcRenderer.invoke('api-call', '/api/tools');
    renderFileTree(tools);
}

function renderFileTree(tools) {
    const tree = buildFileTree(tools);
    const container = document.getElementById('fileTree');
    container.innerHTML = renderTreeNode(tree);
    
    // Add click handlers
    container.querySelectorAll('.tree-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            if (item.dataset.path) {
                showFileDetails(item.dataset.path);
            }
        });
    });
}

function buildFileTree(tools) {
    const tree = {};
    
    tools.forEach(tool => {
        const parts = tool.path.split('/');
        let current = tree;
        
        parts.forEach((part, index) => {
            if (index === parts.length - 1) {
                // File
                current[part] = { type: 'file', data: tool };
            } else {
                // Directory
                if (!current[part]) {
                    current[part] = { type: 'directory', children: {} };
                }
                current = current[part].children;
            }
        });
    });
    
    return tree;
}

function renderTreeNode(node, level = 0) {
    let html = '';
    
    Object.entries(node).forEach(([name, value]) => {
        if (value.type === 'file') {
            html += `
                <div class="tree-item file" style="padding-left: ${level * 20}px" data-path="${value.data.path}">
                    📄 ${name}
                </div>
            `;
        } else {
            html += `
                <div class="tree-item directory" style="padding-left: ${level * 20}px">
                    📁 ${name}
                </div>
                ${renderTreeNode(value.children, level + 1)}
            `;
        }
    });
    
    return html;
}

async function showFileDetails(path) {
    const tool = allTools.find(t => t.path === path);
    if (!tool) return;
    
    // Get components for this file
    const components = await ipcRenderer.invoke('api-call', '/api/components');
    const fileComponents = components.filter(c => c.tool_name === tool.name);
    
    // Build execution section
    let executionHtml = '';
    if (tool.execution_command) {
        executionHtml = `
            <h3>How to Run</h3>
            <div class="execution-info">
                <pre><code>${tool.execution_command}</code></pre>
                ${tool.requires_args ? '<p>⚠️ This script requires arguments</p>' : ''}
                ${tool.environment_vars && tool.environment_vars.length > 0 ? `
                    <p><strong>Environment Variables:</strong></p>
                    <ul>
                        ${tool.environment_vars.map(v => `<li>${v}</li>`).join('')}
                    </ul>
                ` : ''}
            </div>
        `;
    }
    
    // Build import section
    let importHtml = '';
    if (tool.importable_items && (
        tool.importable_items.functions?.length > 0 || 
        tool.importable_items.classes?.length > 0 ||
        tool.importable_items.length > 0
    )) {
        importHtml = '<h3>How to Import</h3><div class="import-info">';
        
        // Handle Python style imports
        if (tool.language === 'python') {
            const modulePath = tool.path.replace(/\//g, '.').replace('.py', '');
            
            if (tool.importable_items.functions?.length > 0) {
                importHtml += '<h4>Functions</h4>';
                tool.importable_items.functions.forEach(func => {
                    const args = func.args ? func.args.join(', ') : '';
                    importHtml += `
                        <div class="import-item">
                            <code>from ${modulePath} import ${func.name}</code>
                            <div>Usage: <code>${func.name}(${args})</code></div>
                            ${func.doc ? `<small>${func.doc}</small>` : ''}
                        </div>
                    `;
                });
            }
            
            if (tool.importable_items.classes?.length > 0) {
                importHtml += '<h4>Classes</h4>';
                tool.importable_items.classes.forEach(cls => {
                    importHtml += `
                        <div class="import-item">
                            <code>from ${modulePath} import ${cls.name}</code>
                            <div>Usage: <code>instance = ${cls.name}()</code></div>
                            ${cls.doc ? `<small>${cls.doc}</small>` : ''}
                        </div>
                    `;
                });
            }
        }
        
        // Handle JavaScript style imports
        else if (tool.language === 'javascript' && Array.isArray(tool.importable_items)) {
            importHtml += '<h4>Exports</h4>';
            tool.importable_items.forEach(item => {
                importHtml += `
                    <div class="import-item">
                        <code>const { ${item} } = require('./${tool.path}');</code>
                        <div>or</div>
                        <code>import { ${item} } from './${tool.path}';</code>
                    </div>
                `;
            });
        }
        
        importHtml += '</div>';
    }
    
    const detailsHtml = `
        <h2>${tool.name}</h2>
        <p><strong>Purpose:</strong> ${tool.purpose || 'No description'}</p>
        <p><strong>Language:</strong> ${tool.language}</p>
        <p><strong>Category:</strong> ${tool.category || 'Uncategorized'}</p>
        <p><strong>Complexity:</strong> ${tool.complexity || 'Unknown'}</p>
        <p><strong>Path:</strong> ${tool.path}</p>
        
        ${executionHtml}
        ${importHtml}
        
        <h3>Components (${fileComponents.length})</h3>
        <div class="components-list">
            ${fileComponents.map(comp => `
                <div class="component-item">
                    <strong>${comp.name}</strong> (${comp.type})
                    <div>${comp.purpose || 'No description'}</div>
                </div>
            `).join('')}
        </div>
    `;
    
    document.getElementById('fileDetails').innerHTML = detailsHtml;
}
// Insights view functions
async function loadInsightsView() {
    const stats = await ipcRenderer.invoke('api-call', '/api/stats');
    const tools = allTools.length ? allTools : await ipcRenderer.invoke('api-call', '/api/tools');
    
    // Draw complexity chart
    drawComplexityChart(tools);
    
    // Draw dependency graph
    drawDependencyGraph();
    
    // Show code patterns
    showCodePatterns(tools);
    
    // Show recommendations
    showRecommendations(tools);
}

function drawComplexityChart(tools) {
    const ctx = document.getElementById('complexityChart');
    if (!ctx) return;
    
    if (complexityChart) {
        complexityChart.destroy();
    }
    
    const complexityData = {
        simple: tools.filter(t => t.complexity === 'simple').length,
        moderate: tools.filter(t => t.complexity === 'moderate').length,
        complex: tools.filter(t => t.complexity === 'complex').length
    };
    
    complexityChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: Object.keys(complexityData),
            datasets: [{
                label: 'Number of Files',
                data: Object.values(complexityData),
                backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c']
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function showCodePatterns(tools) {
    // Analyze patterns (simplified version)
    const patterns = {
        'Singleton Files': tools.filter(t => t.name.includes('__init__')).length,
        'Test Files': tools.filter(t => t.name.includes('test')).length,
        'Configuration Files': tools.filter(t => t.category === 'config').length,
        'Entry Points': tools.filter(t => t.name.includes('main')).length
    };
    
    const patternsHtml = Object.entries(patterns).map(([pattern, count]) => `
        <div class="pattern-item">
            <strong>${pattern}:</strong> ${count} files
        </div>
    `).join('');
    
    document.getElementById('codePatterns').innerHTML = patternsHtml;
}

function showRecommendations(tools) {
    const recommendations = [];
    
    // Simple recommendations based on data
    const pythonFiles = tools.filter(t => t.language === 'python').length;
    if (pythonFiles > 10) {
        recommendations.push('Consider organizing Python files into packages with __init__.py files');
    }
    
    const complexFiles = tools.filter(t => t.complexity === 'complex').length;
    if (complexFiles > 5) {
        recommendations.push('You have several complex files. Consider refactoring for better maintainability');
    }
    
    const uncategorized = tools.filter(t => !t.category || t.category === 'N/A').length;
    if (uncategorized > tools.length * 0.3) {
        recommendations.push('Many files are uncategorized. Consider re-scanning with better categorization');
    }
    
    const recommendationsHtml = recommendations.map(rec => `
        <div class="recommendation-item">
            💡 ${rec}
        </div>
    `).join('') || '<p>No specific recommendations at this time.</p>';
    
    document.getElementById('recommendations').innerHTML = recommendationsHtml;
}

// Utility functions
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    
    return Math.floor(seconds) + " seconds ago";
}

function getComplexityLabel(score) {
    if (score > 2.5) return 'High';
    if (score > 1.5) return 'Medium';
    return 'Low';
}

function showProjectDetails(projectName) {
    // Switch to projects view and highlight the project
    showView('projects');
    // You could implement project filtering here
}

// Search functionality
async function search() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    if (!query) return;
    
    const results = allTools.filter(tool => 
        tool.name.toLowerCase().includes(query) ||
        (tool.purpose && tool.purpose.toLowerCase().includes(query)) ||
        (tool.category && tool.category.toLowerCase().includes(query))
    );
    
    // Show results in explorer view
    showView('explorer');
    renderFileTree(results);
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded');
    init();
});

// Make functions available globally
window.showView = showView;
window.search = search;
window.showFileDetails = showFileDetails;
window.showProjectDetails = showProjectDetails;