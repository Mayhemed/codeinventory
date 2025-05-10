const { ipcRenderer } = require('electron');

let currentView = 'overview';
let allTools = [];
let allComponents = [];

// Initialize dashboard
async function init() {
    await loadOver
# Continue dashboard/renderer.js
cat >> dashboard/renderer.js << 'RENDERER'
viewData();
}

// Show different views
function showView(view) {
   currentView = view;
   document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
   document.getElementById(view).classList.add('active');
   
   switch(view) {
       case 'overview':
           loadOverviewData();
           break;
       case 'tools':
           loadTools();
           break;
       case 'components':
           loadComponents();
           break;
       case 'relationships':
           loadRelationships();
           break;
   }
}

// Load overview data
async function loadOverviewData() {
   try {
       const stats = await ipcRenderer.invoke('api-call', '/api/stats');
       
       document.getElementById('totalTools').textContent = stats.total_tools;
       document.getElementById('totalComponents').textContent = stats.total_components;
       document.getElementById('languageCount').textContent = stats.language_count;
       
       // Draw charts
       drawCategoryChart(stats.categories);
       drawLanguageChart(stats.languages);
   } catch (error) {
       console.error('Failed to load overview data:', error);
   }
}

// Load tools list
async function loadTools() {
   try {
       allTools = await ipcRenderer.invoke('api-call', '/api/tools');
       renderToolsList(allTools);
   } catch (error) {
       console.error('Failed to load tools:', error);
   }
}

// Render tools list
function renderToolsList(tools) {
   const container = document.getElementById('toolsList');
   container.innerHTML = '';
   
   tools.forEach(tool => {
       const card = document.createElement('div');
       card.className = 'tool-card';
       card.innerHTML = `
           <h3>${tool.name}</h3>
           <p>${tool.purpose || 'No description available'}</p>
           <div class="tool-meta">
               <span>Language: ${tool.language}</span>
               <span>Category: ${tool.category || 'Uncategorized'}</span>
               <span>Path: ${tool.path}</span>
           </div>
       `;
       container.appendChild(card);
   });
}

// Load components
async function loadComponents() {
   try {
       allComponents = await ipcRenderer.invoke('api-call', '/api/components');
       renderComponentsList(allComponents);
   } catch (error) {
       console.error('Failed to load components:', error);
   }
}

// Render components list
function renderComponentsList(components) {
   const container = document.getElementById('componentsList');
   container.innerHTML = '';
   
   components.forEach(component => {
       const card = document.createElement('div');
       card.className = 'component-card';
       card.innerHTML = `
           <h3>${component.name}</h3>
           <p>${component.purpose || 'No description available'}</p>
           <div class="tool-meta">
               <span>Type: ${component.type}</span>
               <span>Tool: ${component.tool_name}</span>
           </div>
       `;
       container.appendChild(card);
   });
}

// Load relationship graph
async function loadRelationships() {
   try {
       const relationships = await ipcRenderer.invoke('api-call', '/api/relationships');
       drawNetworkGraph(relationships);
   } catch (error) {
       console.error('Failed to load relationships:', error);
   }
}

// Draw network graph
function drawNetworkGraph(data) {
   const container = document.getElementById('networkGraph');
   
   const nodes = new vis.DataSet(data.nodes.map(node => ({
       id: node.id,
       label: node.name,
       group: node.category,
       title: node.purpose
   })));
   
   const edges = new vis.DataSet(data.edges.map(edge => ({
       from: edge.source,
       to: edge.target,
       label: edge.relationship_type,
       arrows: 'to'
   })));
   
   const networkData = { nodes, edges };
   
   const options = {
       nodes: {
           shape: 'box',
           margin: 10,
           font: { size: 14 }
       },
       edges: {
           font: { size: 12, align: 'middle' },
           arrows: { to: { scaleFactor: 1 } }
       },
       physics: {
           forceAtlas2Based: {
               gravitationalConstant: -26,
               centralGravity: 0.005,
               springLength: 230,
               springConstant: 0.18
           },
           maxVelocity: 146,
           solver: 'forceAtlas2Based',
           timestep: 0.35,
           stabilization: { iterations: 150 }
       }
   };
   
   new vis.Network(container, networkData, options);
}

// Draw category chart
function drawCategoryChart(categories) {
   const ctx = document.getElementById('categoryChart').getContext('2d');
   const labels = Object.keys(categories);
   const data = Object.values(categories);
   
   new Chart(ctx, {
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
               title: {
                   display: true,
                   text: 'Tools by Category'
               }
           }
       }
   });
}

// Draw language chart
function drawLanguageChart(languages) {
   const ctx = document.getElementById('languageChart').getContext('2d');
   const labels = Object.keys(languages);
   const data = Object.values(languages);
   
   new Chart(ctx, {
       type: 'bar',
       data: {
           labels: labels,
           datasets: [{
               label: 'Number of Files',
               data: data,
               backgroundColor: '#3498db'
           }]
       },
       options: {
           responsive: true,
           plugins: {
               title: {
                   display: true,
                   text: 'Files by Language'
               }
           },
           scales: {
               y: {
                   beginAtZero: true
               }
           }
       }
   });
}

// Search functionality
async function search() {
   const query = document.getElementById('searchInput').value;
   if (!query) return;
   
   try {
       const results = await ipcRenderer.invoke('api-call', `/api/search?q=${encodeURIComponent(query)}`);
       showView('tools');
       renderToolsList(results);
   } catch (error) {
       console.error('Search failed:', error);
   }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', init);

// Make functions available globally
window.showView = showView;
window.search = search;
