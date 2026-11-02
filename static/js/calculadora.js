(() => {
  const btn = document.getElementById('calc-btn');
  const sel = document.getElementById('variation');
  const out = document.getElementById('calc-result');
  const brl = v => 'R$ ' + Number(v).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  btn.addEventListener('click', async () => {
    if (!sel.value) return alert('Selecione um aparelho.');
    
    out.innerHTML = '<div class="panel"><p class="muted">Calculando...</p></div>';
    
    try {
      const r = await fetch(`${window.WH_INFO.calcUrl}/${sel.value}`);
      const data = await r.json();
      if (!data.ok) throw new Error('Erro ao calcular');

      let html = `<div class="panel"><h2>${data.product}</h2><div class="grid-2">`;
      
      const sections = [['cash', 'À Vista'], ['debit', 'Débito'], ['credit', 'Crédito']];
      
      for (const [key, label] of sections) {
        if (!data[key] || data[key].length === 0) continue;
        html += `<div><h3 style="color:var(--blue-2); font-size:14px; margin-bottom:12px;">${label}</h3>`;
        html += `<table style="width:100%; font-size:13px;"><thead><tr><th>Parcelas</th><th>Valor Parcela</th><th>Total</th></tr></thead><tbody>`;
        
        for (const opt of data[key]) {
          html += `<tr>
            <td>${opt.installments}x</td>
            <td>${brl(opt.installment_value)}</td>
            <td><b>${brl(opt.total)}</b></td>
          </tr>`;
        }
        html += `</tbody></table></div>`;
      }
      
      html += `</div></div>`;
      out.innerHTML = html;
      
    } catch (err) {
      out.innerHTML = `<div class="panel danger">${err.message}</div>`;
    }
  });
})();