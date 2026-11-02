import os
import io
import csv
import uuid
import requests
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    send_from_directory,
    abort,
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash

import config
import models
from database import init_db, db
from services import pricing, pdf_generator, backup, product_search

app = Flask(
    __name__,
    template_folder=config.resource_path("templates"),
    static_folder=config.resource_path("static"),
)
app.secret_key = config.SECRET_KEY

ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@app.template_filter("brl")
def brl(v):
    try:
        s = f"{float(v):,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)

    return wrapper


def _save_image(file) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMG:
        return ""
    fname = f"{uuid.uuid4().hex}{ext}"
    path = config.IMAGES_DIR / fname
    file.save(path)
    try:
        from PIL import Image

        img = Image.open(path)
        img.thumbnail((1600, 1600))
        img.save(path)
    except Exception:
        pass
    return fname


@app.context_processor
def inject_globals():
    return {
        "settings": models.all_settings(),
        "is_admin": session.get("admin", False),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        s = models.all_settings()
        if check_password_hash(s.get("admin_password_hash", ""), pw):
            session["admin"] = True
            flash("Login realizado com sucesso.", "success")
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        flash("Senha incorreta.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Sessão encerrada.", "success")
    return redirect(url_for("dashboard"))


@app.route("/")
def dashboard():
    return render_template("dashboard.html", stats=models.dashboard_stats())


@app.route("/produtos")
def produtos():
    search = request.args.get("q", "")
    mf = request.args.get("m", "")
    return render_template(
        "produtos.html",
        products=models.list_products(search, mf),
        manufacturers=models.manufacturers(),
        search=search,
        mf=mf,
    )


@app.route("/produtos/novo", methods=["GET", "POST"])
def produto_novo():
    if request.method == "POST":
        data = request.form.to_dict()
        pid = models.create_product(data)

        files = request.files.getlist("images")
        colors = request.form.getlist("image_colors")
        for i, f in enumerate(files):
            if f and f.filename:
                fn = _save_image(f)
                if fn:
                    color = colors[i] if i < len(colors) else ""
                    models.add_product_image(pid, fn, color, is_primary=(i == 0))

        imported_images = request.form.getlist("imported_images")
        for imp_fn in imported_images:
            if imp_fn:
                models.add_product_image(pid, imp_fn, color="")

        if data.get("category") == "Serviço":
            models.create_variation(
                pid, "", "", float(data.get("service_cost", 0) or 0), 9999
            )
        else:
            storages = request.form.getlist("new_storage")
            vcolors = request.form.getlist("new_color")
            costs = request.form.getlist("new_cost")
            stocks = request.form.getlist("new_stock")

            for i in range(len(storages)):
                if storages[i] or vcolors[i]:
                    models.create_variation(
                        pid,
                        storages[i],
                        vcolors[i],
                        float(costs[i] or 0),
                        int(stocks[i] or 0),
                    )

        flash("Produto cadastrado com sucesso.", "success")
        return redirect(url_for("produtos"))

    return render_template("cadastro_produto.html", product=None, mode="novo")


@app.route("/produtos/<int:pid>/editar", methods=["GET", "POST"])
def produto_editar(pid):
    p = models.get_product(pid)
    if not p:
        abort(404)
    if request.method == "POST":
        data = request.form.to_dict()
        models.update_product(pid, data)

        files = request.files.getlist("images")
        colors = request.form.getlist("image_colors")
        for i, f in enumerate(files):
            if f and f.filename:
                fn = _save_image(f)
                if fn:
                    color = colors[i] if i < len(colors) else ""
                    models.add_product_image(pid, fn, color)

        imported_images = request.form.getlist("imported_images")
        for imp_fn in imported_images:
            if imp_fn:
                models.add_product_image(pid, imp_fn, color="")

        for img_id in request.form.getlist("remove_image"):
            try:
                models.delete_product_image(int(img_id))
            except ValueError:
                pass

        for vid in request.form.getlist("var_id"):
            try:
                vid_i = int(vid)
                cost = request.form.get(f"var_cost_{vid_i}")
                stock = request.form.get(f"var_stock_{vid_i}")
                models.update_variation(
                    vid_i,
                    float(cost) if cost else None,
                    int(stock) if stock else None,
                )
            except ValueError:
                pass

        if data.get("category") == "Serviço":
            if not request.form.getlist("var_id"):
                models.create_variation(
                    pid, "", "", float(request.form.get("service_cost", 0) or 0), 9999
                )
        else:
            storages = request.form.getlist("new_storage")
            vcolors = request.form.getlist("new_color")
            costs = request.form.getlist("new_cost")
            stocks = request.form.getlist("new_stock")

            for i in range(len(storages)):
                if storages[i] or vcolors[i]:
                    models.create_variation(
                        pid,
                        storages[i],
                        vcolors[i],
                        float(costs[i] or 0),
                        int(stocks[i] or 0),
                    )

        flash("Produto atualizado.", "success")
        return redirect(url_for("produto_editar", pid=pid))
    return render_template("cadastro_produto.html", product=p, mode="editar")


@app.route("/produtos/<int:pid>/excluir", methods=["POST"])
@login_required
def produto_excluir(pid):
    models.delete_product(pid)
    flash("Produto excluído.", "success")
    return redirect(url_for("produtos"))


@app.route("/variacoes/<int:vid>/excluir", methods=["POST"])
@login_required
def variacao_excluir(vid):
    models.delete_variation(vid)
    flash("Variação excluída.", "success")
    return redirect(request.referrer or url_for("produtos"))


@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory(str(config.IMAGES_DIR), filename)


@app.route("/produtos/buscar", methods=["POST"])
def produto_buscar():
    query = request.json.get("query", "").strip() if request.is_json else ""
    return jsonify(product_search.search_external(query))


@app.route("/produtos/buscar-imagens", methods=["POST"])
def buscar_imagens():
    query = request.json.get("query", "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Digite o nome do aparelho."})
    res = product_search.search_external(query)
    return jsonify(res)


@app.route("/produtos/importar-imagem", methods=["POST"])
def importar_imagem():
    url = request.json.get("url")
    if not url:
        return jsonify({"ok": False, "error": "URL inválida."})

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        fname = f"import_{uuid.uuid4().hex}.jpg"
        path = config.IMAGES_DIR / fname
        with open(path, "wb") as f:
            f.write(r.content)

        from PIL import Image

        img = Image.open(path)
        img.thumbnail((1000, 1000))
        img.convert("RGB").save(path, "JPEG")

        return jsonify({"ok": True, "filename": fname})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/calculadora")
def calculadora():
    return render_template(
        "calculadora.html",
        variations=models.list_variations_with_product(),
        settings=models.all_settings(),
    )


@app.route("/api/precos/<int:vid>")
def api_precos(vid):
    v = models.get_variation(vid)
    if not v:
        return jsonify({"ok": False}), 404
    s = models.all_settings()
    mode = s.get("margin_mode", "markup_on_cost")
    out = {
        "ok": True,
        "product": f"{v['product_name']} {v['storage']} {v['color']}".strip(),
    }
    for method, margin_key, installments_list in [
        ("cash", "margin_cash", [1]),
        ("debit", "margin_debit", [1]),
        ("credit", "margin_credit", [1, 2, 3, 4, 5, 6, 10, 12]),
    ]:
        # Regra de margem zero para serviços na calculadora também
        is_service = v.get("category") == "Serviço"
        margin = 0 if is_service else float(s.get(margin_key, "0"))

        out[method] = []
        for inst in installments_list:
            fee = models.get_fee(method, inst)
            b = pricing.full_breakdown(
                v["supplier_cost"],
                margin,
                mode,
                fee["fee_percent"],
                fee["fixed_fee"],
                inst,
            )
            out[method].append(
                {
                    "installments": inst,
                    "total": b["final_price"],
                    "installment_value": b["installment_value"],
                    "fee_percent": fee["fee_percent"],
                }
            )
    return jsonify(out)


@app.route("/vendas")
def vendas():
    s = models.all_settings()
    fees_list = models.get_fees()

    fees_dict = {
        f"{f['method']}_{f['installments']}": {
            "percent": f["fee_percent"],
            "fixed": f["fixed_fee"],
        }
        for f in fees_list
    }

    js_data = {
        "finalizarUrl": url_for("venda_finalizar"),
        "margins": {
            "cash": float(s.get("margin_cash") or 20),
            "debit": float(s.get("margin_debit") or 22),
            "credit": float(s.get("margin_credit") or 25),
        },
        "fees": fees_dict,
    }

    return render_template(
        "vendas.html",
        variations=models.list_variations_with_product(),
        settings=s,
        js_data=js_data,
    )


@app.route("/vendas/finalizar", methods=["POST"])
def venda_finalizar():
    data = request.get_json()
    if not data or not data.get("items"):
        return jsonify({"ok": False, "error": "Carrinho vazio"}), 400

    s = models.all_settings()
    mode = s.get("margin_mode", "markup_on_cost")
    method = data.get("payment_method", "cash")
    installments = int(data.get("installments", 1))

    margin_key = {
        "cash": "margin_cash",
        "debit": "margin_debit",
        "credit": "margin_credit",
    }.get(method, "margin_cash")
    margin = float(s.get(margin_key, "0"))
    fee = models.get_fee(method, installments)

    items = []
    total = 0.0
    profit = 0.0
    for it in data["items"]:
        v = models.get_variation(int(it["variation_id"]))
        if not v:
            return jsonify({"ok": False, "error": "Variação inválida"}), 400
        qty = int(it.get("quantity", 1))
        if v["stock"] < qty and s.get("allow_backorder") != "1":
            return jsonify(
                {"ok": False, "error": f"Estoque insuficiente para {v['product_name']}"}
            ), 400

        # Regra: Margem zero para serviços
        is_service = v.get("category") == "Serviço"
        item_margin = 0 if is_service else margin

        price = pricing.final_price(
            v["supplier_cost"],
            item_margin,
            mode,
            fee["fee_percent"],
            fee["fixed_fee"],
        )
        unit_profit = (
            price
            - v["supplier_cost"]
            - (price * fee["fee_percent"] / 100 + fee["fixed_fee"])
        )
        items.append(
            {
                "variation_id": v["id"],
                "product_name": v["product_name"],
                "storage": v["storage"],
                "color": v["color"],
                "unit_price": price,
                "unit_cost": v["supplier_cost"],
                "quantity": qty,
                "image_filename": models.image_for_color(v["product_id"], v["color"])
                or "",
            }
        )
        total += price * qty
        profit += unit_profit * qty

    discount_percent = float(data.get("discount", 0))
    if discount_percent > 0:
        discount_value = total * (discount_percent / 100)
        total -= discount_value
        profit -= discount_value

    client = {
        "name": data.get("client_name", "").strip(),
        "phone": data.get("client_phone", "").strip(),
        "cpf": data.get("client_cpf", "").strip(),
        "email": data.get("client_email", "").strip(),
    }

    try:
        sale_id = models.create_sale(
            client, method, installments, items, total, profit, data.get("notes", "")
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify(
        {
            "ok": True,
            "sale_id": sale_id,
            "redirect": url_for("venda_ficha", sale_id=sale_id),
        }
    )


@app.route("/vendas/<int:sale_id>/ficha")
def venda_ficha(sale_id):
    sale = models.get_sale(sale_id)
    if not sale:
        abort(404)
    return render_template("ficha.html", sale=sale, settings=models.all_settings())


@app.route("/vendas/<int:sale_id>/pdf")
def venda_pdf(sale_id):
    sale = models.get_sale(sale_id)
    if not sale:
        abort(404)
    pdf = pdf_generator.generate_sale_pdf(sale, models.all_settings())
    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=request.args.get("download") == "1",
        download_name=f"ficha_{sale['sale_number']}.pdf",
    )


@app.route("/historico")
def historico():
    sales = models.list_sales(
        search=request.args.get("q", ""),
        payment=request.args.get("p", ""),
        date_from=request.args.get("from", ""),
        date_to=request.args.get("to", ""),
    )
    return render_template(
        "historico.html",
        sales=sales,
        search=request.args.get("q", ""),
        payment=request.args.get("p", ""),
        date_from=request.args.get("from", ""),
        date_to=request.args.get("to", ""),
    )


@app.route("/historico/<int:sale_id>")
def historico_detalhe(sale_id):
    sale = models.get_sale(sale_id)
    if not sale:
        abort(404)
    return render_template("historico_detalhe.html", sale=sale)


@app.route("/relatorios")
def relatorios():
    df = request.args.get("from", "")
    dt = request.args.get("to", "")
    return render_template(
        "relatorios.html", report=models.sales_report(df, dt), date_from=df, date_to=dt
    )


@app.route("/relatorios/exportar.csv")
def relatorios_csv():
    df = request.args.get("from", "")
    dt = request.args.get("to", "")
    rep = models.sales_report(df, dt)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Métrica", "Valor"])
    w.writerow(["Total de vendas", rep["summary"]["c"]])
    w.writerow(["Faturamento", f"{rep['summary']['t']:.2f}"])
    w.writerow(["Lucro estimado", f"{rep['summary']['p']:.2f}"])
    w.writerow([])
    w.writerow(["Forma de pagamento", "Quantidade", "Total"])
    for m in rep["by_method"]:
        w.writerow([m["payment_method"], m["c"], f"{m['t']:.2f}"])
    w.writerow([])
    w.writerow(["Produto", "Qtd vendida", "Total"])
    for p in rep["top_products"]:
        w.writerow([p["product_name"], p["qty"], f"{p['total']:.2f}"])
    data = buf.getvalue().encode("utf-8-sig")
    return send_file(
        io.BytesIO(data),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"relatorio_{df or 'inicio'}_{dt or 'fim'}.csv",
    )


@app.route("/configuracoes", methods=["GET", "POST"])
@login_required
def configuracoes():
    if request.method == "POST":
        for key in [
            "store_name",
            "store_subtitle",
            "store_phone",
            "store_address",
            "store_email",
            "margin_cash",
            "margin_debit",
            "margin_credit",
            "margin_mode",
            "low_stock_threshold",
        ]:
            if key in request.form:
                models.set_setting(key, request.form.get(key, ""))
        models.set_setting(
            "allow_backorder", "1" if request.form.get("allow_backorder") else "0"
        )
        new_pw = request.form.get("new_password", "").strip()
        if new_pw:
            models.set_setting("admin_password_hash", generate_password_hash(new_pw))
            flash("Senha alterada.", "success")
        flash("Configurações salvas.", "success")
        return redirect(url_for("configuracoes"))
    return render_template("configuracoes.html", fees=models.get_fees())


@app.route("/configuracoes/taxas", methods=["POST"])
@login_required
def configuracoes_taxas():
    for key, value in request.form.items():
        if key.startswith("fee_"):
            parts = key.split("_")
            method = parts[1]
            inst = parts[2]
            try:
                models.set_fee(method, int(inst), float(value or 0), 0)
            except ValueError:
                pass
    flash("Taxas atualizadas.", "success")
    return redirect(url_for("configuracoes"))


@app.route("/backup", methods=["GET", "POST"])
@login_required
def backup_page():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "criar":
            path = backup.create_backup()
            flash(f"Backup criado: {path.name}", "success")
        elif action == "restaurar":
            f = request.files.get("file")
            if not f or not f.filename:
                flash("Envie um arquivo de backup.", "error")
            else:
                tmp = config.BACKUPS_DIR / f"upload_{uuid.uuid4().hex}.zip"
                f.save(tmp)
                try:
                    backup.restore_backup(str(tmp))
                    flash("Backup restaurado. Reinicie o aplicativo.", "success")
                except Exception as e:
                    flash(f"Falha ao restaurar: {e}", "error")
                finally:
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
        return redirect(url_for("backup_page"))
    return render_template("backup.html", backups=backup.list_backups())


@app.route("/backup/download/<path:filename>")
@login_required
def backup_download(filename):
    return send_from_directory(str(config.BACKUPS_DIR), filename, as_attachment=True)


@app.route("/admin/limpar-vendas", methods=["POST"])
@login_required
def limpar_vendas():
    with db() as conn:
        # 1. Devolve o estoque dos itens vendidos
        items = conn.execute(
            "SELECT variation_id, quantity FROM sale_items WHERE variation_id IS NOT NULL"
        ).fetchall()
        for it in items:
            conn.execute(
                "UPDATE variations SET stock = stock + ? WHERE id = ?",
                (it["quantity"], it["variation_id"]),
            )

        # 2. Apaga os itens das vendas
        conn.execute("DELETE FROM sale_items")

        # 3. Apaga as movimentações de estoque geradas por vendas
        conn.execute("DELETE FROM stock_movements WHERE sale_id IS NOT NULL")

        # 4. Apaga as vendas
        conn.execute("DELETE FROM sales")

        # 5. Limpa os clientes que não possuem mais compras atreladas
        conn.execute(
            "DELETE FROM clients WHERE id NOT IN (SELECT DISTINCT client_id FROM sales WHERE client_id IS NOT NULL)"
        )

    flash("Histórico de vendas apagado e estoque restaurado com sucesso!", "success")
    return redirect(url_for("configuracoes"))


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")


def create_app():
    init_db()
    return app


if __name__ == "__main__":
    create_app()
    app.run(host=config.HOST, port=config.PORT, debug=False)
