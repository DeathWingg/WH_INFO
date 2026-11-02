(() => {
  const cart = new Map();
  const cartEl = document.getElementById('cart-items');
  const totalEl = document.getElementById('cart-total');
  const discountInput = document.getElementById('discount');
  const profitEl = document.getElementById('cart-profit');
  
  const brl = v => {
    const num = Number(v);
    if (isNaN(num)) return 'R$ 0,00';
    return 'R$ ' + num.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  };

  function calcPrice(item, method, installments) {
    try {
      const margins = window.WH_INFO.margins || { cash: 20, debit: 22, credit: 25 };
      const fees = window.WH_INFO.fees || {};
      
      // NOVA REGRA: Se for Serviço, a margem de lucro é ZERO.
      const isService = item.category === "Serviço";
      const margin = isService ? 0 : (parseFloat(margins[method]) || 0);
      
      const feeKey = `${method}_${installments}`;
      const fee = fees[feeKey] || { percent: 0, fixed: 0 };
      
      const cost = parseFloat(item.cost) || 0;
      
      const basePrice = cost * (1 + (margin / 100));
      const finalPrice = (basePrice + fee.fixed) / (1 - (fee.percent / 100));
      return finalPrice;
    } catch (e) {
      console.error("Erro no cálculo:", e);
      return 0;
    }
  }

  function render() {
    if (cart.size === 0) {
      cartEl.innerHTML = '<p class="muted" style="font-size:14px;">Selecione produtos no catálogo.</p>';
      totalEl.textContent = 'R$ 0,00';
      if (profitEl) profitEl.textContent = 'R$ 0,00';
      return;
    }
    
    cartEl.innerHTML = '';
    let subtotal = 0;
    let totalProfit = 0;
    
    const method = document.getElementById('payment-method').value;
    const installments = parseInt(document.getElementById('installments').value);
    
    const fees = window.WH_INFO.fees || {};
    const fee = fees[`${method}_${installments}`] || { percent: 0, fixed: 0 };

    for (const [id, it] of cart) {
      const unitPrice = calcPrice(it, method, installments);
      const qty = parseInt(it.quantity) || 1; 
      
      subtotal += unitPrice * qty;

      const unitFee = (unitPrice * (fee.percent / 100)) + fee.fixed;
      const unitCost = parseFloat(it.cost) || 0;
      const unitProfit = unitPrice - unitCost - unitFee;
      totalProfit += unitProfit * qty;

      const line = document.createElement('div');
      line.style.cssText = 'display:flex; gap:8px; align-items:center; padding:8px; background:var(--bg-2); border-radius:8px;';
      line.innerHTML = `
        <div style="flex:1; font-size:12px;">
          <strong>${it.name}</strong><br>
          <small style="color:var(--muted)">${it.storage} ${it.color}</small><br>
          <small style="color:var(--blue-2)">${brl(unitPrice)} un.</small>
        </div>
        <input type="number" min="1" max="${it.stock}" value="${qty}" data-id="${id}" style="width:45px; padding:4px; text-align:center; background:var(--panel); border:1px solid var(--border); color:white; border-radius:4px;">
        <button class="remove" data-id="${id}" style="background:none; border:none; color:var(--danger); cursor:pointer; font-size:18px;">&times;</button>
      `;
      cartEl.appendChild(line);
    }

    const discountPercent = (discountInput) ? (parseFloat(discountInput.value) || 0) : 0;
    const discountValue = subtotal * (discountPercent / 100);
    const total = subtotal - discountValue;
    
    totalEl.textContent = brl(total);
    totalProfit -= discountValue;
    if (profitEl) profitEl.textContent = brl(totalProfit);

    cartEl.querySelectorAll('input[type=number]').forEach(inp => {
      inp.addEventListener('change', e => {
        const i = cart.get(e.target.dataset.id);
        i.quantity = Math.max(1, Math.min(parseInt(e.target.value) || 1, i.stock));
        render();
      });
    });

    cartEl.querySelectorAll('.remove').forEach(b => {
      b.addEventListener('click', () => { cart.delete(b.dataset.id); render(); });
    });
  }

  document.querySelectorAll('.catalog-item').forEach(el => {
    el.addEventListener('click', () => {
      const id = el.dataset.id;
      if (!cart.has(id)) {
        cart.set(id, {
          variation_id: parseInt(id),
          name: el.dataset.name,
          storage: el.dataset.storage,
          color: el.dataset.color,
          stock: parseInt(el.dataset.stock),
          cost: parseFloat(el.dataset.cost || 0),
          category: el.dataset.category,
          quantity: 1
        });
      } else {
        const item = cart.get(id);
        if (item.quantity < item.stock) item.quantity += 1;
      }
      render();
    });
  });

  const paySelect = document.getElementById('payment-method');
  if (paySelect) paySelect.addEventListener('change', render);
  
  const instSelect = document.getElementById('installments');
  if (instSelect) instSelect.addEventListener('change', render);
  
  if (discountInput) discountInput.addEventListener('input', render);

  const searchInput = document.getElementById('search-variations');
  if (searchInput) {
    searchInput.addEventListener('input', e => {
      const q = e.target.value.toLowerCase();
      document.querySelectorAll('.catalog-item').forEach(el => {
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  const checkoutBtn = document.getElementById('checkout');
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', async () => {
      if (cart.size === 0) return alert('O carrinho está vazio.');
      
      checkoutBtn.disabled = true;
      checkoutBtn.textContent = 'Processando...';

      const payload = {
        payment_method: document.getElementById('payment-method').value,
        installments: parseInt(document.getElementById('installments').value),
        discount: (discountInput) ? (parseFloat(discountInput.value) || 0) : 0,
        client_name: document.getElementById('client-name').value,
        client_phone: document.getElementById('client-phone').value,
        items: [...cart.values()].map(i => ({ variation_id: i.variation_id, quantity: parseInt(i.quantity) || 1 }))
      };

      try {
        const r = await fetch(window.WH_INFO.finalizarUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.error || 'Erro desconhecido');
        window.location.href = data.redirect;
      } catch (err) {
        alert('Erro: ' + err.message);
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Finalizar Venda';
      }
    });
  }
})();