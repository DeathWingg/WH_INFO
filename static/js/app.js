function addRow(containerId, type) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  // Pega a primeira linha para usar de molde e limpa os valores
  const firstRow = container.firstElementChild;
  const newRow = firstRow.cloneNode(true);
  
  newRow.querySelectorAll('input').forEach(inp => {
    if (inp.type !== 'file') inp.value = ''; 
  });
  
  container.appendChild(newRow);
}