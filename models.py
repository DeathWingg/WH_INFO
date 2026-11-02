from database import db


# ---------------- settings ----------------
def get_setting(key, default=None):
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def all_settings():
    with db() as conn:
        return {r["key"]: r["value"] for r in conn.execute("SELECT * FROM settings")}


def get_fees():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM payment_fees ORDER BY method, installments"
        ).fetchall()
        return [dict(r) for r in rows]


def set_fee(method, installments, fee_percent, fixed_fee):
    with db() as conn:
        conn.execute(
            "INSERT INTO payment_fees (method, installments, fee_percent, fixed_fee) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(method, installments) DO UPDATE SET "
            "fee_percent=excluded.fee_percent, fixed_fee=excluded.fixed_fee",
            (method, int(installments), float(fee_percent), float(fixed_fee)),
        )


def get_fee(method, installments):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM payment_fees WHERE method=? AND installments=?",
            (method, int(installments)),
        ).fetchone()
        return (
            dict(row)
            if row
            else {
                "method": method,
                "installments": installments,
                "fee_percent": 0,
                "fixed_fee": 0,
            }
        )


# ---------------- manufacturers ----------------
def manufacturers():
    with db() as conn:
        return [
            dict(r) for r in conn.execute("SELECT * FROM manufacturers ORDER BY name")
        ]


def get_or_create_manufacturer(name: str):
    if not name:
        return None
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO manufacturers (name) VALUES (?)", (name.strip(),)
        )
        row = conn.execute(
            "SELECT id FROM manufacturers WHERE name=?", (name.strip(),)
        ).fetchone()
        return row["id"]


# ---------------- products ----------------
def create_product(data: dict) -> int:
    mfid = get_or_create_manufacturer(data.get("manufacturer_name", "").strip() or None)
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO products
               (name, manufacturer_id, model, category, description, processor, ram,
                storage, screen_size, resolution, cameras, battery, os, connectivity,
                warranty, active)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                data["name"],
                mfid,
                data.get("model", ""),
                data.get("category", "Celular"),
                data.get("description", ""),
                data.get("processor", ""),
                data.get("ram", ""),
                data.get("storage", ""),
                data.get("screen_size", ""),
                data.get("resolution", ""),
                data.get("cameras", ""),
                data.get("battery", ""),
                data.get("os", ""),
                data.get("connectivity", ""),
                data.get("warranty", ""),
            ),
        )
        return cur.lastrowid


def update_product(pid: int, data: dict):
    mfid = get_or_create_manufacturer(data.get("manufacturer_name", "").strip() or None)
    with db() as conn:
        conn.execute(
            """UPDATE products SET
               name=?, manufacturer_id=?, model=?, category=?, description=?, processor=?,
               ram=?, storage=?, screen_size=?, resolution=?, cameras=?, battery=?, os=?,
               connectivity=?, warranty=?, active=?
               WHERE id=?""",
            (
                data["name"],
                mfid,
                data.get("model", ""),
                data.get("category", "Celular"),
                data.get("description", ""),
                data.get("processor", ""),
                data.get("ram", ""),
                data.get("storage", ""),
                data.get("screen_size", ""),
                data.get("resolution", ""),
                data.get("cameras", ""),
                data.get("battery", ""),
                data.get("os", ""),
                data.get("connectivity", ""),
                data.get("warranty", ""),
                1 if data.get("active", True) else 0,
                pid,
            ),
        )


def delete_product(pid: int):
    with db() as conn:
        variations = conn.execute(
            "SELECT id FROM variations WHERE product_id=?", (pid,)
        ).fetchall()
        for v in variations:
            conn.execute("DELETE FROM stock_movements WHERE variation_id=?", (v["id"],))
            conn.execute(
                "UPDATE sale_items SET variation_id=NULL WHERE variation_id=?",
                (v["id"],),
            )
        conn.execute("DELETE FROM products WHERE id=?", (pid,))


def list_products(search: str = "", manufacturer: str = ""):
    sql = """
        SELECT p.*, m.name AS manufacturer_name,
               (SELECT COALESCE(SUM(v.stock),0) FROM variations v WHERE v.product_id=p.id) AS total_stock,
               (SELECT filename FROM product_images pi WHERE pi.product_id=p.id AND pi.is_primary=1 LIMIT 1) AS primary_image
        FROM products p LEFT JOIN manufacturers m ON m.id=p.manufacturer_id
    """
    where, params = [], []
    if search:
        where.append("(p.name LIKE ? OR p.model LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if manufacturer:
        where.append("m.name = ?")
        params.append(manufacturer)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.created_at DESC"
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def get_product(pid: int):
    with db() as conn:
        row = conn.execute(
            """SELECT p.*, m.name AS manufacturer_name FROM products p
               LEFT JOIN manufacturers m ON m.id=p.manufacturer_id WHERE p.id=?""",
            (pid,),
        ).fetchone()
        if not row:
            return None
        p = dict(row)
        p["variations"] = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM variations WHERE product_id=? ORDER BY storage, color",
                (pid,),
            )
        ]
        p["images"] = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC",
                (pid,),
            )
        ]
        return p


def add_product_image(
    pid: int, filename: str, color: str = "", is_primary: bool = False
):
    with db() as conn:
        if is_primary:
            conn.execute(
                "UPDATE product_images SET is_primary=0 WHERE product_id=?", (pid,)
            )
        conn.execute(
            "INSERT INTO product_images (product_id, color, filename, is_primary) VALUES (?,?,?,?)",
            (pid, color, filename, 1 if is_primary else 0),
        )


def delete_product_image(image_id: int):
    with db() as conn:
        conn.execute("DELETE FROM product_images WHERE id=?", (image_id,))


def image_for_color(pid: int, color: str):
    with db() as conn:
        row = conn.execute(
            "SELECT filename FROM product_images WHERE product_id=? AND color=? LIMIT 1",
            (pid, color),
        ).fetchone()
        if row:
            return row["filename"]
        row = conn.execute(
            "SELECT filename FROM product_images WHERE product_id=? ORDER BY is_primary DESC LIMIT 1",
            (pid,),
        ).fetchone()
        return row["filename"] if row else None


# ---------------- variations ----------------
def create_variation(
    pid: int, storage: str, color: str, supplier_cost: float, stock: int, sku: str = ""
) -> int:
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO variations (product_id, storage, color, supplier_cost, stock, sku)
               VALUES (?,?,?,?,?,?)""",
            (pid, storage, color, float(supplier_cost), int(stock), sku),
        )
        vid = cur.lastrowid
        if stock:
            conn.execute(
                "INSERT INTO stock_movements (variation_id, delta, reason) VALUES (?,?,?)",
                (vid, int(stock), "cadastro inicial"),
            )
        return vid


def update_variation(
    vid: int, supplier_cost: float | None = None, stock: int | None = None
):
    with db() as conn:
        if supplier_cost is not None:
            conn.execute(
                "UPDATE variations SET supplier_cost=? WHERE id=?",
                (float(supplier_cost), vid),
            )
        if stock is not None:
            row = conn.execute(
                "SELECT stock FROM variations WHERE id=?", (vid,)
            ).fetchone()
            delta = int(stock) - (row["stock"] if row else 0)
            conn.execute("UPDATE variations SET stock=? WHERE id=?", (int(stock), vid))
            if delta:
                conn.execute(
                    "INSERT INTO stock_movements (variation_id, delta, reason) VALUES (?,?,?)",
                    (vid, delta, "ajuste manual"),
                )


def delete_variation(vid: int):
    with db() as conn:
        conn.execute("DELETE FROM variations WHERE id=?", (vid,))


def get_variation(vid: int):
    with db() as conn:
        row = conn.execute(
            """SELECT v.*, p.name AS product_name, p.id AS product_id, p.warranty, p.category
               FROM variations v JOIN products p ON p.id=v.product_id WHERE v.id=?""",
            (vid,),
        ).fetchone()
        return dict(row) if row else None


def list_variations_with_product():
    with db() as conn:
        rows = conn.execute(
            """SELECT v.*, p.name AS product_name, p.warranty, p.category,
                      (SELECT filename FROM product_images pi WHERE pi.product_id=p.id
                       AND pi.color=v.color LIMIT 1) AS color_image,
                      (SELECT filename FROM product_images pi WHERE pi.product_id=p.id
                       AND pi.is_primary=1 LIMIT 1) AS primary_image
               FROM variations v JOIN products p ON p.id=v.product_id
               WHERE v.active=1 AND p.active=1
               ORDER BY p.name, v.storage, v.color"""
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------- sales ----------------
def next_sale_number() -> str:
    with db() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM sales").fetchone()
        return f"WH-{row['c'] + 1:06d}"


def create_sale(
    client_data: dict,
    payment_method: str,
    installments: int,
    items: list,
    total: float,
    profit: float,
    notes: str = "",
) -> int:
    with db() as conn:
        client_id = None
        if client_data.get("name"):
            cur = conn.execute(
                "INSERT INTO clients (name, phone, cpf, email) VALUES (?,?,?,?)",
                (
                    client_data["name"],
                    client_data.get("phone", ""),
                    client_data.get("cpf", ""),
                    client_data.get("email", ""),
                ),
            )
            client_id = cur.lastrowid

        sale_number = next_sale_number()
        cur = conn.execute(
            """INSERT INTO sales (sale_number, client_id, client_name, payment_method,
                                  installments, total, profit, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                sale_number,
                client_id,
                client_data.get("name", ""),
                payment_method,
                installments,
                total,
                profit,
                notes,
            ),
        )
        sale_id = cur.lastrowid

        for it in items:
            conn.execute(
                """INSERT INTO sale_items (sale_id, variation_id, product_name, storage,
                    color, unit_price, unit_cost, quantity, image_filename)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    sale_id,
                    it["variation_id"],
                    it["product_name"],
                    it.get("storage", ""),
                    it.get("color", ""),
                    it["unit_price"],
                    it["unit_cost"],
                    it["quantity"],
                    it.get("image_filename", ""),
                ),
            )
            conn.execute(
                "UPDATE variations SET stock = stock - ? WHERE id=?",
                (it["quantity"], it["variation_id"]),
            )
            conn.execute(
                "INSERT INTO stock_movements (variation_id, delta, reason, sale_id) "
                "VALUES (?,?,?,?)",
                (it["variation_id"], -it["quantity"], "venda", sale_id),
            )
        return sale_id


def get_sale(sale_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
        if not row:
            return None
        sale = dict(row)
        sale["items"] = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)
            )
        ]
        return sale


def list_sales(search="", payment="", date_from="", date_to=""):
    sql = "SELECT * FROM sales"
    where, params = [], []
    if search:
        where.append(
            "(sale_number LIKE ? OR client_name LIKE ? OR "
            "EXISTS(SELECT 1 FROM sale_items si WHERE si.sale_id=sales.id AND si.product_name LIKE ?))"
        )
        params.extend([f"%{search}%"] * 3)
    if payment:
        where.append("payment_method = ?")
        params.append(payment)
    if date_from:
        where.append("date(created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        where.append("date(created_at) <= date(?)")
        params.append(date_to)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT 500"
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def dashboard_stats():
    with db() as conn:
        products = conn.execute(
            "SELECT COUNT(*) c FROM products WHERE active=1"
        ).fetchone()["c"]
        sales_count = conn.execute("SELECT COUNT(*) c FROM sales").fetchone()["c"]
        today = conn.execute(
            "SELECT COALESCE(SUM(total),0) t, COALESCE(SUM(profit),0) p FROM sales "
            "WHERE date(created_at)=date('now','localtime')"
        ).fetchone()
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(total),0) t FROM sales"
        ).fetchone()["t"]
        total_profit = conn.execute(
            "SELECT COALESCE(SUM(profit),0) p FROM sales"
        ).fetchone()["p"]
        threshold = int(get_setting("low_stock_threshold", "3"))
        low = [
            dict(r)
            for r in conn.execute(
                """SELECT v.id, v.stock, v.storage, v.color, p.name
               FROM variations v JOIN products p ON p.id=v.product_id
               WHERE v.stock <= ? AND v.active=1 ORDER BY v.stock ASC LIMIT 10""",
                (threshold,),
            )
        ]
        recent = [
            dict(r)
            for r in conn.execute("SELECT * FROM sales ORDER BY id DESC LIMIT 5")
        ]
        return {
            "products": products,
            "sales_count": sales_count,
            "today_revenue": today["t"],
            "today_profit": today["p"],
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "low_stock": low,
            "recent_sales": recent,
        }


def sales_report(date_from="", date_to=""):
    where, params = [], []
    if date_from:
        where.append("date(s.created_at) >= date(?)")
        params.append(date_from)
    if date_to:
        where.append("date(s.created_at) <= date(?)")
        params.append(date_to)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""

    with db() as conn:
        summary = conn.execute(
            f"SELECT COUNT(*) c, COALESCE(SUM(s.total),0) t, COALESCE(SUM(s.profit),0) p "
            f"FROM sales s{wsql}",
            params,
        ).fetchone()
        by_method = [
            dict(r)
            for r in conn.execute(
                f"""SELECT s.payment_method, COUNT(*) c, COALESCE(SUM(s.total),0) t
                FROM sales s{wsql} GROUP BY s.payment_method""",
                params,
            )
        ]
        top_products = [
            dict(r)
            for r in conn.execute(
                f"""SELECT si.product_name, SUM(si.quantity) qty, SUM(si.unit_price*si.quantity) total
                FROM sale_items si JOIN sales s ON s.id=si.sale_id{wsql}
                GROUP BY si.product_name ORDER BY qty DESC LIMIT 20""",
                params,
            )
        ]
        return {
            "summary": dict(summary),
            "by_method": by_method,
            "top_products": top_products,
            "date_from": date_from,
            "date_to": date_to,
        }
