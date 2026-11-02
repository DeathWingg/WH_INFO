"""Cálculos de preço e margem — coração do sistema financeiro."""


def base_price(
    cost: float, margin_percent: float, mode: str = "markup_on_cost"
) -> float:
    """Preço-base antes das taxas de cartão.

    mode='markup_on_cost'  -> preço = custo * (1 + margem)
    mode='margin_on_final' -> margem é % do PREÇO FINAL => preço = custo / (1 - margem)
    """
    cost = float(cost or 0)
    m = float(margin_percent or 0) / 100.0
    if cost <= 0:
        return 0.0
    if mode == "margin_on_final":
        if m >= 1:
            return cost
        return cost / (1 - m)
    return cost * (1 + m)


def final_price(
    cost: float,
    margin_percent: float,
    mode: str,
    fee_percent: float = 0.0,
    fixed_fee: float = 0.0,
) -> float:
    """Preço final aplicando a taxa da máquina de cartão."""
    base = base_price(cost, margin_percent, mode)
    fee = float(fee_percent or 0) / 100.0
    if fee >= 1:
        return base + fixed_fee
    return (base + fixed_fee) / (1 - fee)


def installment_value(total: float, installments: int) -> float:
    """Calcula o valor de cada parcela."""
    installments = max(1, int(installments))
    return round(total / installments, 2)


def full_breakdown(
    cost: float,
    margin_percent: float,
    mode: str,
    fee_percent: float = 0.0,
    fixed_fee: float = 0.0,
    installments: int = 1,
) -> dict:
    """Gera um relatório completo com lucro e taxas (para a tela interna)."""
    base = base_price(cost, margin_percent, mode)
    final = final_price(cost, margin_percent, mode, fee_percent, fixed_fee)
    fee_value = final * (float(fee_percent) / 100.0) + float(fixed_fee)
    profit = final - cost - fee_value
    return {
        "cost": round(cost, 2),
        "base_price": round(base, 2),
        "final_price": round(final, 2),
        "fee_value": round(fee_value, 2),
        "profit": round(profit, 2),
        "installments": installments,
        "installment_value": installment_value(final, installments),
    }
