// Fixed renderer.js with improved toolbar and right-click functionality

const { ipcRenderer } = require('electron');

// Global state variables
let currentView = 'dashboard';
let allTools = [];
let projectData = {};
let languageChart = null;
let complexityChart = null;

// Initialize dashboard
async function init() {
    console.log('Initializing dashboard...');
    
    // Check for required libraries
    checkExternalLibraries();
    
    // Add custom styles
    updateCustomStyles();
    
    // Create clean dashboard structure
    createDashboardStructure();
    
    // Add components view
    addComponentsView();
    
    // Initialize context menu
    initializeContextMenu();
    
    // Load dashboard data
    await loadDashboardData();
}

// Add context menu functionality
function initializeContextMenu() {
    // Create context menu element
    const contextMenu = document.createElement('div');
    contextMenu.id = 'contextMenu';
    contextMenu.className = 'context-menu';
    contextMenu.style.display = 'none';
    document.body.appendChild(contextMenu);
    
    // Add global event listeners
    document.addEventListener('click', () => {
        hideContextMenu();
    });
    
    document.addEventListener('contextmenu', (e) => {
        // Don't show browser's context menu
        e.preventDefault();
        
        // Hide any existing context menu
        hideContextMenu();
        
        // Check if right-click was on a file or directory item
        let target = e.target;
        while (target && !target.classList.contains('tree-item') && !target.classList.contains('file-card')) {
            target = target.parentElement;
        }
        
        if (target) {
            // Show our custom context menu
            showContextMenu(e.clientX, e.clientY, target);
        }
    });
}
// Show context menu
function showContextMenu(x, y, target) {
    const contextMenu = document.getElementById('contextMenu');
    if (!contextMenu) return;
    
    // Determine menu items based on target
    let menuItems = [];
    
    if (target.classList.contains('file')) {
        const fileId = target.dataset.id;
        const filePath = target.dataset.path;
        menuItems = [
            { label: 'View Details', action: () => showFileDetails(fileId) },
            { label: 'View Source', action: () => {
                const file = allTools.find(t => t.id === fileId);
                if (file) viewFileSource(file);
            }},
            { label: 'Exclude File', action: () => {
                const file = allTools.find(t => t.id === fileId);
                if (file) addToExclusionList(file);
            }}
        ];
    } else if (target.classList.contains('directory')) {
        const dirPath = target.dataset.path;
        menuItems = [
            { label: 'Expand All', action: () => expandDirectory(target) },
            { label: 'Collapse All', action: () => collapseDirectory(target) },
            { label: 'Exclude Directory', action: () => {
                if (dirPath) showExclusionDialog(dirPath);
            }}
        ];
    } else if (target.classList.contains('project-card')) {
        const projectName = target.dataset.project;
        menuItems = [
            { label: 'Show Files', action: () => filterProjects(projectName) },
            { label: 'Show in Explorer', action: () => {
                showView('explorer');
                filterTreeByProject(projectName);
            }}
        ];
    }
    
    // Build menu HTML
    contextMenu.innerHTML = menuItems.map(item => 
        `<div class="context-menu-item">${item.label}</div>`
    ).join('');
    
    // Add event listeners to menu items
    contextMenu.querySelectorAll('.context-menu-item').forEach((item, index) => {
        item.addEventListener('click', () => {
            menuItems[index].action();
            hideContextMenu();
        });
    });
    
    // Position and show menu
    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.style.display = 'block';
    
    // Adjust position if menu goes off screen
    const rect = contextMenu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
        contextMenu.style.left = `${window.innerWidth - rect.width}px`;
    }
    if (rect.bottom > window.innerHeight) {
        contextMenu.style.top = `${window.innerHeight - rect.height}px`;
    }
}

// Hide context menu
function hideContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    if (contextMenu) {
        contextMenu.style.display = 'none';
    }
}

// Expand directory
function expandDirectory(dirElement) {
    const childrenContainer = dirElement.nextElementSibling;
    if (childrenContainer && childrenContainer.classList.contains('tree-children')) {
        childrenContainer.classList.remove('collapsed');
        
        // Update expand icon
        const expandIcon = dirElement.querySelector('.expand-icon');
        if (expandIcon) {
            expandIcon.textContent = '▼';
        }
        
        // Expand all subdirectories
        childrenContainer.querySelectorAll('.tree-item.directory').forEach(subdir => {
            expandDirectory(subdir);
        });
    }
}

// Collapse directory
function collapseDirectory(dirElement) {
    const childrenContainer = dirElement.nextElementSibling;
    if (childrenContainer && childrenContainer.classList.contains('tree-children')) {
        childrenContainer.classList.add('collapsed');
        
        // Update expand icon
        const expandIcon = dirElement.querySelector('.expand-icon');
        if (expandIcon) {
            expandIcon.textContent = '▶';
        }
    }
}

// Filter tree by project
function filterTreeByProject(projectName) {
    const filteredTools = allTools.filter(tool => {
        const path = tool.path || '';
        const parts = path.replace(/\\/g, '/').split('/');
        return parts.length > 0 && parts[0] === projectName;
    });
    
    renderFileTree(filteredTools);
}

// Check if required external libraries are loaded
function checkExternalLibraries() {
    const requiredLibraries = [
        { name: 'Chart.js', global: 'Chart', cdn: 'https://cdn.jsdelivr.net/npm/chart.js' },
        { name: 'vis-network', global: 'vis', cdn: 'https://unpkg.com/vis-network/standalone/umd/vis-network.min.js' }
    ];
    
    const missingLibraries = requiredLibraries.filter(lib => !window[lib.global]);
    
    if (missingLibraries.length > 0) {
        console.warn('Missing required libraries:', missingLibraries.map(lib => lib.name).join(', '));
        
        // Load missing libraries dynamically
        const promises = missingLibraries.map(lib => {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = lib.cdn;
                script.onload = () => resolve(lib.name);
                script.onerror = () => reject(new Error(`Failed to load ${lib.name}`));
                document.head.appendChild(script);
            });
        });
        
        Promise.all(promises)
            .then(loaded => {
                console.log('Successfully loaded libraries:', loaded.join(', '));
                // Reload current view
                showView(currentView);
            })
            .catch(error => {
                console.error('Failed to load libraries:', error);
                showNotification('Some required libraries failed to load. The application may not function correctly.', 'error');
            });
    }
}

// Show different views
function showView(view) {
    console.log('Switching to view:', view);
    currentView = view;
    
    // Update navigation
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    const activeLink = document.querySelector(`nav a[onclick="showView('${view}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    // Show the selected view
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const activeView = document.getElementById(view);
    if (activeView) {
        activeView.classList.add('active');
    }
    
    // Load data for the view
    switch (view) {
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
        case 'components':
            loadComponentsView();
            break;
    }
}

// Create dashboard structure
function createDashboardStructure() {
    const dashboardView = document.getElementById('dashboard');
    if (!dashboardView) return;
    
    // Clear current content
    dashboardView.innerHTML = '';
    
    // Create a header
    const header = document.createElement('h2');
    header.textContent = 'Code Overview';
    dashboardView.appendChild(header);
    
    // Create dashboard grid
    const grid = document.createElement('div');
    grid.className = 'dashboard-grid';
    dashboardView.appendChild(grid);
    
    // Create sections
    const sections = [
        {
            id: 'recentActivity',
            title: 'Recent Activity',
            content: '<p>Loading recent activity...</p>'
        },
        {
            id: 'projectSummary',
            title: 'Project Summary',
            content: '<p>Loading project summary...</p>'
        },
        {
            id: 'quickStats',
            title: 'Quick Stats',
            content: `
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value" id="totalProjects">...</span>
                        <span class="stat-label">Projects</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value" id="totalFiles">...</span>
                        <span class="stat-label">Files</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value" id="totalLines">...</span>
                        <span class="stat-label">Lines of Code</span>
                    </div>
                </div>
            `
        },
        {
            id: 'techStackChart',
            title: 'Technology Stack',
            content: '<p>Loading language distribution...</p>'
        }
    ];
    
    // Add sections to grid
    sections.forEach(section => {
        const card = document.createElement('div');
        card.className = 'dashboard-card';
        card.id = section.id + 'Card';
        
        card.innerHTML = `
            <h3>${section.title}</h3>
            <div id="${section.id}" class="card-content">
                ${section.content}
            </div>
        `;
        
        grid.appendChild(card);
    });
}

// Get empty state HTML
function getEmptyStateHTML(message = 'No data available') {
    return `
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <h3>No Data Available</h3>
            <p>${message}</p>
            <p class="empty-state-hint">Try scanning some projects with the CLI:</p>
            <pre>codeinventory scan ~/Projects</pre>
        </div>
    `;
}

// Dashboard view functions
async function loadDashboardData() {
    console.log('Loading dashboard data...');
    try {
        // Get all tools
        const tools = await ipcRenderer.invoke('api-call', '/api/tools');
        
        // Validate tools data
        const toolsArray = Array.isArray(tools) ? tools : [];
        
        if (!Array.isArray(tools) || tools.length === 0) {
            console.warn('No valid tools data available');
            displayEmptyDashboard('No code inventory data available. Try scanning your projects first.');
            return;
        }
        
        // Store tools globally for reuse across views
        allTools = toolsArray;
        
        // Get stats
        const stats = await ipcRenderer.invoke('api-call', '/api/stats');
        
        // Extract meaningful metrics
        const metrics = extractCodeMetrics(toolsArray);
        
        // Update dashboard components with metrics
        updateQuickStats(metrics, stats);
        updateRecentActivity(toolsArray);
        updateProjectSummary(toolsArray);
        updateLanguageDistribution(metrics.languageCounts);
        
    } catch (error) {
        console.error('Dashboard data loading error:', error);
        displayEmptyDashboard('Error loading dashboard data: ' + error.message);
    }
}

// Extract metrics from code data
function extractCodeMetrics(tools) {
    // Initialize metrics object
    const metrics = {
        totalFiles: tools.length,
        totalProjects: 0,
        totalComponents: 0,
        totalFunctions: 0,
        totalClasses: 0,
        codeLines: 0,
        projectCount: {},
        languageCounts: {},
        categoryCounts: {},
        complexityCounts: {
            simple: 0,
            moderate: 0,
            complex: 0,
            unknown: 0
        }
    };
    
    // Set of project names
    const projects = new Set();
    
    // Process each tool
    tools.forEach(tool => {
        // Count by language
        const lang = tool.language || 'unknown';
        metrics.languageCounts[lang] = (metrics.languageCounts[lang] || 0) + 1;
        
        // Count by category
        const category = tool.category || 'uncategorized';
        metrics.categoryCounts[category] = (metrics.categoryCounts[category] || 0) + 1;
        
        // Count by complexity
        if (tool.complexity) {
            metrics.complexityCounts[tool.complexity] = 
                (metrics.complexityCounts[tool.complexity] || 0) + 1;
        } else {
            metrics.complexityCounts.unknown++;
        }
        
        // Extract project name from path
        if (tool.path) {
            const parts = tool.path.replace(/\\/g, '/').split('/').filter(p => p);
            if (parts.length > 0) {
                const project = parts[0];
                projects.add(project);
                metrics.projectCount[project] = (metrics.projectCount[project] || 0) + 1;
            }
        }
        
        // Count components
        if (tool.components && Array.isArray(tool.components)) {
            metrics.totalComponents += tool.components.length;
            
            // Count functions and classes
            tool.components.forEach(comp => {
                if (comp.type === 'function') {
                    metrics.totalFunctions++;
                } else if (comp.type === 'class') {
                    metrics.totalClasses++;
                }
            });
        }
        
        // Count code lines
        if (tool.code_lines) {
            metrics.codeLines += parseInt(tool.code_lines, 10) || 0;
        }
    });
    
    metrics.totalProjects = projects.size;
    
    return metrics;
}

// Display empty dashboard with error message
function displayEmptyDashboard(message) {
    const containers = [
        'recentActivity', 
        'projectSummary', 
        'techStackChart'
    ];
    
    containers.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = `<p>${message}</p>`;
        }
    });
    
    document.getElementById('totalProjects').textContent = 'N/A';
    document.getElementById('totalFiles').textContent = 'N/A';
    document.getElementById('totalLines').textContent = 'N/A';
}

// Update quick stats in dashboard
function updateQuickStats(metrics, stats) {
    try {
        // Update DOM elements with stats
        const totalProjectsElem = document.getElementById('totalProjects');
        if (totalProjectsElem) {
            totalProjectsElem.textContent = metrics.totalProjects || stats?.total_projects || 'N/A';
        }
        
        const totalFilesElem = document.getElementById('totalFiles');
        if (totalFilesElem) {
            totalFilesElem.textContent = (metrics.totalFiles || stats?.total_tools || 0).toLocaleString();
        }
        
        // Handle code lines - try multiple sources
        const totalLinesElem = document.getElementById('totalLines');
        if (totalLinesElem) {
            // Try to get lines from various possible fields
            const linesCount = stats?.total_code_lines || 
                              stats?.totalCodeLines || 
                              metrics.codeLines || 0;
            
            if (linesCount) {
                totalLinesElem.textContent = parseInt(linesCount, 10).toLocaleString();
            } else {
                console.log('Lines of Code set to N/A (not found in API response)');
                totalLinesElem.textContent = 'N/A';
            }
        }
    } catch (error) {
        console.error('Error updating quick stats:', error);
    }
}

// Update recent activity section in dashboard
function updateRecentActivity(tools) {
    const activityContainer = document.getElementById('recentActivity');
    if (!activityContainer) return;
    
    // Sort tools by last_modified (most recent first)
    const recentTools = [...tools]
        .filter(tool => tool.last_modified) // Filter out tools without last_modified
        .sort((a, b) => {
            // Convert to numbers for comparison if they're not already
            const timeA = typeof a.last_modified === 'number' ? a.last_modified : parseInt(a.last_modified);
            const timeB = typeof b.last_modified === 'number' ? b.last_modified : parseInt(b.last_modified);
            return timeB - timeA; // Descending order (newest first)
        })
        .slice(0, 5); // Get top 5 most recent
    
    if (recentTools.length === 0) {
        activityContainer.innerHTML = '<p>No recent activity found.</p>';
        return;
    }
    
    let html = '';
    
    recentTools.forEach(tool => {
        // Format date
        let dateDisplay = 'Unknown date';
        
        if (tool.last_modified) {
            try {
                // Convert to milliseconds if it's in seconds (Unix timestamp)
                const timestamp = typeof tool.last_modified === 'number' 
                    ? tool.last_modified 
                    : parseInt(tool.last_modified);
                
                // If timestamp is in seconds (typical Unix format), convert to milliseconds
                const milliseconds = timestamp > 1000000000000 ? timestamp : timestamp * 1000;
                
                const date = new Date(milliseconds);
                
                // Check if date is valid
                if (!isNaN(date.getTime())) {
                    dateDisplay = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                }
            } catch (e) {
                console.warn('Error formatting date:', e);
            }
        }
        
        // Create activity item
        html += `
            <div class="activity-item" data-id="${tool.id || ''}">
                <div class="activity-header">
                    <span class="activity-file">${tool.name || 'Unnamed file'}</span>
                    <span class="activity-time">${dateDisplay}</span>
                </div>
                <div class="activity-description">
                    ${tool.purpose || 'No description available'}
                </div>
            </div>
        `;
    });
    
    activityContainer.innerHTML = html;
    
    // Add click handlers to activity items
    activityContainer.querySelectorAll('.activity-item').forEach(item => {
        item.addEventListener('click', () => {
            const fileId = item.dataset.id;
            if (fileId) {
                // Navigate to explorer view and show file details
                showView('explorer');
                showFileDetails(fileId);
            }
        });
    });
}

// Update project summary section in dashboard
function updateProjectSummary(tools) {
    const container = document.getElementById('projectSummary');
    if (!container) return;
    
    // Group tools by project (top-level directory)
    projectData = {};
    
    tools.forEach(tool => {
        if (!tool.path) return;
        
        // Extract project name from path
        const parts = tool.path.replace(/\\/g, '/').split('/').filter(p => p);
        const projectName = parts.length > 0 ? parts[0] : 'Unknown';
        
        if (!projectData[projectName]) {
            projectData[projectName] = {
                name: projectName,
                files: [],
                languages: new Set(),
                categories: new Set()
            };
        }
        
        projectData[projectName].files.push(tool);
        
        if (tool.language) {
            projectData[projectName].languages.add(tool.language);
        }
        
        if (tool.category) {
            projectData[projectName].categories.add(tool.category);
        }
    });
    
    // Sort projects by file count (descending)
    const sortedProjects = Object.values(projectData)
        .sort((a, b) => b.files.length - a.files.length)
        .slice(0, 5); // Show top 5 projects
    
    if (sortedProjects.length === 0) {
        container.innerHTML = '<p>No projects found.</p>';
        return;
    }
    
    let html = '';
    
    sortedProjects.forEach(project => {
        const languages = Array.from(project.languages).slice(0, 3).join(', ');
        const fileCount = project.files.length;
        
        html += `
            <div class="project-summary-item" data-project="${project.name}">
                <div class="project-header">
                    <span class="project-name">${project.name}</span>
                    <span class="project-stats">${fileCount} files</span>
                </div>
                <div class="project-languages">
                    ${languages}${project.languages.size > 3 ? ', ...' : ''}
                </div>
            </div>
        `;
    });
    
    // Add total count at the end
    const totalProjects = Object.keys(projectData).length;
    const totalFiles = tools.length;
    
    html += `
        <div class="projects-total">
            Total: ${totalProjects} projects, ${totalFiles} files
        </div>
    `;
    
    container.innerHTML = html;
    
    // Add click handlers to project items
    container.querySelectorAll('.project-summary-item').forEach(item => {
        item.addEventListener('click', () => {
            const projectName = item.dataset.project;
            if (projectName) {
                // Navigate to projects view and show filtered list
                showView('projects');
                filterProjects(projectName);
            }
        });
    });
}

// Update language distribution chart
function updateLanguageDistribution(languageCounts) {
    // Get the language chart container
    const container = document.getElementById('techStackChart');
    if (!container) return;
    
    // Clear previous content
    container.innerHTML = '';
    
    // Check if we have valid data
    if (!languageCounts || Object.keys(languageCounts).length === 0) {
        container.innerHTML = '<p>No language data available.</p>';
        return;
    }
    
    // Create a new canvas element
    const canvas = document.createElement('canvas');
    canvas.id = 'languageChartCanvas';
    container.appendChild(canvas);
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        container.innerHTML = '<p>Chart.js library not loaded. Please refresh the page.</p>';
        return;
    }
    
    try {
        // Sort languages by file count (descending)
        const sortedLanguages = Object.entries(languageCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8); // Show top 8 languages
        
        // Prepare chart data
        const labels = sortedLanguages.map(([lang]) => lang);
        const data = sortedLanguages.map(([_, count]) => count);
        
        // Color palette for languages
        const colors = [
            '#3498db', // blue
            '#2ecc71', // green
            '#e74c3c', // red
            '#f39c12', // orange
            '#9b59b6', // purple
            '#1abc9c', // teal
            '#34495e', // dark blue
            '#95a5a6'  // gray
        ];
        
        // Create chart
        if (languageChart) {
            languageChart.destroy();
        }
        
        languageChart = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 15,
                            padding: 15
                        }
                    },
                    title: {
                        display: true,
                        text: 'Language Distribution'
                    }
                },
                cutout: '60%'
            }
        });
    } catch (error) {
        console.error('Error creating language chart:', error);
        container.innerHTML = '<p>Error creating language chart: ' + error.message + '</p>';
    }
}

// Explorer view functions
async function loadExplorerView() {
    console.log('Loading explorer view...');
    
    // Make sure the file structure and details panels exist
    const fileExplorerContainer = document.getElementById('explorer');
    if (fileExplorerContainer) {
        // Check if we need to initialize the structure
        if (!document.getElementById('fileTree') || !document.getElementById('fileDetails')) {
            // Create the two-panel layout if it doesn't exist
            fileExplorerContainer.innerHTML = `
                <h2>Code Explorer</h2>
                <div class="explorer-layout">
                    <div class="file-structure">
                        <div class="file-tree-header">
                            <h3>File Structure</h3>
                            <div class="file-tree-controls">
                                <button id="expandAllBtn" class="tree-control">
                                    <span class="btn-icon">🔽</span> Expand All
                                </button>
                                <button id="collapseAllBtn" class="tree-control">
                                    <span class="btn-icon">🔼</span> Collapse All
                                </button>
                                <div class="file-search">
                                    <input type="text" id="fileSearchInput" placeholder="Search files...">
                                    <button id="fileSearchButton" class="tree-control">Search</button>
                                </div>
                            </div>
                        </div>
                        <div id="fileTree" class="file-tree-container">
                            <p>Loading file structure...</p>
                        </div>
                    </div>
                    <!-- ADD THIS RESIZER DIV -->
                    <div id="panelResizer" class="panel-resizer"></div>
                    <!-- END ADDITION -->
                    <div class="file-details-panel">
                        <h3>File Details</h3>
                        <div id="fileDetails">
                            <p>Select a file to view details</p>
                        </div>
                    </div>
                </div>
            `;
            // Add resizer functionality
            setupResizablePanels();
            
            // Add search functionality
            const searchInput = document.getElementById('fileSearchInput');
            const searchButton = document.getElementById('fileSearchButton');
            
            if (searchInput && searchButton) {
                searchButton.addEventListener('click', () => {
                    searchFileTree();
                });
                
                searchInput.addEventListener('keyup', (e) => {
                    if (e.key === 'Enter') {
                        searchFileTree();
                    }
                });
            }
            
            // Add expand/collapse all functionality
            document.getElementById('expandAllBtn')?.addEventListener('click', () => {
                document.querySelectorAll('.tree-children').forEach(child => {
                    child.classList.remove('collapsed');
                });
                
                document.querySelectorAll('.expand-icon').forEach(icon => {
                    icon.textContent = '▼';
                });
            });
            
            document.getElementById('collapseAllBtn')?.addEventListener('click', () => {
                document.querySelectorAll('.tree-children').forEach(child => {
                    child.classList.add('collapsed');
                });
                
                document.querySelectorAll('.expand-icon').forEach(icon => {
                    icon.textContent = '▶';
                });
            });
        }
    }
    
    // Get the file tree container
    const fileTreeContainer = document.getElementById('fileTree');
    if (!fileTreeContainer) return;
    
    fileTreeContainer.innerHTML = '<p>Loading file structure...</p>';
    
    try {
        // Get all tools
        const tools = (allTools && allTools.length > 0) ? allTools : await ipcRenderer.invoke('api-call', '/api/tools');
        
        // Check if we have valid file data
        if (Array.isArray(tools) && tools.length > 0) {
            // Store globally for reuse
            allTools = tools;
            
            // Render the file tree
            renderFileTree(tools);
        } else {
            fileTreeContainer.innerHTML = getEmptyStateHTML('No files found in inventory. Try scanning some code first.');
        }
    } catch (error) {
        console.error('Error loading files:', error);
        fileTreeContainer.innerHTML = `<p>Error loading file structure: ${error.message}</p>`;
    }
}

// Render file tree
function renderFileTree(files) {
    const container = document.getElementById('fileTree');
    if (!container) {
        console.error('fileTree container not found');
        return;
    }
    
    // Clear the container first
    container.innerHTML = '';
    
    // Handle empty files array
    if (!Array.isArray(files) || files.length === 0) {
        container.innerHTML = '<p>No files found in inventory.</p>';
        return;
    }
    
    // Build hierarchical file tree
    const fileTree = buildHierarchicalTree(files);
    
    // Create the tree container
    const treeDiv = document.createElement('div');
    treeDiv.className = 'tree-content';
    container.appendChild(treeDiv);
    
    // Render the tree
    treeDiv.innerHTML = renderTreeHTML(fileTree);
    
    // Add click handlers to tree items
    treeDiv.querySelectorAll('.tree-item').forEach(item => {
        // Directory click handler
        if (item.classList.contains('directory')) {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                
                // Toggle the next sibling (the children container)
                const childrenContainer = item.nextElementSibling;
                if (childrenContainer && childrenContainer.classList.contains('tree-children')) {
                    childrenContainer.classList.toggle('collapsed');
                    
                    // Update expand icon
                    const expandIcon = item.querySelector('.expand-icon');
                    if (expandIcon) {
                        if (childrenContainer.classList.contains('collapsed')) {
                            expandIcon.textContent = '▶';
                        } else {
                            expandIcon.textContent = '▼';
                        }
                    }
                }
            });
        }
        
        // File click handler
        if (item.classList.contains('file')) {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                
                // Get file ID and show details
                const fileId = item.getAttribute('data-id');
                if (fileId) {
                    showFileDetails(fileId);
                    
                    // Highlight selected file
                    treeDiv.querySelectorAll('.tree-item.selected').forEach(selected => {
                        selected.classList.remove('selected');
                    });
                    item.classList.add('selected');
                }
            });
        }
    });
}

// Build hierarchical tree from file paths
function buildHierarchicalTree(files) {
    const tree = {};
    
    files.forEach(file => {
        if (!file.path) return;
        
        // Split path into parts, normalizing separators
        const path = file.path.replace(/\\/g, '/').split('/').filter(p => p);
        
        // Start at the root of the tree
        let currentNode = tree;
        
        // Build path in tree
        path.forEach((part, index) => {
            // If this is the last part, it's a file
            if (index === path.length - 1) {
                currentNode[part] = {
                    type: 'file',
                    id: file.id || '',
                    name: part,
                    data: file
                };
            } else {
                // It's a directory
                if (!currentNode[part]) {
                    currentNode[part] = {
                        type: 'directory',
                        name: part,
                        children: {}
                    };
                }
                // Move to the next level
                currentNode = currentNode[part].children;
            }
        });
    });
    
    return tree;
}

// Render HTML for tree structure
function renderTreeHTML(tree, level = 0, parentPath = '') {
    let html = '';
    
    // Sort entries: directories first, then files, alphabetically within each type
    const entries = Object.entries(tree).sort((a, b) => {
        // Sort by type first (directory before file)
        if (a[1].type !== b[1].type) {
            return a[1].type === 'directory' ? -1 : 1;
        }
        // Then sort alphabetically by name
        return a[0].localeCompare(b[0]);
    });
    
    entries.forEach(([name, item]) => {
        if (item.type === 'directory') {
            // Build the full path for this directory
            const fullPath = parentPath ? `${parentPath}/${name}` : name;
            
            // Render directory
            html += `
                <div class="tree-item directory" data-path="${fullPath}" style="padding-left: ${level * 20}px">
                    <span class="expand-icon">▶</span>
                    <span class="tree-icon">📁</span>
                    <span class="dir-name">${name}</span>
                </div>
                <div class="tree-children collapsed">
                    ${renderTreeHTML(item.children, level + 1, fullPath)}
                </div>
            `;
        } else {
            // Render file
            const language = item.data?.language || 'unknown';
            const category = item.data?.category || '';
            
            html += `
                <div class="tree-item file" data-id="${item.id}" data-path="${item.data?.path || ''}" style="padding-left: ${level * 20}px">
                    <span class="tree-icon">📄</span>
                    <span class="file-name">${name}</span>
                    <span class="file-meta">
                        <span class="file-language">${language}</span>
                        ${category ? `<span class="file-category">${category}</span>` : ''}
                    </span>
                </div>
            `;
        }
    });
    
    return html;
}

// Search in file tree
function searchFileTree() {
    const searchInput = document.getElementById('fileSearchInput');
    if (!searchInput) return;
    
    const query = searchInput.value.toLowerCase().trim();
    if (!query) {
        // Reset tree to show all files
        renderFileTree(allTools);
        return;
    }
    
    // Filter files that match the query
    const matchingFiles = allTools.filter(tool => {
        const name = (tool.name || '').toLowerCase();
        const path = (tool.path || '').toLowerCase();
        const language = (tool.language || '').toLowerCase();
        const category = (tool.category || '').toLowerCase();
        const purpose = (tool.purpose || '').toLowerCase();
        
        return name.includes(query) || 
               path.includes(query) || 
               language.includes(query) ||
               category.includes(query) ||
               purpose.includes(query);
    });
    
    // Render filtered tree
    if (matchingFiles.length > 0) {
        renderFileTree(matchingFiles);
        
        // Show search results info
        const container = document.getElementById('fileTree');
        if (container) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'search-results-info';
            infoDiv.textContent = `Found ${matchingFiles.length} files matching "${query}"`;
            container.insertBefore(infoDiv, container.firstChild);
        }
    } else {
        // No matches found
        const container = document.getElementById('fileTree');
        if (container) {
            container.innerHTML = `
                <div class="no-results">
                    <p>No files found matching "${query}"</p>
                    <button class="reset-search-btn tree-control">Clear Search</button>
                </div>
            `;
            
            // Add handler for reset button
            const resetBtn = container.querySelector('.reset-search-btn');
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    searchInput.value = '';
                    renderFileTree(allTools);
                });
            }
        }
    }
}

// Show file details
function showFileDetails(fileId) {
    console.log(`Showing details for file ID: ${fileId}`);
    
    const fileDetailsContainer = document.getElementById('fileDetails');
    if (!fileDetailsContainer) {
        console.error('fileDetails container not found');
        return;
    }
    
    // Show loading state
    fileDetailsContainer.innerHTML = '<p>Loading file details...</p>';
    
    // First try to find the file in already loaded data
    let file = null;
    
    // Find the file by ID
    for (let i = 0; i < allTools.length; i++) {
        if (allTools[i].id === fileId) {
            file = allTools[i];
            break;
        }
    }
    
    if (file) {
        renderFileDetails(file);
    } else {
        // If not found in global array, try to fetch by ID
        ipcRenderer.invoke('api-call', `/api/file/${fileId}`)
            .then(fileData => {
                if (fileData && !fileData.error) {
                    renderFileDetails(fileData);
                } else {
                    fileDetailsContainer.innerHTML = `
                        <div class="error-message">
                            <p>Error loading file details: ${fileData?.message || 'File not found'}</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error fetching file details:', error);
                fileDetailsContainer.innerHTML = `
                    <div class="error-message">
                        <p>Error loading file details: ${error.message}</p>
                    </div>
                `;
            });
    }
}

// Render file details
function renderFileDetails(file) {
    const container = document.getElementById('fileDetails');
    if (!container) return;

    if (!file) {
        container.innerHTML = '<p>No file selected.</p>';
        return;
    }
    
    // Basic file information
    let basicInfoHtml = `
        <h2>${file.name || 'Unnamed File'}</h2>
        <div class="file-path">${file.path || 'Unknown path'}</div>
        
        <div class="file-meta">
            <div class="metric-row">
                <span class="metric-label">Language:</span>
                <span class="metric-value">${file.language || 'Unknown'}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Category:</span>
                <span class="metric-value">${file.category || 'Uncategorized'}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Complexity:</span>
                <span class="metric-value">${file.complexity || 'Unknown'}</span>
            </div>
        </div>
    `;
    
    let purposeHtml = '';
    if (file.purpose) {
        purposeHtml = `
            <div class="file-purpose">
                <h3>Purpose</h3>
                <p>${file.purpose}</p>
            </div>
        `;
    }
    
    let descriptionHtml = '';
    if (file.description) {
        descriptionHtml = `
            <div class="file-description">
                <h3>Description</h3>
                <p>${file.description}</p>
            </div>
        `;
    }
    
    // Add file actions section with exclusion options
    let actionsHtml = `
        <div class="file-actions">
            <h3>File Actions</h3>
            <div class="action-buttons">
                <button id="excludeFileBtn" class="action-btn exclude-btn">
                    <span class="action-icon">🚫</span> Exclude File
                </button>
                <button id="excludeDirBtn" class="action-btn exclude-dir-btn">
                    <span class="action-icon">📁</span> Exclude Directory
                </button>
                <button id="viewSourceBtn" class="action-btn view-btn">
                    <span class="action-icon">📝</span> View Source
                </button>
            </div>
        </div>
    `;
    
    // Add component information if available
    let componentsHtml = '';
    if (file.components && Array.isArray(file.components) && file.components.length > 0) {
        componentsHtml = `
            <div class="file-components">
                <h3>Components (${file.components.length})</h3>
                <div class="components-list">
                    ${file.components.map(comp => `
                        <div class="component-item">
                            <span class="component-type">${comp.type || 'unknown'}</span>
                            <strong>${comp.name || 'unnamed'}</strong>
                            <p>${comp.purpose || 'No description available'}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // Combine all sections
    container.innerHTML = basicInfoHtml + purposeHtml + descriptionHtml + actionsHtml + componentsHtml;
    
    // Add click handlers for buttons
    document.getElementById('excludeFileBtn')?.addEventListener('click', () => {
        addToExclusionList(file);
    });
    
    document.getElementById('excludeDirBtn')?.addEventListener('click', () => {
        // Get directory from file path
        const filePath = file.path;
        const lastSlashIndex = filePath.lastIndexOf('/');
        
        if (lastSlashIndex > 0) {
            const dirPath = filePath.substring(0, lastSlashIndex);
            // Show confirmation dialog
            showExclusionDialog(dirPath);
        } else {
            showNotification('Could not determine parent directory', 'error');
        }
    });
    
    document.getElementById('viewSourceBtn')?.addEventListener('click', () => {
        viewFileSource(file);
    });
}

// View file source
function viewFileSource(file) {
    // Create a modal with syntax-highlighted source code
    const modal = document.createElement('div');
    modal.className = 'source-modal';
    
    // Get file content using an API call
    ipcRenderer.invoke('api-call', `/api/file-content?path=${encodeURIComponent(file.path)}`)
        .then(content => {
            // Create modal content
            modal.innerHTML = `
                <div class="source-modal-content">
                    <div class="source-modal-header">
                        <h3>${file.name}</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="source-modal-body">
                        <pre><code class="language-${file.language}">${escapeHtml(content)}</code></pre>
                    </div>
                </div>
            `;
            
            // Add to document
            document.body.appendChild(modal);
            
            // Add close handler
            modal.querySelector('.close-btn').addEventListener('click', () => {
                document.body.removeChild(modal);
            });
        })
        .catch(error => {
            console.error('Error loading file content:', error);
            showNotification(`Error loading file content: ${error.message}`, 'error');
        });
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Show exclusion dialog
function showExclusionDialog(dirPath) {
    // Create a modal dialog
    const modal = document.createElement('div');
    modal.className = 'exclusion-modal';
    
    modal.innerHTML = `
        <div class="exclusion-modal-content">
            <div class="exclusion-modal-header">
                <h3>Exclude Directory</h3>
                <button class="close-btn">&times;</button>
            </div>
            <div class="exclusion-modal-body">
                <p>You're about to exclude the following directory from future scans:</p>
                <code>${dirPath}</code>
                
                <div class="exclusion-options">
                    <div class="option">
                        <input type="checkbox" id="includeSubdirs" checked>
                        <label for="includeSubdirs">Include all subdirectories</label>
                    </div>
                </div>
                
                <div class="exclusion-warning">
                    <p>⚠️ This will affect future scans only. Existing data will remain in the inventory.</p>
                </div>
            </div>
            <div class="exclusion-modal-footer">
                <button class="cancel-btn">Cancel</button>
                <button class="confirm-btn">Exclude Directory</button>
            </div>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Add event handlers
    modal.querySelector('.close-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    modal.querySelector('.cancel-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    modal.querySelector('.confirm-btn').addEventListener('click', () => {
        const includeSubdirs = document.getElementById('includeSubdirs').checked;
        addDirectoryToExclusions(dirPath, includeSubdirs);
        document.body.removeChild(modal);
    });
}

// Function to add a file to the exclusion list
async function addToExclusionList(file) {
    try {
        // Add to exclusions via API
        const response = await ipcRenderer.invoke('api-call', '/api/exclusions/add', 'POST', {
            path: file.path,
            isDirectory: false
        });
        
        if (response.success) {
            // Show success message
            showNotification(`Excluded ${file.name} from future scans.`, 'success');
            
            // Optionally, mark the file in the UI as excluded
            document.querySelector('.file-path').classList.add('excluded');
        } else {
            showNotification(`Error: ${response.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error updating exclusions:', error);
        showNotification(`Error excluding file: ${error.message}`, 'error');
    }
}

// Function to add a directory to exclusions
async function addDirectoryToExclusions(dirPath, includeSubdirectories) {
    try {
        console.log(`Adding directory to exclusions: ${dirPath} (include subdirs: ${includeSubdirectories})`);
        
        // Add to exclusions via API
        const response = await ipcRenderer.invoke('api-call', '/api/exclusions/add', 'POST', {
            path: dirPath,
            isDirectory: true,
            includeSubdirectories: includeSubdirectories
        });
        
        if (response.success) {
            // Show success message
            showNotification(`Excluded directory "${dirPath}" from future scans.`, 'success');
            
            // Update UI to reflect change - mark all matching directories as excluded
            document.querySelectorAll('.tree-item.directory').forEach(dirItem => {
                const itemPath = dirItem.dataset.path;
                if (itemPath === dirPath || (includeSubdirectories && itemPath.startsWith(dirPath + '/'))) {
                    dirItem.classList.add('excluded');
                }
            });
            
            // Also mark all files within this directory as excluded
            document.querySelectorAll('.tree-item.file').forEach(fileItem => {
                const itemPath = fileItem.dataset.path;
                if (itemPath && (itemPath.startsWith(dirPath + '/') || (dirPath && itemPath.includes('/' + dirPath + '/')))) {
                    fileItem.classList.add('excluded');
                }
            });
        } else {
            showNotification(`Error: ${response.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error updating directory exclusions:', error);
        showNotification(`Error excluding directory: ${error.message}`, 'error');
    }
}

// Projects view functions
async function loadProjectsView() {
    try {
        const tools = (allTools && allTools.length > 0) ? allTools : await ipcRenderer.invoke('api-call', '/api/tools');
        
        if (!Array.isArray(tools) || tools.length === 0) {
            document.getElementById('projectsList').innerHTML = getEmptyStateHTML('No projects found in inventory.');
            return;
        }
        
        // Store tools if needed
        if (allTools.length === 0) {
            allTools = tools;
        }
        
        // Group tools by project
        const projects = {};
        
        tools.forEach(tool => {
            if (!tool.path) return;
            
            // Extract project name from path
            const parts = tool.path.replace(/\\/g, '/').split('/').filter(p => p);
            const projectName = parts.length > 0 ? parts[0] : 'Unknown';
            
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
            
            if (tool.language) {
                projects[projectName].languages.add(tool.language);
            }
            
            if (tool.category) {
                projects[projectName].categories.add(tool.category);
            }
            
            if (tool.complexity) {
                projects[projectName].totalComplexity += 
                    tool.complexity === 'complex' ? 3 : 
                    tool.complexity === 'moderate' ? 2 : 1;
            }
        });
        
        // Sort projects by file count (descending)
        const sortedProjects = Object.values(projects)
            .sort((a, b) => b.files.length - a.files.length);
        
        if (sortedProjects.length === 0) {
            document.getElementById('projectsList').innerHTML = getEmptyStateHTML('No projects found in inventory.');
            return;
        }
        
        let html = '';
        
        sortedProjects.forEach(project => {
            const complexityScore = project.files.length > 0 ? 
                project.totalComplexity / project.files.length : 0;
            
            html += `
                <div class="project-card" data-project="${project.name}">
                    <h3>${project.name}</h3>
                    <p>${project.files.length} files</p>
                    <div class="project-meta">
                        <span>${Array.from(project.languages).slice(0, 3).join(', ')}${project.languages.size > 3 ? '...' : ''}</span>
                        <span>Complexity: ${getComplexityLabel(complexityScore)}</span>
                    </div>
                    <div class="project-categories">
                        ${Array.from(project.categories).slice(0, 5).map(cat => 
                            `<span class="category-tag">${cat}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        });
        
        document.getElementById('projectsList').innerHTML = html;
        
        // Add click handlers to project cards
        document.querySelectorAll('.project-card').forEach(card => {
            card.addEventListener('click', () => {
                const projectName = card.dataset.project;
                if (projectName) {
                    // Show filtered view of files in this project
                    filterProjects(projectName);
                }
            });
        });
    } catch (error) {
        console.error('Failed to load projects view:', error);
        document.getElementById('projectsList').innerHTML = `<p>Error loading projects: ${error.message}</p>`;
    }
}

// Filter projects
function filterProjects(projectName) {
    console.log(`Filtering for project: ${projectName}`);
    
    // Update UI to show we're filtering
    const titleElement = document.querySelector('#projects h2');
    if (titleElement) {
        titleElement.textContent = `Project: ${projectName}`;
    }
    
    // Filter the tools to show only those from this project
    const filteredTools = allTools.filter(tool => {
        const path = tool.path || '';
        const parts = path.replace(/\\/g, '/').split('/');
        return parts.length > 0 && parts[0] === projectName;
    });
    
    // Display the filtered tools
    if (filteredTools.length > 0) {
        renderProjectsList(filteredTools);
    } else {
        const container = document.getElementById('projectsList');
        if (container) {
            container.innerHTML = `<p>No files found for project "${projectName}".</p>`;
        }
    }
}

// Render projects list
function renderProjectsList(tools) {
    const container = document.getElementById('projectsList');
    if (!container) return;
    
    if (!Array.isArray(tools) || tools.length === 0) {
        container.innerHTML = '<p>No files found.</p>';
        return;
    }
    
    // Group by top-level directories
    const filesByDir = {};
    
    tools.forEach(tool => {
        if (!tool.path) return;
        
        const parts = tool.path.replace(/\\/g, '/').split('/').filter(p => p);
        if (parts.length < 2) return;
        
        const dir = parts[1]; // Second-level directory
        
        if (!filesByDir[dir]) {
            filesByDir[dir] = [];
        }
        
        filesByDir[dir].push(tool);
    });
    
    // Sort directories
    const sortedDirs = Object.keys(filesByDir).sort();
    
    let html = '';
    
    sortedDirs.forEach(dir => {
        const files = filesByDir[dir];
        
        html += `
            <div class="directory-group">
                <h3 class="directory-name">${dir} (${files.length})</h3>
                <div class="file-grid">
        `;
        
        // Sort files by name
        const sortedFiles = files.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        
        sortedFiles.forEach(file => {
            html += `
                <div class="file-card" data-id="${file.id || ''}">
                    <div class="file-icon">📄</div>
                    <div class="file-info">
                        <div class="file-name">${file.name || 'Unnamed'}</div>
                        <div class="file-meta">
                            <span class="file-language">${file.language || 'Unknown'}</span>
                            ${file.category ? `<span class="file-category">${file.category}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Add click handlers to file cards
    document.querySelectorAll('.file-card').forEach(card => {
        card.addEventListener('click', () => {
            const fileId = card.dataset.id;
            if (fileId) {
                // Navigate to file details
                showView('explorer');
                showFileDetails(fileId);
            }
        });
    });
}

// Add components view
function addComponentsView() {
    // Create the components view if it doesn't exist
    if (!document.getElementById('components')) {
        const mainContent = document.getElementById('content');
        if (!mainContent) return;
        
        const componentsView = document.createElement('div');
        componentsView.id = 'components';
        componentsView.className = 'view';
        
        componentsView.innerHTML = `
            <h2>Reusable Components</h2>
            
            <div class="components-filters">
                <div class="filter-group">
                    <label for="languageFilter">Language:</label>
                    <select id="languageFilter">
                        <option value="">All Languages</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="typeFilter">Type:</label>
                    <select id="typeFilter">
                        <option value="">All Types</option>
                        <option value="function">Functions</option>
                        <option value="class">Classes</option>
                        <option value="method">Methods</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="componentSearch">Search:</label>
                    <input type="text" id="componentSearch" placeholder="Search components...">
                </div>
            </div>
            
            <div class="components-grid" id="componentsGrid">
                <p>Loading components...</p>
            </div>
        `;
        
        mainContent.appendChild(componentsView);
        
        // Add event listeners for filters
        document.getElementById('languageFilter')?.addEventListener('change', filterComponents);
        document.getElementById('typeFilter')?.addEventListener('change', filterComponents);
        document.getElementById('componentSearch')?.addEventListener('input', filterComponents);
    }
    
    // Now add the components view to the navigation
    const navList = document.querySelector('nav ul');
    if (navList && !document.querySelector('nav a[onclick="showView(\'components\')"]')) {
        const navItem = document.createElement('li');
        navItem.innerHTML = '<a href="#" onclick="showView(\'components\')">Components</a>';
        navList.appendChild(navItem);
    }
}

// Load components view
async function loadComponentsView() {
    console.log('Loading components view...');
    
    const componentsGrid = document.getElementById('componentsGrid');
    if (!componentsGrid) return;
    
    componentsGrid.innerHTML = '<p>Loading components...</p>';
    
    try {
        // Get tools data if not already available
        const tools = (allTools && allTools.length > 0) ? 
            allTools : 
            await ipcRenderer.invoke('api-call', '/api/tools');
        
        if (!Array.isArray(tools) || tools.length === 0) {
            componentsGrid.innerHTML = '<p>No components found.</p>';
            return;
        }
        
        // Extract all components
        const allComponents = [];
        const languages = new Set();
        
        tools.forEach(tool => {
            if (tool.components && Array.isArray(tool.components)) {
                tool.components.forEach(comp => {
                    if (comp.name) {
                        allComponents.push({
                            ...comp,
                            parentFile: tool.name,
                            parentPath: tool.path,
                            parentId: tool.id,
                            language: tool.language
                        });
                        
                        if (tool.language) {
                            languages.add(tool.language);
                        }
                    }
                });
            }
        });
        
        // Update language filter options
        const languageFilter = document.getElementById('languageFilter');
        if (languageFilter) {
            // Clear existing options except the first one
            while (languageFilter.options.length > 1) {
                languageFilter.remove(1);
            }
            
            // Add language options
            Array.from(languages).sort().forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = lang;
                languageFilter.appendChild(option);
            });
        }
        
        // Render components
        renderComponentsGrid(allComponents);
        
    } catch (error) {
        console.error('Error loading components:', error);
        componentsGrid.innerHTML = `<p>Error loading components: ${error.message}</p>`;
    }
}

// Render components grid
function renderComponentsGrid(components) {
    const grid = document.getElementById('componentsGrid');
    if (!grid) return;
    
    if (!Array.isArray(components) || components.length === 0) {
        grid.innerHTML = '<p>No components found matching your filters.</p>';
        return;
    }
    
    // Group components by language for better organization
    const componentsByLanguage = {};
    
    components.forEach(comp => {
        const lang = comp.language || 'unknown';
        if (!componentsByLanguage[lang]) {
            componentsByLanguage[lang] = [];
        }
        componentsByLanguage[lang].push(comp);
    });
    
    // Build the HTML
    let html = '';
    
    Object.entries(componentsByLanguage).forEach(([language, comps]) => {
        html += `
            <div class="language-section">
                <h3 class="language-header">${language}</h3>
                <div class="language-components">
        `;
        
        comps.forEach(comp => {
            html += `
                <div class="component-card" data-parent-id="${comp.parentId}" data-type="${comp.type}">
                    <div class="component-card-header">
                        <div class="component-name-type">
                            <span class="component-type ${comp.type}">${comp.type}</span>
                            <h4 class="component-name">${comp.name}</h4>
                        </div>
                        <div class="component-parent">
                            <span class="file-label">File:</span>
                            <span class="file-name">${comp.parentFile}</span>
                        </div>
                    </div>
                    
                    <div class="component-card-body">
                        <p class="component-purpose">${comp.purpose || 'No description available'}</p>
                        ${comp.signature ? `
                            <div class="component-signature">
                                <pre><code>${comp.signature}</code></pre>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="component-card-footer">
                        <button class="view-source-btn" data-parent-id="${comp.parentId}">View Source</button>
                        <button class="copy-component-btn" data-component="${comp.name}" data-file="${comp.parentFile}">Copy Reference</button>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
    
    // Add event listeners
    grid.querySelectorAll('.component-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.classList.contains('view-source-btn') && 
                !e.target.classList.contains('copy-component-btn')) {
                const parentId = card.dataset.parentId;
                if (parentId) {
                    showView('explorer');
                    showFileDetails(parentId);
                }
            }
        });
    });
    
    grid.querySelectorAll('.view-source-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            
            const parentId = btn.dataset.parentId;
            if (parentId) {
                // Find parent file
                const file = allTools.find(t => t.id === parentId);
                if (file) {
                    viewFileSource(file);
                }
            }
        });
    });
    
    grid.querySelectorAll('.copy-component-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            
            const componentName = btn.dataset.component;
            const fileName = btn.dataset.file;
            
            if (componentName && fileName) {
                // Find the actual file
                const file = allTools.find(t => t.name === fileName);
                
                if (file) {
                    const language = file.language || 'unknown';
                    
                    // Create a reference string
                    let reference = '';
                    
                    switch (language) {
                        case 'python':
                            // Convert file path to module path
                            const modulePath = file.path
                                .replace(/\\/g, '/')
                                .replace(/\.py$/, '')
                                .split('/')
                                .filter(p => p)
                                .join('.');
                                
                            reference = `from ${modulePath} import ${componentName}`;
                            break;
                            
                        case 'javascript':
                        case 'typescript':
                            reference = `import { ${componentName} } from './path/to/${fileName}'`;
                            break;
                            
                        default:
                            reference = `${componentName} from ${fileName}`;
                    }
                    
                    // Copy to clipboard
                    navigator.clipboard.writeText(reference)
                        .then(() => {
                            // Change button text temporarily
                            const originalText = btn.textContent;
                            btn.textContent = 'Copied!';
                            setTimeout(() => {
                                btn.textContent = originalText;
                            }, 2000);
                        })
                        .catch(err => {
                            console.error('Failed to copy:', err);
                        });
                }
            }
        });
    });
}

// Filter components based on user selections
function filterComponents() {
    const languageFilter = document.getElementById('languageFilter')?.value || '';
    const typeFilter = document.getElementById('typeFilter')?.value || '';
    const searchText = document.getElementById('componentSearch')?.value.toLowerCase() || '';
    
    // Get all components from tools
    const allComponents = [];
    
    allTools.forEach(tool => {
        if (tool.components && Array.isArray(tool.components)) {
            tool.components.forEach(comp => {
                if (comp.name) {
                    allComponents.push({
                        ...comp,
                        parentFile: tool.name,
                        parentPath: tool.path,
                        parentId: tool.id,
                        language: tool.language
                    });
                }
            });
        }
    });
    
    // Apply filters
    const filteredComponents = allComponents.filter(comp => {
        // Language filter
        if (languageFilter && comp.language !== languageFilter) return false;
        
        // Type filter
        if (typeFilter && comp.type !== typeFilter) return false;
        
        // Search filter
        if (searchText) {
            const name = (comp.name || '').toLowerCase();
            const purpose = (comp.purpose || '').toLowerCase();
            const signature = (comp.signature || '').toLowerCase();
            
            return name.includes(searchText) || 
                   purpose.includes(searchText) || 
                   signature.includes(searchText);
        }
        
        return true;
    });
    
    // Render filtered components
    renderComponentsGrid(filteredComponents);
}

// Insights view functions
async function loadInsightsView() {
    console.log('Loading insights view...');
    
    // Set loading state for chart containers
    ['complexityChart', 'dependencyGraph', 'codePatterns', 'recommendations'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = '<p>Loading data...</p>';
        }
    });
    
    // Use already loaded tools or fetch from API
    let tools = allTools;
    let stats = null;
    
    if (allTools.length === 0) {
        try {
            // Fetch both tools and stats in parallel
            [stats, tools] = await Promise.all([
                ipcRenderer.invoke('api-call', '/api/stats'),
                ipcRenderer.invoke('api-call', '/api/tools')
            ]);
            
            // Store tools for later use
            if (Array.isArray(tools)) {
                allTools = tools;
            }
        } catch (error) {
            console.error('Error fetching insights data:', error);
            ['complexityChart', 'dependencyGraph', 'codePatterns', 'recommendations'].forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    element.innerHTML = '<p>Error loading insights data: ' + error.message + '</p>';
                }
            });
            return;
        }
    } else {
        // We have tools, but still need to fetch stats
        try {
            stats = await ipcRenderer.invoke('api-call', '/api/stats');
        } catch (error) {
            console.warn('Failed to fetch stats, will calculate from tools:', error);
            // Continue without stats, charts will calculate from tools
        }
    }
    
    // Validate data before processing
    if (!Array.isArray(tools)) {
        console.error('Invalid tools data:', tools);
        document.getElementById('codePatterns').innerHTML = '<p>Error: Could not load code insights.</p>';
        return;
    }
    
    // Now process and display the data
    drawComplexityChart(tools, stats);
    drawDependencyGraph(tools);
    showCodePatterns(tools);
    showRecommendations(tools);
}

// Draw complexity chart
function drawComplexityChart(tools, stats) {
    const container = document.getElementById('complexityChart');
    if (!container) return;
    
    // Clear previous content
    container.innerHTML = '';
    
    // Create a new canvas element
    const canvas = document.createElement('canvas');
    canvas.id = 'complexityChartCanvas';
    container.appendChild(canvas);
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        container.innerHTML = '<p>Chart.js library not loaded. Please refresh the page.</p>';
        return;
    }
    
    // Use stats data if available, otherwise calculate from tools
    let complexityData;
    
    if (stats && stats.complexity && typeof stats.complexity === 'object') {
        // Use pre-calculated stats
        complexityData = stats.complexity;
    } else {
        // Calculate from tools
        complexityData = {
            simple: tools.filter(t => t.complexity === 'simple').length,
            moderate: tools.filter(t => t.complexity === 'moderate').length,
            complex: tools.filter(t => t.complexity === 'complex').length,
            unknown: tools.filter(t => !t.complexity || t.complexity === 'unknown').length
        };
    }
    
    try {
        // Prepare chart data
        const labels = Object.keys(complexityData);
        const data = Object.values(complexityData);
        
        // Colors for complexity levels
        const colors = ['#2ecc71', '#f39c12', '#e74c3c', '#95a5a6']; // green, orange, red, gray
        
        // Create chart
        if (complexityChart) {
            complexityChart.destroy();
        }
        
        complexityChart = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)), // Capitalize
                datasets: [{
                    label: 'Files',
                    data: data,
                    backgroundColor: colors.slice(0, labels.length)
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Code Complexity Distribution'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating complexity chart:', error);
        container.innerHTML = '<p>Error creating complexity chart: ' + error.message + '</p>';
    }
}

// Draw dependency graph
function drawDependencyGraph(tools) {
    const container = document.getElementById('dependencyGraph');
    if (!container) return;
    
    // Check if vis.js is available
    if (!window.vis) {
        container.innerHTML = '<p>Visualization library not loaded. Please refresh the page.</p>';
        return;
    }
    
    // Clear container
    container.innerHTML = '';
    
    // Extract dependencies from tools
    const dependencies = {};
    const nodes = [];
    const edges = [];
    
    // Process up to a limited number of tools to avoid performance issues
    const MAX_TOOLS = 100;
    const toolsToProcess = tools.slice(0, MAX_TOOLS);
    
    // Add tools as nodes
    toolsToProcess.forEach((tool, index) => {
        // Add node for the tool
        nodes.push({
            id: tool.id || `tool_${index}`,
            label: tool.name || `Tool ${index}`,
            group: tool.category || 'unknown'
        });
        
        // Process dependencies if available
        if (tool.dependencies) {
            // Handle both string array and object array formats
            let deps = tool.dependencies;
            if (typeof deps === 'string') {
                try {
                    deps = JSON.parse(deps);
                } catch (e) {
                    console.warn('Error parsing dependencies JSON:', e);
                    deps = [];
                }
            }
            
            if (Array.isArray(deps)) {
                deps.forEach(dep => {
                    // Handle both string and object formats
                    const depName = typeof dep === 'string' ? dep : 
                                   (dep.dependency_name || dep.name || '');
                    
                    if (depName) {
                        // Count dependency occurrences
                        dependencies[depName] = (dependencies[depName] || 0) + 1;
                        
                        // Add edge from tool to dependency
                        edges.push({
                            from: tool.id || `tool_${index}`,
                            to: `dep_${depName}`,
                            arrows: 'to'
                        });
                    }
                });
            }
        }
    });
    
    // Add top dependencies as nodes
    const TOP_DEPENDENCIES = 20;
    Object.entries(dependencies)
        .sort((a, b) => b[1] - a[1])
        .slice(0, TOP_DEPENDENCIES)
        .forEach(([dep, count]) => {
            nodes.push({
                id: `dep_${dep}`,
                label: `${dep} (${count})`,
                group: 'dependency',
                shape: 'box'
            });
        });
    
    // Create a network
    try {
        const data = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };
        
        const options = {
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 12
                }
            },
            edges: {
                width: 0.5,
                color: { opacity: 0.6 }
            },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -26,
                    centralGravity: 0.005,
                    springLength: 100,
                    springConstant: 0.18
                },
                maxVelocity: 146,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: { iterations: 150 }
            },
            groups: {
                dependency: {
                    color: { background: '#3498db', border: '#2980b9' },
                    shape: 'box'
                },
                utility: { color: { background: '#2ecc71' } },
                api: { color: { background: '#e74c3c' } },
                'data-processing': { color: { background: '#f39c12' } },
                ui: { color: { background: '#9b59b6' } },
                config: { color: { background: '#1abc9c' } },
                unknown: { color: { background: '#95a5a6' } }
            }
        };
        
        new vis.Network(container, data, options);
    } catch (error) {
        console.error('Error creating network graph:', error);
        container.innerHTML = '<p>Error creating dependency graph: ' + error.message + '</p>';
    }
}

// Show code patterns
function showCodePatterns(tools) {
    const container = document.getElementById('codePatterns');
    if (!container) return;
    
    // Identify patterns in the code
    const patterns = {
        'Entry Points': tools.filter(t => t.is_entry_point === true).length,
        'File Operations': tools.filter(t => t.category === 'file-ops' || t.purpose?.toLowerCase().includes('file')).length,
        'API Components': tools.filter(t => t.category === 'api').length,
        'Data Processing': tools.filter(t => t.category === 'data-processing').length,
        'UI Components': tools.filter(t => t.category === 'ui').length,
        'Configuration': tools.filter(t => t.category === 'config').length,
        'Test Files': tools.filter(t => t.name?.toLowerCase().includes('test') || t.path?.toLowerCase().includes('test')).length
    };
    
    // Build HTML
    let html = '<ul class="pattern-list">';
    
    Object.entries(patterns).forEach(([pattern, count]) => {
        if (count > 0) {
            html += `
                <li class="pattern-item">
                    <span class="pattern-name">${pattern}:</span>
                    <span class="pattern-count">${count} files</span>
                </li>
            `;
        }
    });
    
    html += '</ul>';
    
    // If no patterns found
    if (Object.values(patterns).every(count => count === 0)) {
        html = '<p>No significant code patterns detected.</p>';
    }
    
    container.innerHTML = html;
}

// Show recommendations
function showRecommendations(tools) {
    const container = document.getElementById('recommendations');
    if (!container) return;
    
    const recommendations = [];
    
    // Generate recommendations based on code analysis
    
    // Check for potentially complex files
    const complexFiles = tools.filter(t => t.complexity === 'complex');
    if (complexFiles.length > 5) {
        recommendations.push({
            title: 'Consider refactoring complex files',
            description: `You have ${complexFiles.length} complex files that might benefit from refactoring.`
        });
    }
    
    // Check test coverage
    const testFiles = tools.filter(t => t.name?.toLowerCase().includes('test') || t.path?.toLowerCase().includes('test'));
    const testRatio = testFiles.length / tools.length;
    if (testRatio < 0.1 && tools.length > 20) {
        recommendations.push({
            title: 'Improve test coverage',
            description: 'Your codebase has relatively few test files. Consider adding more tests.'
        });
    }
    
    // Check for inconsistent categorization
    const uncategorized = tools.filter(t => !t.category || t.category === 'unknown');
    if (uncategorized.length > tools.length * 0.3) {
        recommendations.push({
            title: 'Categorize uncategorized files',
            description: `${uncategorized.length} files (${Math.round(uncategorized.length / tools.length * 100)}%) are uncategorized. Consider rescanning with better categorization.`
        });
    }
    
    // Check Python-specific recommendations
    const pythonFiles = tools.filter(t => t.language === 'python');
    if (pythonFiles.length > 10) {
        const initFiles = pythonFiles.filter(t => t.name === '__init__.py');
        if (initFiles.length < pythonFiles.length * 0.2) {
            recommendations.push({
                title: 'Organize Python files into packages',
                description: 'Consider organizing Python files into proper packages with __init__.py files.'
            });
        }
    }
    
    // Generate HTML
    if (recommendations.length > 0) {
        let html = '<ul class="recommendations-list">';
        
        recommendations.forEach(rec => {
            html += `
                <li class="recommendation-item">
                    <h4>${rec.title}</h4>
                    <p>${rec.description}</p>
                </li>
            `;
        });
        
        html += '</ul>';
        container.innerHTML = html;
    } else {
        container.innerHTML = '<p>No specific recommendations at this time.</p>';
    }
}

// Notify user with a message
function showNotification(message, type = 'info') {
    // Remove any existing notifications first
    document.querySelectorAll('.notification').forEach(note => {
        note.remove();
    });
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Auto-remove after timeout
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 3000);
}

// Utility function: Get complexity label from score
function getComplexityLabel(score) {
    if (score === undefined || score === null || isNaN(score)) return 'Unknown';
    if (score > 2.0) return 'High'; 
    if (score > 1.0) return 'Medium';
    return 'Low';
}

// Update custom styles
function updateCustomStyles() {
    // Add custom styles
    let styleElement = document.getElementById('codeinventory-custom-styles');
    
    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = 'codeinventory-custom-styles';
        document.head.appendChild(styleElement);
    }
    
    styleElement.textContent += `
        /* Styles for excluded items */
         .explorer-layout {
            display: flex;
            position: relative;
        }
        
        .file-structure {
            width: 300px;
            min-width: 200px;
            flex-shrink: 0;
            overflow: auto;
        }
        
        .file-details-panel {
            flex-grow: 1;
            overflow: auto;
        }
        
        .panel-resizer {
            width: 8px;
            background-color: #e5e5e5;
            cursor: col-resize;
            position: relative;
            z-index: 10;
        }
        
        .panel-resizer:hover {
            background-color: #ccc;
        }
        
        body.resizing {
            cursor: col-resize;
            user-select: none;
        }
        
        .tree-item.excluded {
            text-decoration: line-through;
            opacity: 0.7;
            color: #e74c3c;
        }
        
        .tree-item.directory.excluded {
            background-color: #ffeeee;
            border-left: 2px solid #e74c3c;
        }
        
        .tree-item.file.excluded {
            background-color: #fff5f5;
            border-left: 2px solid #e74c3c;
        }
        
        /* Improved context menu */
        .context-menu {
            position: absolute;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            min-width: 180px;
            overflow: hidden;
        }
        
        .context-menu-item {
            padding: 10px 15px;
            cursor: pointer;
            transition: background-color 0.2s;
            font-size: 0.9rem;
        }
        
        .context-menu-item:hover {
            background-color: #f0f7fa;
        }
        
        .context-menu-item:not(:last-child) {
            border-bottom: 1px solid #f0f0f0;
        }
    `;
}

// Update the buildHierarchicalTree function to ensure directory structure is preserved
function buildHierarchicalTree(files) {
    const tree = {};
    
    // First pass - add all files
    files.forEach(file => {
        if (!file.path) return;
        
        // Split path into parts, normalizing separators
        const path = file.path.replace(/\\/g, '/').split('/').filter(p => p);
        
        // Start at the root of the tree
        let currentNode = tree;
        
        // Build path in tree
        path.forEach((part, index) => {
            // If this is the last part, it's a file
            if (index === path.length - 1) {
                currentNode[part] = {
                    type: 'file',
                    id: file.id || '',
                    name: part,
                    data: file
                };
            } else {
                // It's a directory
                if (!currentNode[part]) {
                    currentNode[part] = {
                        type: 'directory',
                        name: part,
                        children: {}
                    };
                }
                // Move to the next level
                currentNode = currentNode[part].children;
            }
        });
    });
    
    return tree;
}


// Add this function to set up resizable panels
function setupResizablePanels() {
    const resizer = document.getElementById('panelResizer');
    const fileStructure = document.querySelector('.file-structure');
    const fileDetails = document.querySelector('.file-details-panel');
    
    if (!resizer || !fileStructure || !fileDetails) return;
    
    let x = 0;
    let startWidth = 0;
    
    // Mouse events
    resizer.addEventListener('mousedown', initResize);
    
    function initResize(e) {
        x = e.clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(fileStructure).width, 10);
        
        document.documentElement.addEventListener('mousemove', doResize);
        document.documentElement.addEventListener('mouseup', stopResize);
        
        // Add a resize class to the document while resizing
        document.body.classList.add('resizing');
    }
    
    function doResize(e) {
        const width = startWidth + e.clientX - x;
        
        // Set min/max width
        if (width > 150 && width < window.innerWidth - 200) {
            fileStructure.style.width = `${width}px`;
            fileStructure.style.flexBasis = `${width}px`;
        }
    }
    
    function stopResize() {
        document.documentElement.removeEventListener('mousemove', doResize);
        document.documentElement.removeEventListener('mouseup', stopResize);
        document.body.classList.remove('resizing');
    }
    
    // Touch events for mobile/tablet
    resizer.addEventListener('touchstart', initTouchResize);
    
    function initTouchResize(e) {
        x = e.touches[0].clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(fileStructure).width, 10);
        
        document.documentElement.addEventListener('touchmove', doTouchResize);
        document.documentElement.addEventListener('touchend', stopTouchResize);
        
        document.body.classList.add('resizing');
    }
    
    function doTouchResize(e) {
        const width = startWidth + e.touches[0].clientX - x;
        
        if (width > 150 && width < window.innerWidth - 200) {
            fileStructure.style.width = `${width}px`;
            fileStructure.style.flexBasis = `${width}px`;
        }
    }
    
    function stopTouchResize() {
        document.documentElement.removeEventListener('touchmove', doTouchResize);
        document.documentElement.removeEventListener('touchend', stopTouchResize);
        document.body.classList.remove('resizing');
    }
}
// Search function for top search bar
function search() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;
    
    console.log(`Searching for: ${query}`);
    
    // Show loading indicator
    const resultsElement = document.getElementById('projectsList');
    if (resultsElement) {
        resultsElement.innerHTML = '<p>Searching...</p>';
    }
    
    // If we already have tools loaded, try searching locally first
    if (allTools.length > 0) {
        const localResults = allTools.filter(tool => {
            const name = (tool.name || '').toLowerCase();
            const path = (tool.path || '').toLowerCase();
            const language = (tool.language || '').toLowerCase();
            const category = (tool.category || '').toLowerCase();
            const purpose = (tool.purpose || '').toLowerCase();
            const description = (tool.description || '').toLowerCase();
            
            const searchTerm = query.toLowerCase();
            
            return name.includes(searchTerm) || 
                   path.includes(searchTerm) || 
                   language.includes(searchTerm) ||
                   category.includes(searchTerm) ||
                   purpose.includes(searchTerm) ||
                   description.includes(searchTerm);
        });
        
        if (localResults.length > 0) {
            console.log('Found local results:', localResults.length);
            showView('explorer');
            renderFileTree(localResults);
            return;
        }
    }
    
    // If no local results or no tools loaded, perform API search
    ipcRenderer.invoke('api-call', `/api/search?q=${encodeURIComponent(query)}`)
        .then(results => {
            console.log('Search results:', results);
            
            // Switch to explorer view
            showView('explorer');
            
            // Display results
            if (Array.isArray(results) && results.length > 0) {
                renderFileTree(results);
            } else {
                const treeContainer = document.getElementById('fileTree');
                if (treeContainer) {
                    treeContainer.innerHTML = `
                        <div class="no-results">
                            <p>No results found for "${query}"</p>
                            <p>Try a different search term or scan more code.</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Search error:', error);
            const treeContainer = document.getElementById('fileTree');
            if (treeContainer) {
                treeContainer.innerHTML = `
                    <div class="error-message">
                        <p>Error performing search: ${error.message}</p>
                        <p>Please try again.</p>
                    </div>
                `;
            }
        });
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded');
    
    // Add custom styles
    updateCustomStyles();
    
    // Add components view
    addComponentsView();
    
    // Initialize context menu
    initializeContextMenu();
    
    // Set up navigation event listeners
    document.querySelectorAll('nav a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = link.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
            if (viewName) {
                showView(viewName);
            }
        });
    });
    
    // Set up search functionality
    const searchButton = document.querySelector('.search-bar button');
    if (searchButton) {
        searchButton.addEventListener('click', search);
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                search();
            }
        });
    }
    
    // Initialize dashboard
    init();
});

// Make functions available globally for onclick handlers in HTML
window.showView = showView;
window.search = search;
window.showFileDetails = showFileDetails;
window.filterProjects = filterProjects;